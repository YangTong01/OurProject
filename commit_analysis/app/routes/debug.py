from flask import Blueprint, jsonify
from app.models import Commit

bp = Blueprint("debug", __name__, url_prefix="/api/debug")

@bp.get("/counts")
def counts():
    return jsonify({
        "commits": Commit.query.count(),
    })

@bp.get("/time_range")
def time_range():
    # 最早/最晚提交时间
    min_dt = Commit.query.with_entities(Commit.committed_at).order_by(Commit.committed_at.asc()).first()
    max_dt = Commit.query.with_entities(Commit.committed_at).order_by(Commit.committed_at.desc()).first()
    return jsonify({
        "min_committed_at": min_dt[0].isoformat() if min_dt and min_dt[0] else None,
        "max_committed_at": max_dt[0].isoformat() if max_dt and max_dt[0] else None,
    })
