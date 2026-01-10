from __future__ import annotations
from flask import Blueprint, request, jsonify
from app.models import db, Repository
from app.collector.repo_ops import prepare_repo, sanitize_repo_name
from app.collector.extract import extract_commits
from app.collector.preprocess import preprocess_commits
from app.collector.ingest import ingest_repo_commits

bp = Blueprint("repo", __name__, url_prefix="/api")

@bp.post("/repos/import")
def import_repo():
    body = request.get_json(force=True)
    repo_url = body["repo_url"]
    drop_merge = bool(body.get("drop_merge", False))
    max_count = body.get("max_count")  # 可选：限制采集数量

    local_path = prepare_repo(repo_url)
    name = sanitize_repo_name(repo_url)

    repo = Repository.query.filter_by(url=repo_url).first()
    if not repo:
        repo = Repository(url=repo_url, name=name, local_path=local_path)
        db.session.add(repo)
        db.session.commit()
    else:
        repo.local_path = local_path
        db.session.add(repo)
        db.session.commit()

    raw = extract_commits(repo.local_path, since_commit=repo.last_collected_commit, max_count=max_count)
    clean = preprocess_commits(raw, drop_merge=drop_merge)
    inserted = ingest_repo_commits(repo, clean)

    return jsonify({
        "repo_id": repo.id,
        "repo_url": repo.url,
        "local_path": repo.local_path,
        "collected_raw": len(raw),
        "inserted_commits": inserted,
        "drop_merge": drop_merge,
        "max_count": max_count,
    })
