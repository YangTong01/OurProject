from __future__ import annotations

from flask import Blueprint, request, jsonify
from app.analytics.contributors import contributors_summary

bp = Blueprint("contributors", __name__, url_prefix="/api/contributors")


@bp.get("/summary")
def summary():
    repo_id = int(request.args.get("repo_id", "1"))
    metric = request.args.get("metric", "commits")
    if metric not in ("commits", "churn"):
        metric = "commits"

    top = int(request.args.get("top", "10"))
    start = request.args.get("start")  # ISO date, e.g. 2024-01-01
    end = request.args.get("end")      # ISO date, e.g. 2024-12-31

    churn_window_months = int(request.args.get("churn_window_months", "2"))

    include_network = request.args.get("include_network", "false").lower() in ("1", "true", "yes", "y")
    network_top_edges = int(request.args.get("network_top_edges", "50"))

    data = contributors_summary(
        repo_id=repo_id,
        metric=metric,
        top=top,
        start=start,
        end=end,
        churn_window_months=churn_window_months,
        include_network=include_network,
        network_top_edges=network_top_edges,
    )
    return jsonify(data)
