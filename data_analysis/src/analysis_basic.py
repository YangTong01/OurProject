import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from .utils import ensure_dir


def classify_commit_message(msg: str) -> str:
    """
    Simple rule-based commit type classification.
    """
    m = (msg or "").lower()

    if any(k in m for k in ["fix", "bug", "error", "issue", "hotfix"]):
        return "fix"
    if any(k in m for k in ["add", "feature", "feat", "implement", "support"]):
        return "feat"
    if any(k in m for k in ["doc", "docs", "readme", "documentation"]):
        return "doc"
    if "test" in m:
        return "test"
    if any(k in m for k in ["refactor", "cleanup", "reformat", "style"]):
        return "refactor"
    if any(k in m for k in ["ci", "build", "chore", "deps", "dependency", "bump"]):
        return "chore"
    return "other"


def plot_series(x, y, title, xlabel, ylabel, outpath):
    plt.figure()
    plt.plot(x, y)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(outpath, dpi=200)
    plt.close()


def plot_bar(labels, values, title, xlabel, ylabel, outpath):
    plt.figure()
    plt.bar(labels, values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(outpath, dpi=200)
    plt.close()


def plot_stacked_bar(x, y1, y2, label1, label2, title, xlabel, ylabel, outpath):
    plt.figure()
    plt.bar(x, y1, label=label1)
    plt.bar(x, y2, bottom=y1, label=label2)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath, dpi=200)
    plt.close()


def run_basic_analysis(input_csv: str, fig_dir: str, stats_out: str = None):
    """
    Run basic stats:
    - monthly commits
    - monthly contributors
    - monthly insertions/deletions
    - commit type overall + monthly trend
    - weekend ratio
    Output figures into fig_dir
    """
    ensure_dir(fig_dir)
    df = pd.read_csv(input_csv)
    df["date"] = pd.to_datetime(df["date"])

    # ---------- Activity trend ----------
    monthly_commits = df.groupby("month").size()
    plot_series(
        monthly_commits.index,
        monthly_commits.values,
        "Monthly Commits",
        "Month",
        "Commits",
        str(Path(fig_dir) / "monthly_commits.png")
    )

    monthly_contributors = df.groupby("month")["author_name"].nunique()
    plot_series(
        monthly_contributors.index,
        monthly_contributors.values,
        "Monthly Active Contributors",
        "Month",
        "Contributors",
        str(Path(fig_dir) / "monthly_contributors.png")
    )

    # ---------- Insertions & deletions ----------
    monthly_insertions = df.groupby("month")["insertions"].sum()
    monthly_deletions = df.groupby("month")["deletions"].sum()

    # stacked bars (insertions + deletions)
    plot_stacked_bar(
        monthly_insertions.index,
        monthly_insertions.values,
        monthly_deletions.values,
        "Insertions",
        "Deletions",
        "Monthly Code Changes (Insertions & Deletions)",
        "Month",
        "Lines",
        str(Path(fig_dir) / "monthly_insertions_deletions.png")
    )

    # ---------- Commit type analysis ----------
    df["commit_type"] = df["message"].apply(classify_commit_message)

    type_counts = df["commit_type"].value_counts()
    plot_bar(
        type_counts.index,
        type_counts.values,
        "Commit Type (Overall)",
        "Type",
        "Count",
        str(Path(fig_dir) / "commit_type_overall.png")
    )

    # monthly commit type stacked
    pivot = df.pivot_table(index="month", columns="commit_type", values="hash", aggfunc="count").fillna(0)
    pivot = pivot.sort_index()

    plt.figure()
    bottom = None
    for col in pivot.columns:
        if bottom is None:
            plt.bar(pivot.index, pivot[col], label=col)
            bottom = pivot[col].values
        else:
            plt.bar(pivot.index, pivot[col], bottom=bottom, label=col)
            bottom = bottom + pivot[col].values

    plt.title("Monthly Commit Types")
    plt.xlabel("Month")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    plt.savefig(str(Path(fig_dir) / "commit_type_monthly.png"), dpi=200)
    plt.close()

    # ---------- Weekend ratio ----------
    weekend_ratio = df["is_weekend"].mean()
    weekday_ratio = 1 - weekend_ratio

    plt.figure()
    plt.bar(["Weekday", "Weekend"], [weekday_ratio, weekend_ratio])
    plt.title("Weekend vs Weekday Commit Ratio")
    plt.ylabel("Ratio")
    plt.tight_layout()
    plt.savefig(str(Path(fig_dir) / "weekend_ratio.png"), dpi=200)
    plt.close()

    # ---------- Stats output ----------
    stats = {
        "total_commits": int(len(df)),
        "time_range_start": str(df["date"].min()),
        "time_range_end": str(df["date"].max()),
        "total_contributors": int(df["author_name"].nunique()),
        "weekend_ratio": float(weekend_ratio),
        "top_5_months_by_commits": monthly_commits.sort_values(ascending=False).head(5).to_dict(),
        "top_10_contributors": df["author_name"].value_counts().head(10).to_dict(),
        "commit_type_counts": type_counts.to_dict()
    }

    if stats_out:
        ensure_dir(str(Path(stats_out).parent))
        pd.Series(stats).to_json(stats_out, force_ascii=False, indent=2)

    return stats
