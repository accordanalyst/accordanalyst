# Portfolio — accordanalyst.com


TL;DR: Found out that accordanalyst.systems exist as a domain name and my ass needs to get it. This realm will not rest until I can put **accordanalyst.sys** as me domain name. I will concur all the worlds with my unhinged but seemingly professional naming conventions. Just you watch.

Don't ask too many questions about why "accordanalyst.com" ain't working. Nothing has humbled me most than me forgetting half of my teenage coding years. To be a millennial that grew up on nothing but Xanga, LiveJournal, Myspace and early Tumblr coding has brought me the most craziest realization of "Damn I have to start from ALMOST scratch?"

That's the other reason why I hosted this on Netlify, I have to re-learn the sections of coding I forgotten, backwards. Not everyone can learn something backwards and that's literally been my entire life lesson at this point. Gollyyyyyy ugh.

Anyway, back to scheduled programming, my bad.

This repo contains the case studies and supporting files behind my portfolio site. Everything here is simulated data built to mirror real-world workflows — no client or proprietary data is used anywhere in this repository.

---

## Why Netlify

This site is hosted on Netlify for the convenience of it: connect the repo, push to `main`, and the live site updates automatically — no manual upload step, no server to manage, no build pipeline to babysit. For a static, mostly-HTML portfolio like this one, that kind of zero-friction deploy is exactly what's needed: I can focus on the projects themselves rather than infrastructure. Netlify's free tier also covers everything a personal portfolio site needs (custom domain support, HTTPS by default, instant rollbacks if a deploy ever breaks something), so there's no real reason to reach for anything heavier.

---

## What's in this repo

### Case studies (HTML)

| File | What it is |
|---|---|
| `freight-audit-dashboard.html` | An interactive recovery dashboard built around 200,000+ simulated invoices across a freight audit portfolio with heavy international exposure. Tracks pre-audit vs. post-audit recovery rates month over month, with seasonal context (Chinese New Year disruption, European summer slowdown, peak-season volume spikes) baked into the simulated data so the numbers move the way they actually would in a real freight audit operation. |
| `intl-freight-audit.html` | The write-up for a simulated multi-sheet Excel system modeling international freight audit workflows — Ocean (LCL, FCL 20', FCL 40') and Air, with per-account tolerance rules, demurrage calculation, spot quote handling, and short-pay detection, rolled up into an executive dashboard view. |
| `revenue-anomaly-detector.html` | The write-up for a Python-based statistical anomaly detector that flags accounts whose monthly revenue deviates from their own historical pattern — catching sudden spikes, sudden drops, and slow erosion trends that wouldn't trip a simple month-over-month check. |
| `revenue-reconciliation.html` | The write-up for a five-query SQL set covering the most common revenue leakage points in a SaaS billing environment: aging receivables, short payments, duplicate charges, and contract-vs-billed variance, rolled into one executive leakage summary. |

Each HTML file is a self-contained case study page — dark/light theme toggle, KPI strip, and (where relevant) a live interactive dashboard rendered with D3.

### Supporting source files

| File | What it is |
|---|---|
| `anomaly_detector.py` | The actual Python script behind the Revenue Anomaly Detector case study — rolling baseline + z-score detection, an erosion check for slow declines, severity scoring, and a styled matplotlib chart export. |
| `revenue_reconciliation.sql` | The actual SQL query set behind the Revenue Reconciliation case study — five standalone queries (aging receivables, payment shortfalls, duplicate charges, contract variance, and the rolled-up executive summary) against a simulated SaaS billing schema. |
| `Freight_Audit_Recovery_Dashboard_v5.xlsx` | The underlying simulated dataset and workbook behind the freight audit recovery dashboard. |
| `Freight_Audit_Automation_CaseStudy.xlsx` | The supporting workbook for the freight audit automation case study. |
| `Intl_Freight_Audit_CaseStudy.xlsx` | The supporting multi-sheet workbook for the international freight audit case study (Ocean/Air tolerance rules, demurrage, spot quotes). |

---

## A note on the data

Every dataset in this repo — invoice volumes, revenue figures, account names, billing records — is simulated. None of it reflects any real company, client, or employer. The goal of each project is to demonstrate how a given analysis or system would be built and reasoned through, using data engineered to behave the way real-world data does (seasonality, edge cases, the occasional messy outlier) without using anyone's actual numbers.
