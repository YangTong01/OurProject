from __future__ import annotations

from flask import Blueprint, request, jsonify
from app.analytics.basic_stats import activity_summary, commits_trend, top_contributors

bp = Blueprint("stats", __name__, url_prefix="/api/stats")


@bp.get("/activity")
def activity():
    repo_id = int(request.args.get("repo_id", "1"))
    days = int(request.args.get("days", "30"))
    return jsonify(activity_summary(repo_id, days))


@bp.get("/trend")
def trend():
    repo_id = int(request.args.get("repo_id", "1"))
    granularity = request.args.get("granularity", "day")
    if granularity not in ("day", "week", "month"):
        granularity = "day"
    return jsonify({"repo_id": repo_id, "granularity": granularity, "series": commits_trend(repo_id, granularity)})


@bp.get("/top_contributors")
def top():
    repo_id = int(request.args.get("repo_id", "1"))
    metric = request.args.get("metric", "commits")
    if metric not in ("commits", "churn"):
        metric = "commits"
    top_n = int(request.args.get("top", "10"))
    return jsonify(top_contributors(repo_id, metric, top_n))
