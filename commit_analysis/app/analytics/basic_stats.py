from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional

from sqlalchemy import func, distinct
from app.models import db, Commit, Developer, FileChange


Granularity = Literal["day", "week", "month"]


def _time_bucket_expr(granularity: Granularity):
    # SQLite: committed_at 是 datetime
    if granularity == "day":
        return func.strftime("%Y-%m-%d", Commit.committed_at)
    if granularity == "week":
        return func.strftime("%Y-%W", Commit.committed_at)  # 年-周
    if granularity == "month":
        return func.strftime("%Y-%m", Commit.committed_at)
    raise ValueError("invalid granularity")


def activity_summary(repo_id: int, days: int = 30) -> Dict:
    end = datetime.utcnow()
    start = end - timedelta(days=int(days))

    base = db.session.query(Commit).filter(
        Commit.repo_id == repo_id,
        Commit.committed_at >= start,
        Commit.committed_at < end
    )

    total_commits = base.count()

    active_days = db.session.query(
        func.count(distinct(func.strftime("%Y-%m-%d", Commit.committed_at)))
    ).filter(
        Commit.repo_id == repo_id,
        Commit.committed_at >= start,
        Commit.committed_at < end
    ).scalar() or 0

    active_devs = db.session.query(
        func.count(distinct(Commit.developer_id))
    ).filter(
        Commit.repo_id == repo_id,
        Commit.committed_at >= start,
        Commit.committed_at < end,
        Commit.developer_id.isnot(None)
    ).scalar() or 0

    return {
        "repo_id": repo_id,
        "days": int(days),
        "start_utc": start.isoformat(timespec="seconds"),
        "end_utc": end.isoformat(timespec="seconds"),
        "total_commits": int(total_commits),
        "active_days": int(active_days),
        "active_developers": int(active_devs),
        "avg_commits_per_day": (float(total_commits) / days) if days > 0 else 0.0,
    }


def commits_trend(repo_id: int, granularity: Granularity = "day") -> List[Dict]:
    bucket = _time_bucket_expr(granularity)

    rows = db.session.query(
        bucket.label("bucket"),
        func.count(Commit.id).label("commits"),
        func.sum(Commit.insertions + Commit.deletions).label("churn"),
        func.sum(Commit.insertions).label("insertions"),
        func.sum(Commit.deletions).label("deletions"),
    ).filter(
        Commit.repo_id == repo_id
    ).group_by(
        "bucket"
    ).order_by(
        "bucket"
    ).all()

    out = []
    for b, c, churn, ins, dels in rows:
        out.append({
            "bucket": b,
            "commits": int(c or 0),
            "churn": int(churn or 0),
            "insertions": int(ins or 0),
            "deletions": int(dels or 0),
        })
    return out



def top_contributors(repo_id: int, metric: Literal["commits", "churn"] = "commits", top: int = 10) -> Dict:
    top = int(top)

    if metric == "commits":
        amount_expr = func.count(Commit.id)
    else:
        amount_expr = func.sum(Commit.insertions + Commit.deletions)

    amount_col = amount_expr.label("amount")

    rows = db.session.query(
        Commit.developer_id.label("dev_id"),
        amount_col,
    ).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    ).group_by(
        Commit.developer_id
    ).order_by(
        amount_col.desc()   # ✅ 关键：用列的 desc()，不要用 func.desc
    ).limit(top).all()

    # 总量用于算 share
    total = db.session.query(
        amount_expr
    ).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    ).scalar() or 0

    result = []
    for dev_id, amount in rows:
        dev = Developer.query.get(dev_id)
        a = int(amount or 0)
        result.append({
            "developer_id": int(dev_id),
            "name": (dev.name if dev else None),
            "email": (dev.email if dev else None),
            "amount": a,
            "share": (a / total) if total else 0.0
        })

    return {"repo_id": repo_id, "metric": metric, "top": top, "total": int(total), "items": result}
