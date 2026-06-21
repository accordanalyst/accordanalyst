"""
Revenue Anomaly Detector
=========================
Business question: Which accounts had a revenue month that doesn't
match their own historical pattern — and how severe is the deviation?

Method: For each account, compute a rolling mean and rolling standard
deviation of trailing months. Flag any month where actual revenue
falls outside a z-score threshold of that account's own trailing
baseline. This catches sudden drops, sudden spikes, and (via a
secondary trend-slope check) slow erosion that no single month would
trigger on its own.

All data is simulated — see generate_data.py for the seeded scenarios.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ── CONFIG ──────────────────────────────────────────────────────────
ROLLING_WINDOW   = 6      # trailing months used to establish each account's baseline
Z_SCORE_THRESHOLD = 2.5   # months beyond this many std deviations are flagged
EROSION_WINDOW    = 6     # months used to detect slow decline trend
EROSION_THRESHOLD = -0.30 # cumulative % decline over the window to flag as erosion

df = pd.read_csv("monthly_revenue.csv")
df["month"] = pd.to_datetime(df["month"])
df = df.sort_values(["account", "month"]).reset_index(drop=True)


def compute_anomalies(group: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling baseline, z-score, and anomaly flags for one account."""
    g = group.copy()
    g["rolling_mean"] = g["revenue"].rolling(ROLLING_WINDOW, min_periods=5).mean().shift(1)
    g["rolling_std"]  = g["revenue"].rolling(ROLLING_WINDOW, min_periods=5).std().shift(1)

    # Floor the std at a small % of the rolling mean — prevents z-score blowup
    # when a few trailing months happen to be unusually flat
    std_floor = g["rolling_mean"] * 0.03
    g["rolling_std"] = g["rolling_std"].clip(lower=std_floor)

    g["z_score"] = (g["revenue"] - g["rolling_mean"]) / g["rolling_std"]
    g["z_score"] = g["z_score"].replace([np.inf, -np.inf], np.nan)

    g["pct_vs_baseline"] = (g["revenue"] - g["rolling_mean"]) / g["rolling_mean"] * 100

    # Point anomaly: this month's revenue is statistically far from the trailing baseline
    g["point_anomaly"] = g["z_score"].abs() >= Z_SCORE_THRESHOLD

    # Erosion check: cumulative decline over trailing window even if no single
    # month trips the z-score threshold
    g["erosion_pct"] = g["revenue"].pct_change(periods=EROSION_WINDOW)
    g["erosion_flag"] = g["erosion_pct"] <= EROSION_THRESHOLD

    g["anomaly_type"] = np.select_dtype = None
    conditions = []
    labels = []

    def classify(row):
        # Point anomalies (single dramatic month) take priority over erosion
        # since a sudden drop or spike is more urgent than a gradual trend
        if row["point_anomaly"] and row["z_score"] > 0:
            return "SPIKE"
        elif row["point_anomaly"] and row["z_score"] < 0:
            return "DROP"
        elif row["erosion_flag"]:
            return "EROSION"
        else:
            return "NORMAL"

    g["anomaly_type"] = g.apply(classify, axis=1)

    # Severity score: combines magnitude of z-score and % deviation
    # so the most actionable anomalies surface to the top regardless of type
    g["severity_score"] = np.where(
        g["anomaly_type"] == "EROSION",
        g["erosion_pct"].abs() * 100,
        g["z_score"].abs().fillna(0)
    )

    return g


results = df.groupby("account", group_keys=False)[df.columns].apply(compute_anomalies)
results = results.reset_index(drop=True)

# ── BUILD ANOMALY REPORT ────────────────────────────────────────────
anomalies = results[results["anomaly_type"] != "NORMAL"].copy()
anomalies = anomalies.sort_values("severity_score", ascending=False)

report_cols = ["account", "month", "revenue", "rolling_mean", "pct_vs_baseline",
                "z_score", "anomaly_type", "severity_score"]
anomaly_report = anomalies[report_cols].copy()
anomaly_report["month"] = anomaly_report["month"].dt.strftime("%Y-%m")
anomaly_report = anomaly_report.round({
    "revenue": 2, "rolling_mean": 2, "pct_vs_baseline": 1,
    "z_score": 2, "severity_score": 2
})

anomaly_report.to_csv("anomaly_report.csv", index=False)

print("=" * 78)
print("REVENUE ANOMALY DETECTION REPORT")
print("=" * 78)
print(f"Accounts analyzed: {df['account'].nunique()}")
print(f"Months analyzed:   {df['month'].nunique()}")
print(f"Anomalies flagged: {len(anomaly_report)}")
print()
print(anomaly_report.head(15).to_string(index=False))
print()
print(f"Full report saved to anomaly_report.csv")

# ── SUMMARY BY TYPE ──────────────────────────────────────────────────
summary = anomaly_report.groupby("anomaly_type").agg(
    count=("account", "count"),
    avg_severity=("severity_score", "mean"),
    accounts_affected=("account", "nunique")
).round(2)
print()
print("Summary by anomaly type:")
print(summary.to_string())

# ── PRIORITY TIERS — for executive triage ───────────────────────────
def priority_tier(score, atype):
    if atype == "EROSION":
        if score >= 40: return "HIGH"
        elif score >= 20: return "MEDIUM"
        else: return "LOW"
    else:  # SPIKE or DROP — z-score based
        if score >= 10: return "HIGH"
        elif score >= 4: return "MEDIUM"
        else: return "LOW"

anomaly_report["priority"] = anomaly_report.apply(
    lambda r: priority_tier(r["severity_score"], r["anomaly_type"]), axis=1
)
anomaly_report.to_csv("anomaly_report.csv", index=False)

priority_summary = anomaly_report["priority"].value_counts().reindex(["HIGH","MEDIUM","LOW"]).fillna(0).astype(int)
print()
print("Priority tier breakdown:")
print(priority_summary.to_string())
high_priority_accounts = anomaly_report[anomaly_report["priority"]=="HIGH"]["account"].nunique()
print(f"\n{high_priority_accounts} accounts require immediate review (HIGH priority)")

# ── CHART: TOP 4 FLAGGED ACCOUNTS ───────────────────────────────────
# Styled with gradient area fills, glowing anomaly markers, and a
# cleaner dark-friendly aesthetic — built around the fall palette
# (espresso / burnt orange / amber) rather than literal stock colors.
top_accounts = anomaly_report.drop_duplicates("account").head(4)["account"].tolist()

ESPRESSO  = "#3B2207"
AMBER     = "#7A5C2E"
BURNT     = "#C4621D"
CREAM     = "#FDF3E7"
PANEL_BG  = "#2A1A0E"   # deep warm dark panel, not pure black
GRID_CLR  = "#4A3520"

colors = {"SPIKE": "#E8956D", "DROP": "#FF6B5B", "EROSION": "#F0C070"}
glow_colors = {"SPIKE": "#E8956D", "DROP": "#FF6B5B", "EROSION": "#F0C070"}

fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
fig.suptitle("Revenue Trend — Top Flagged Accounts", fontsize=15,
             fontweight="bold", color=CREAM, y=0.99)

for ax, acct in zip(axes.flat, top_accounts):
    acct_data = results[results["account"] == acct].sort_values("month")
    x = acct_data["month"]
    y = acct_data["revenue"]
    baseline = acct_data["rolling_mean"]

    # Gradient area fill beneath the revenue line
    y_min = ax.get_ylim()[0]
    grad = ax.fill_between(x, y, y.min() * 0.85, color=BURNT, alpha=0.0)
    # Build a vertical gradient via imshow clipped to the fill path
    n = 256
    grad_img = np.linspace(0, 1, n).reshape(n, 1)
    extent = [mdates.date2num(x.min()), mdates.date2num(x.max()),
              y.min() * 0.85, y.max() * 1.05]
    im = ax.imshow(grad_img, extent=extent, aspect="auto", origin="lower",
                    cmap=plt.cm.colors.LinearSegmentedColormap.from_list(
                        "fade", [(0.18,0.10,0.04,0.0), (0.77,0.38,0.11,0.38)]
                    ), zorder=1)
    im.set_clip_path(grad.get_paths()[0] if grad.get_paths() else None,
                      transform=ax.transData)
    grad.remove()

    # Rolling baseline — soft dashed line behind the main trend
    ax.plot(x, baseline, color=AMBER, linewidth=1.3, linestyle=(0, (4, 3)),
             alpha=0.85, label="Rolling Baseline", zorder=2)

    # Main revenue line — smooth, bold, in cream against the dark panel
    ax.plot(x, y, color=CREAM, linewidth=2.2, label="Revenue",
             zorder=4, solid_capstyle="round")

    # Glowing anomaly markers — layered scatter for a soft glow effect
    flagged = acct_data[acct_data["anomaly_type"] != "NORMAL"]
    for atype in flagged["anomaly_type"].unique():
        subset = flagged[flagged["anomaly_type"] == atype]
        c = glow_colors.get(atype, "#FFFFFF")
        # Outer glow layers (progressively larger, more transparent)
        for size, alpha in [(420, 0.06), (260, 0.10), (140, 0.18)]:
            ax.scatter(subset["month"], subset["revenue"], color=c,
                       s=size, alpha=alpha, zorder=4, linewidths=0)
        # Solid core dot on top
        ax.scatter(subset["month"], subset["revenue"], color=c, s=55,
                   zorder=6, label=atype, edgecolors=ESPRESSO, linewidths=0.8)

    ax.set_title(acct, fontsize=12, fontweight="bold", color=CREAM, pad=10)
    ax.set_ylabel("Monthly Revenue ($)", fontsize=8.5, color="#C4A882")
    ax.tick_params(axis="x", rotation=45, labelsize=7, colors="#A8927A")
    ax.tick_params(axis="y", labelsize=8, colors="#A8927A")
    leg = ax.legend(fontsize=7, loc="upper left", framealpha=0.25,
                     facecolor=PANEL_BG, edgecolor=GRID_CLR, labelcolor=CREAM)
    ax.grid(alpha=0.15, color=GRID_CLR, linewidth=0.6)
    ax.set_facecolor(PANEL_BG)
    for spine in ax.spines.values():
        spine.set_color(GRID_CLR)
        spine.set_linewidth(0.8)

fig.patch.set_facecolor(ESPRESSO)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("anomaly_chart.png", dpi=150, bbox_inches="tight",
            facecolor=ESPRESSO)
print("\nChart saved to anomaly_chart.png")
