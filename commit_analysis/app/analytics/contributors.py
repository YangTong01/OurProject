from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional, Tuple

from dateutil import parser as date_parser
from sqlalchemy import func, distinct
from app.models import db, Commit, Developer, FileChange


Metric = Literal["commits", "churn"]


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    dt = date_parser.isoparse(s)
    # 统一用 naive datetime（UTC 语义），与 committed_at 一致
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


def _end_exclusive(end: Optional[datetime]) -> Optional[datetime]:
    # 用户传 end=2024-01-01 时，通常期望包含这一天；这里用 “次日 00:00” 作为排他上界
    if end is None:
        return None
    return end + timedelta(days=1)


def _month_bucket_expr():
    # SQLite: 'YYYY-MM'
    return func.strftime("%Y-%m", Commit.committed_at)


def _metric_amount_expr(metric: Metric):
    if metric == "commits":
        return func.count(Commit.id)
    return func.sum(Commit.insertions + Commit.deletions)


def _query_commits_filtered(repo_id: int, start: Optional[datetime], end_excl: Optional[datetime]):
    q = db.session.query(Commit).filter(Commit.repo_id == repo_id)
    if start is not None:
        q = q.filter(Commit.committed_at >= start)
    if end_excl is not None:
        q = q.filter(Commit.committed_at < end_excl)
    return q


def _dev_amounts(repo_id: int, metric: Metric, start: Optional[datetime], end_excl: Optional[datetime]) -> List[Tuple[int, int]]:
    """
    返回 [(developer_id, amount_int), ...] 按 amount 降序
    """
    amount_expr = _metric_amount_expr(metric)
    amount_col = amount_expr.label("amount")

    q = db.session.query(
        Commit.developer_id.label("dev_id"),
        amount_col
    ).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    )

    if start is not None:
        q = q.filter(Commit.committed_at >= start)
    if end_excl is not None:
        q = q.filter(Commit.committed_at < end_excl)

    rows = q.group_by(Commit.developer_id).order_by(amount_col.desc()).all()

    out: List[Tuple[int, int]] = []
    for dev_id, amount in rows:
        out.append((int(dev_id), int(amount or 0)))
    return out


def _total_amount(repo_id: int, metric: Metric, start: Optional[datetime], end_excl: Optional[datetime]) -> int:
    amount_expr = _metric_amount_expr(metric)

    q = db.session.query(amount_expr).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    )
    if start is not None:
        q = q.filter(Commit.committed_at >= start)
    if end_excl is not None:
        q = q.filter(Commit.committed_at < end_excl)

    total = q.scalar() or 0
    return int(total)


def _gini(amounts: List[int]) -> float:
    # Gini for non-negative amounts
    xs = [x for x in amounts if x is not None]
    if not xs:
        return 0.0
    xs = sorted(xs)
    n = len(xs)
    s = sum(xs)
    if s == 0:
        return 0.0
    # G = (2*sum(i*x_i)/(n*sum(x))) - (n+1)/n
    num = 0
    for i, x in enumerate(xs, start=1):
        num += i * x
    g = (2 * num) / (n * s) - (n + 1) / n
    return float(max(0.0, min(1.0, g)))


def _hhi(amounts: List[int]) -> float:
    s = sum(amounts)
    if s <= 0:
        return 0.0
    h = 0.0
    for a in amounts:
        share = a / s
        h += share * share
    return float(h)


def _month_range(repo_id: int, start: Optional[datetime], end_excl: Optional[datetime]) -> Tuple[Optional[str], Optional[str]]:
    """
    返回过滤窗口内 commit 的 min/max 月份 bucket（YYYY-MM）。
    """
    bucket = _month_bucket_expr()

    q = db.session.query(
        func.min(bucket),
        func.max(bucket)
    ).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    )
    if start is not None:
        q = q.filter(Commit.committed_at >= start)
    if end_excl is not None:
        q = q.filter(Commit.committed_at < end_excl)

    mn, mx = q.first() or (None, None)
    return mn, mx


def _iter_months(mn: str, mx: str) -> List[str]:
    # mn/mx: 'YYYY-MM'
    y1, m1 = map(int, mn.split("-"))
    y2, m2 = map(int, mx.split("-"))
    months = []
    y, m = y1, m1
    while (y < y2) or (y == y2 and m <= m2):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m = 1
            y += 1
    return months


def _add_month(yyyy_mm: str, k: int) -> str:
    y, m = map(int, yyyy_mm.split("-"))
    total = (y * 12 + (m - 1)) + k
    y2 = total // 12
    m2 = total % 12 + 1
    return f"{y2:04d}-{m2:02d}"


def _community_timeseries(repo_id: int, start: Optional[datetime], end_excl: Optional[datetime], churn_window_months: int = 2) -> Dict:
    bucket = _month_bucket_expr()

    # 月活跃开发者数
    q = db.session.query(
        bucket.label("month"),
        func.count(distinct(Commit.developer_id)).label("active_devs"),
        func.count(Commit.id).label("commits"),
        func.sum(Commit.insertions + Commit.deletions).label("churn")
    ).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    )
    if start is not None:
        q = q.filter(Commit.committed_at >= start)
    if end_excl is not None:
        q = q.filter(Commit.committed_at < end_excl)

    rows = q.group_by("month").order_by("month").all()

    # 每个开发者 first/last 活跃月
    q2 = db.session.query(
        Commit.developer_id.label("dev_id"),
        func.min(bucket).label("first_month"),
        func.max(bucket).label("last_month"),
    ).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    )
    if start is not None:
        q2 = q2.filter(Commit.committed_at >= start)
    if end_excl is not None:
        q2 = q2.filter(Commit.committed_at < end_excl)

    dev_months = q2.group_by(Commit.developer_id).all()

    mn, mx = _month_range(repo_id, start, end_excl)
    if not mn or not mx:
        return {
            "months": [],
            "active_devs_by_month": [],
            "new_devs_by_month": [],
            "lost_devs_by_month": [],
            "churn_window_months": int(churn_window_months),
        }

    all_months = _iter_months(mn, mx)

    active_map = {r[0]: int(r[1] or 0) for r in rows}
    commits_map = {r[0]: int(r[2] or 0) for r in rows}
    churn_map = {r[0]: int(r[3] or 0) for r in rows}

    # 新贡献者：first_month 计数
    new_map: Dict[str, int] = {}
    for dev_id, first_m, last_m in dev_months:
        if first_m:
            new_map[first_m] = new_map.get(first_m, 0) + 1

    # 流失贡献者（近似定义，适合课程项目）：
    # 若某 dev 的 last_month = L，则在 L + churn_window_months 这个月记为 “lost +1”
    # 直观解释：连续 K 月未再出现，则认为流失。
    lost_map: Dict[str, int] = {}
    for dev_id, first_m, last_m in dev_months:
        if not last_m:
            continue
        lost_m = _add_month(last_m, int(churn_window_months))
        # 只统计落在分析时间范围内的月份
        if lost_m >= mn and lost_m <= _add_month(mx, int(churn_window_months)):
            lost_map[lost_m] = lost_map.get(lost_m, 0) + 1

    series_active = []
    series_new = []
    series_lost = []

    for m in all_months:
        series_active.append({
            "month": m,
            "active_devs": active_map.get(m, 0),
            "commits": commits_map.get(m, 0),
            "churn": churn_map.get(m, 0),
        })
        series_new.append({"month": m, "new_devs": new_map.get(m, 0)})
        series_lost.append({"month": m, "lost_devs": lost_map.get(m, 0)})

    return {
        "months": all_months,
        "active_devs_by_month": series_active,
        "new_devs_by_month": series_new,
        "lost_devs_by_month": series_lost,
        "churn_window_months": int(churn_window_months),
        "min_month": mn,
        "max_month": mx,
    }


def _collaboration_network(repo_id: int, start: Optional[datetime], end_excl: Optional[datetime], top_edges: int = 50) -> Dict:
    """
    可选加分：协作网络（简化版）
    定义：如果两个开发者都改动过同一个文件，则认为有协作边；权重=共同改动文件数。
    注意：这是“总体共改文件”的简化网络，不做复杂时间窗/同一时间段共改。
    """
    # 取 (file_path, developer_id) 去重集合
    q = db.session.query(
        FileChange.file_path,
        Commit.developer_id
    ).join(
        Commit, Commit.id == FileChange.commit_id
    ).filter(
        Commit.repo_id == repo_id,
        Commit.developer_id.isnot(None)
    )

    if start is not None:
        q = q.filter(Commit.committed_at >= start)
    if end_excl is not None:
        q = q.filter(Commit.committed_at < end_excl)

    rows = q.distinct().all()

    # file -> list(dev)
    file_to_devs: Dict[str, List[int]] = {}
    for fp, dev_id in rows:
        fp = str(fp)
        did = int(dev_id)
        file_to_devs.setdefault(fp, []).append(did)

    # 生成边：对每个文件，dev 列表两两组合
    edge_w: Dict[Tuple[int, int], int] = {}
    for fp, devs in file_to_devs.items():
        devs = sorted(set(devs))
        if len(devs) < 2:
            continue
        for i in range(len(devs)):
            for j in range(i + 1, len(devs)):
                a, b = devs[i], devs[j]
                edge_w[(a, b)] = edge_w.get((a, b), 0) + 1

    # top edges
    items = sorted(edge_w.items(), key=lambda x: x[1], reverse=True)[: int(top_edges)]

    # 补充开发者信息
    edges = []
    for (a, b), w in items:
        da = Developer.query.get(a)
        dbv = Developer.query.get(b)
        edges.append({
            "a_id": a, "a_name": da.name if da else None, "a_email": da.email if da else None,
            "b_id": b, "b_name": dbv.name if dbv else None, "b_email": dbv.email if dbv else None,
            "weight_common_files": int(w),
        })

    return {
        "type": "cochange_same_file_overall",
        "top_edges": int(top_edges),
        "edges": edges,
        "nodes": len({x for e in edge_w.keys() for x in e}),
    }


def contributors_summary(
    repo_id: int,
    metric: Metric = "commits",
    top: int = 10,
    start: Optional[str] = None,
    end: Optional[str] = None,
    churn_window_months: int = 2,
    include_network: bool = False,
    network_top_edges: int = 50
) -> Dict:
    start_dt = _parse_date(start)
    end_dt_excl = _end_exclusive(_parse_date(end))

    # 贡献量分布
    pairs = _dev_amounts(repo_id, metric, start_dt, end_dt_excl)
    amounts = [a for _, a in pairs]
    total = _total_amount(repo_id, metric, start_dt, end_dt_excl)

    # Core team：Top-N + 覆盖率
    top_n = int(top)
    core_pairs = pairs[:top_n]
    core_sum = sum(a for _, a in core_pairs)
    core_share = (core_sum / total) if total else 0.0

    core_items = []
    for dev_id, amt in core_pairs:
        dev = Developer.query.get(dev_id)
        core_items.append({
            "developer_id": dev_id,
            "name": dev.name if dev else None,
            "email": dev.email if dev else None,
            "amount": int(amt),
            "share": (amt / total) if total else 0.0
        })

    # Concentration：Top10 share / Gini / HHI
    top10_sum = sum(a for _, a in pairs[:10])
    top10_share = (top10_sum / total) if total else 0.0
    gini = _gini(amounts)
    hhi = _hhi(amounts)

    # Community structure：月活跃/新/流失
    community = _community_timeseries(
        repo_id=repo_id,
        start=start_dt,
        end_excl=end_dt_excl,
        churn_window_months=int(churn_window_months)
    )

    # 可选协作网络
    network = None
    if include_network:
        network = _collaboration_network(
            repo_id=repo_id,
            start=start_dt,
            end_excl=end_dt_excl,
            top_edges=int(network_top_edges)
        )

    return {
        "repo_id": int(repo_id),
        "params": {
            "metric": metric,
            "top": int(top),
            "start": start,
            "end": end,
            "churn_window_months": int(churn_window_months),
            "include_network": bool(include_network),
            "network_top_edges": int(network_top_edges),
        },
        "core_team": {
            "definition": f"Top-{top_n} by {metric}",
            "top_n": int(top_n),
            "coverage": float(core_share),
            "core_amount": int(core_sum),
            "total_amount": int(total),
            "members": core_items,
        },
        "concentration": {
            "top10_share": float(top10_share),
            "gini": float(gini),
            "hhi": float(hhi),
            "total_amount": int(total),
            "n_developers": int(len(amounts)),
        },
        "community": community,
        "collaboration_network": network,
    }
