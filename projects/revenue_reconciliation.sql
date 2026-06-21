-- ============================================================
--  REVENUE RECONCILIATION QUERY SET
--  Author  : Alexis "Zaira" Kelly  |  accordanalyst.com
--  Purpose : Surface revenue leakage, aging receivables,
--            duplicate charges, and payment gaps across a
--            SaaS billing environment.
--  Schema  : Simulated — no real client data used.
--  Target  : Revenue Ops · Billing Ops · Senior Data Analyst
-- ============================================================


-- ============================================================
-- SCHEMA REFERENCE (simulated tables)
-- ============================================================
--
-- accounts        : account_id, account_name, tier, region, csm_owner
--
-- invoices        : invoice_id, account_id, invoice_date, due_date,
--                   amount_due, status, billing_period_start,
--                   billing_period_end, product_line
--
-- payments        : payment_id, invoice_id, account_id,
--                   payment_date, amount_paid, payment_method
--
-- contracts       : contract_id, account_id, contracted_arr,
--                   billing_frequency, contract_start, contract_end,
--                   auto_renew
--
-- credit_memos    : memo_id, account_id, invoice_id,
--                   memo_date, memo_amount, reason_code
--
-- ============================================================


-- ============================================================
-- QUERY 1: AGING RECEIVABLES REPORT
-- Business question: Which accounts owe us money, how long
-- have they owed it, and how much total is outstanding?
-- ============================================================
-- Why this matters: Aging receivables are the most direct
-- form of revenue leakage. Every unpaid invoice older than
-- 30 days represents cash the company has earned but not
-- collected. This query buckets outstanding balances into
-- standard aging tiers so collections can be prioritised.
-- ============================================================

SELECT
    a.account_name,
    a.tier,
    a.region,
    a.csm_owner,
    COUNT(i.invoice_id)                                  AS open_invoice_count,
    SUM(i.amount_due)                                    AS total_outstanding,

    -- Bucket by days past due
    SUM(CASE WHEN CURRENT_DATE - i.due_date BETWEEN 1  AND 30  THEN i.amount_due ELSE 0 END) AS bucket_1_30,
    SUM(CASE WHEN CURRENT_DATE - i.due_date BETWEEN 31 AND 60  THEN i.amount_due ELSE 0 END) AS bucket_31_60,
    SUM(CASE WHEN CURRENT_DATE - i.due_date BETWEEN 61 AND 90  THEN i.amount_due ELSE 0 END) AS bucket_61_90,
    SUM(CASE WHEN CURRENT_DATE - i.due_date > 90               THEN i.amount_due ELSE 0 END) AS bucket_90_plus,

    -- Flag accounts with the most critical exposure
    CASE
        WHEN SUM(CASE WHEN CURRENT_DATE - i.due_date > 90 THEN i.amount_due ELSE 0 END) > 10000
        THEN 'ESCALATE'
        WHEN SUM(CASE WHEN CURRENT_DATE - i.due_date > 60 THEN i.amount_due ELSE 0 END) > 5000
        THEN 'PRIORITY FOLLOW-UP'
        ELSE 'STANDARD'
    END                                                  AS collection_priority,

    MAX(CURRENT_DATE - i.due_date)                       AS max_days_outstanding

FROM invoices i
JOIN accounts a ON i.account_id = a.account_id
WHERE
    i.status NOT IN ('paid', 'void', 'written_off')
    AND i.amount_due > 0
GROUP BY
    a.account_name, a.tier, a.region, a.csm_owner
HAVING
    SUM(i.amount_due) > 0
ORDER BY
    total_outstanding DESC;


-- ============================================================
-- QUERY 2: PAYMENT SHORTFALL DETECTION
-- Business question: Where has an account paid less than
-- invoiced, and by how much?
-- ============================================================
-- Why this matters: Short payments are one of the most
-- common and least-tracked billing gaps. Without a dedicated
-- query, they surface only when a customer disputes a balance
-- or a collections team manually reconciles accounts.
-- This query automates that reconciliation continuously.
-- ============================================================

WITH invoice_totals AS (
    SELECT
        invoice_id,
        account_id,
        amount_due,
        invoice_date,
        due_date,
        product_line
    FROM invoices
    WHERE status NOT IN ('void', 'written_off')
),
payment_totals AS (
    SELECT
        invoice_id,
        SUM(amount_paid)  AS total_paid,
        COUNT(*)          AS payment_count,
        MAX(payment_date) AS last_payment_date
    FROM payments
    GROUP BY invoice_id
),
credit_totals AS (
    SELECT
        invoice_id,
        SUM(memo_amount)  AS total_credits
    FROM credit_memos
    GROUP BY invoice_id
)

SELECT
    a.account_name,
    a.tier,
    it.invoice_id,
    it.invoice_date,
    it.due_date,
    it.product_line,
    it.amount_due,
    COALESCE(pt.total_paid, 0)                           AS total_paid,
    COALESCE(ct.total_credits, 0)                        AS credits_applied,

    -- Net balance after payments and credits
    it.amount_due
        - COALESCE(pt.total_paid, 0)
        - COALESCE(ct.total_credits, 0)                  AS net_balance_due,

    -- Percentage paid
    ROUND(
        COALESCE(pt.total_paid, 0) / NULLIF(it.amount_due, 0) * 100,
    2)                                                   AS pct_paid,

    COALESCE(pt.payment_count, 0)                        AS payment_count,
    pt.last_payment_date,
    CURRENT_DATE - it.due_date                           AS days_past_due

FROM invoice_totals it
JOIN accounts a      ON it.account_id = a.account_id
LEFT JOIN payment_totals pt ON it.invoice_id = pt.invoice_id
LEFT JOIN credit_totals  ct ON it.invoice_id = ct.invoice_id
WHERE
    -- Only invoices with a payment gap
    (it.amount_due
        - COALESCE(pt.total_paid, 0)
        - COALESCE(ct.total_credits, 0)) > 0.01
ORDER BY
    net_balance_due DESC;


-- ============================================================
-- QUERY 3: DUPLICATE CHARGE DETECTION
-- Business question: Are any accounts being billed more than
-- once for the same billing period and product?
-- ============================================================
-- Why this matters: Duplicate invoices cause customer churn,
-- dispute volume, and compliance exposure. They occur most
-- often during system migrations, billing system upgrades,
-- or when billing cycles are manually re-triggered.
-- This query catches them before they reach the customer.
-- ============================================================

WITH invoice_fingerprint AS (
    SELECT
        invoice_id,
        account_id,
        product_line,
        billing_period_start,
        billing_period_end,
        amount_due,
        invoice_date,
        -- Build a fingerprint: same account + product + period = potential duplicate
        COUNT(*) OVER (
            PARTITION BY
                account_id,
                product_line,
                billing_period_start,
                billing_period_end
        )                                                AS period_invoice_count
    FROM invoices
    WHERE status NOT IN ('void', 'written_off')
)

SELECT
    a.account_name,
    a.tier,
    f.product_line,
    f.billing_period_start,
    f.billing_period_end,
    f.period_invoice_count                               AS duplicate_count,
    SUM(f.amount_due)                                    AS total_billed,
    MIN(f.amount_due)                                    AS expected_charge,
    SUM(f.amount_due) - MIN(f.amount_due)                AS overcharge_amount,
    STRING_AGG(f.invoice_id, ', ')                       AS invoice_ids

FROM invoice_fingerprint f
JOIN accounts a ON f.account_id = a.account_id
WHERE
    f.period_invoice_count > 1
GROUP BY
    a.account_name, a.tier, f.product_line,
    f.billing_period_start, f.billing_period_end,
    f.period_invoice_count
ORDER BY
    overcharge_amount DESC;


-- ============================================================
-- QUERY 4: CONTRACTED vs BILLED REVENUE RECONCILIATION
-- Business question: Is every account being billed at their
-- contracted rate — not under, not over?
-- ============================================================
-- Why this matters: Billing at rates that differ from the
-- signed contract is both a revenue risk (under-billing) and
-- a compliance risk (over-billing). At scale this gap can
-- represent hundreds of thousands in annual revenue leakage
-- or liability. This query surfaces every discrepancy.
-- ============================================================

WITH annualised_billing AS (
    SELECT
        account_id,
        SUM(amount_due) AS actual_arr_billed,
        COUNT(DISTINCT billing_period_start) AS periods_billed
    FROM invoices
    WHERE
        invoice_date >= DATE_TRUNC('year', CURRENT_DATE)
        AND status NOT IN ('void', 'written_off')
    GROUP BY account_id
)

SELECT
    a.account_name,
    a.tier,
    a.region,
    c.contracted_arr,
    c.billing_frequency,
    c.contract_start,
    c.contract_end,
    ab.actual_arr_billed,
    ab.periods_billed,

    -- Variance: positive = over-billed, negative = under-billed
    ab.actual_arr_billed - c.contracted_arr               AS arr_variance,

    ROUND(
        (ab.actual_arr_billed - c.contracted_arr)
        / NULLIF(c.contracted_arr, 0) * 100,
    2)                                                    AS variance_pct,

    CASE
        WHEN ABS(ab.actual_arr_billed - c.contracted_arr)
             / NULLIF(c.contracted_arr, 0) > 0.05        THEN 'REVIEW REQUIRED'
        WHEN ab.actual_arr_billed > c.contracted_arr      THEN 'OVER-BILLED'
        WHEN ab.actual_arr_billed < c.contracted_arr      THEN 'UNDER-BILLED'
        ELSE 'IN LINE'
    END                                                   AS billing_status,

    -- Flag contracts expiring within 90 days
    CASE
        WHEN c.contract_end <= CURRENT_DATE + INTERVAL '90 days'
             AND c.auto_renew = FALSE
        THEN 'RENEWAL RISK'
        ELSE NULL
    END                                                   AS renewal_flag

FROM contracts c
JOIN accounts a          ON c.account_id = a.account_id
LEFT JOIN annualised_billing ab ON c.account_id = ab.account_id
WHERE
    c.contract_end >= CURRENT_DATE
ORDER BY
    ABS(ab.actual_arr_billed - COALESCE(c.contracted_arr, 0)) DESC;


-- ============================================================
-- QUERY 5: REVENUE LEAKAGE SUMMARY DASHBOARD
-- Business question: Give me a single executive view of
-- total revenue at risk across all leakage categories.
-- ============================================================
-- Why this matters: Finance leadership and RevOps managers
-- need a single number they can act on. This query aggregates
-- all four leakage vectors — aging receivables, short pays,
-- duplicate charges, and contract variance — into one
-- prioritised summary. It is the output you present to a VP.
-- ============================================================

WITH aging AS (
    SELECT
        'Aging Receivables'                              AS leakage_type,
        COUNT(DISTINCT i.invoice_id)                     AS record_count,
        SUM(i.amount_due)                                AS amount_at_risk,
        'Invoice unpaid past due date'                   AS description
    FROM invoices i
    WHERE
        i.status NOT IN ('paid', 'void', 'written_off')
        AND CURRENT_DATE > i.due_date
),
short_pay AS (
    SELECT
        'Short Payments'                                 AS leakage_type,
        COUNT(DISTINCT i.invoice_id)                     AS record_count,
        SUM(i.amount_due - COALESCE(p.total_paid, 0))   AS amount_at_risk,
        'Invoice partially paid — balance outstanding'   AS description
    FROM invoices i
    LEFT JOIN (
        SELECT invoice_id, SUM(amount_paid) AS total_paid
        FROM payments GROUP BY invoice_id
    ) p ON i.invoice_id = p.invoice_id
    WHERE
        i.status NOT IN ('void', 'written_off')
        AND COALESCE(p.total_paid, 0) > 0
        AND COALESCE(p.total_paid, 0) < i.amount_due
),
duplicates AS (
    SELECT
        'Duplicate Charges'                              AS leakage_type,
        COUNT(*)                                         AS record_count,
        SUM(overcharge_amount)                           AS amount_at_risk,
        'Same account billed twice for same period'      AS description
    FROM (
        SELECT
            SUM(amount_due) - MIN(amount_due)            AS overcharge_amount
        FROM invoices
        WHERE status NOT IN ('void', 'written_off')
        GROUP BY account_id, product_line,
                 billing_period_start, billing_period_end
        HAVING COUNT(*) > 1
    ) dup
),
contract_variance AS (
    SELECT
        'Contract vs Billed Variance'                    AS leakage_type,
        COUNT(*)                                         AS record_count,
        SUM(ABS(actual_billed - contracted_arr))         AS amount_at_risk,
        'Billing rate differs from signed contract'      AS description
    FROM (
        SELECT
            c.contracted_arr,
            COALESCE(SUM(i.amount_due), 0)               AS actual_billed
        FROM contracts c
        LEFT JOIN invoices i
            ON c.account_id = i.account_id
            AND i.invoice_date >= DATE_TRUNC('year', CURRENT_DATE)
            AND i.status NOT IN ('void', 'written_off')
        WHERE c.contract_end >= CURRENT_DATE
        GROUP BY c.contract_id, c.contracted_arr
    ) cv
    WHERE ABS(actual_billed - contracted_arr)
          / NULLIF(contracted_arr, 0) > 0.02
)

SELECT
    leakage_type,
    record_count,
    ROUND(amount_at_risk, 2)                             AS amount_at_risk,
    description,
    ROUND(
        amount_at_risk / SUM(amount_at_risk) OVER () * 100,
    1)                                                   AS pct_of_total_risk
FROM (
    SELECT * FROM aging
    UNION ALL
    SELECT * FROM short_pay
    UNION ALL
    SELECT * FROM duplicates
    UNION ALL
    SELECT * FROM contract_variance
) combined
ORDER BY amount_at_risk DESC;


-- ============================================================
-- END OF QUERY SET
-- accordanalyst.com  |  alexis@accordanalyst.com
-- ============================================================
