import json
import os
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]  # 项目根目录 OPEN/
OUT_DIR = ROOT / "reports" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 你导出的 JSON 文件（按你的实际文件名）
ACTIVITY_JSON = ROOT / "activity_repo1.json"
TREND_JSON = ROOT / "trend_month_repo1.json"
TOP_JSON = ROOT / "top_contributors_repo1.json"
SUMMARY_JSON = ROOT / "contributors_summary_repo1.json"


def load_json(p: Path):
    with open(p, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_fig(filename: str):
    out_path = OUT_DIR / filename
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[OK] saved: {out_path}")


def plot_trend_commits(trend):
    series = trend["series"]
    months = [x["bucket"] for x in series]
    commits = [x["commits"] for x in series]

    plt.figure(figsize=(10, 4))
    plt.plot(months, commits, marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Month")
    plt.ylabel("Commits")
    plt.title("Commit Trend (Monthly)")
    save_fig("trend_commits_month.png")


def plot_trend_churn(trend):
    series = trend["series"]
    months = [x["bucket"] for x in series]
    churn = [x["churn"] for x in series]

    plt.figure(figsize=(10, 4))
    plt.plot(months, churn, marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Month")
    plt.ylabel("Churn (insertions + deletions)")
    plt.title("Churn Trend (Monthly)")
    save_fig("trend_churn_month.png")


def plot_top_contributors(top):
    items = top["items"]

    names = []
    amounts = []
    for x in items:
        name = x.get("name") or x.get("email") or f"dev#{x.get('developer_id')}"
        names.append(name)
        amounts.append(x["amount"])

    plt.figure(figsize=(10, 4))
    plt.bar(names, amounts)
    plt.xticks(rotation=30, ha="right")
    plt.xlabel("Developer")
    plt.ylabel(f"Amount ({top['metric']})")
    plt.title(f"Top Contributors (Top-{top['top']})")
    save_fig("top_contributors.png")


def plot_community(summary):
    community = summary["community"]
    months = community["months"]

    active = [x["active_devs"] for x in community["active_devs_by_month"]]
    new_devs = [x["new_devs"] for x in community["new_devs_by_month"]]
    lost_devs = [x["lost_devs"] for x in community["lost_devs_by_month"]]

    plt.figure(figsize=(10, 4))
    plt.plot(months, active, marker="o", label="active_devs")
    plt.plot(months, new_devs, marker="o", label="new_devs")
    plt.plot(months, lost_devs, marker="o", label="lost_devs")

    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Month")
    plt.ylabel("Developers")
    plt.title("Community Structure: Active/New/Lost Developers (Monthly)")
    plt.legend()
    save_fig("community_active_new_lost.png")


def export_kpi_text(activity, summary):
    """
    附赠：输出一个 KPI 文本文件，写报告可直接复制
    """
    core_cov = summary["core_team"]["coverage"]
    top10_share = summary["concentration"]["top10_share"]
    gini = summary["concentration"]["gini"]
    hhi = summary["concentration"]["hhi"]

    txt = []
    txt.append("=== KPI Summary ===")
    txt.append(f"Total commits: {activity['total_commits']}")
    txt.append(f"Active days: {activity['active_days']}")
    txt.append(f"Active developers: {activity['active_developers']}")
    txt.append(f"Avg commits/day: {activity['avg_commits_per_day']:.3f}")
    txt.append("")
    txt.append(f"Core team coverage (Top-{summary['core_team']['top_n']}): {core_cov:.4f}")
    txt.append(f"Top10 share: {top10_share:.4f}")
    txt.append(f"Gini: {gini:.4f}")
    txt.append(f"HHI: {hhi:.4f}")

    out_path = OUT_DIR / "kpi_summary.txt"
    out_path.write_text("\n".join(txt), encoding="utf-8")
    print(f"[OK] saved: {out_path}")


def main():
    # 检查文件是否存在
    for p in [ACTIVITY_JSON, TREND_JSON, TOP_JSON, SUMMARY_JSON]:
        if not p.exists():
            raise FileNotFoundError(f"Missing file: {p}")

    activity = load_json(ACTIVITY_JSON)
    trend = load_json(TREND_JSON)
    top = load_json(TOP_JSON)
    summary = load_json(SUMMARY_JSON)

    plot_trend_commits(trend)
    plot_trend_churn(trend)
    plot_top_contributors(top)
    plot_community(summary)
    export_kpi_text(activity, summary)

    print("\nAll figures exported ")


if __name__ == "__main__":
    main()
