from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.models import db, Repository, Developer, Commit, FileChange

def get_or_create_developer(name: Optional[str], email: Optional[str]) -> Optional[Developer]:
    if not (name or email):
        return None

    dev = None
    if email:
        dev = Developer.query.filter_by(email=email).first()

    if dev:
        if name and not dev.name:
            dev.name = name
            db.session.add(dev)
        return dev

    dev = Developer(name=name, email=email)
    db.session.add(dev)
    db.session.flush()
    return dev

def ingest_repo_commits(repo: Repository, commits: List[Dict[str, Any]]) -> int:
    inserted = 0

    for c in commits:
        # 去重：repo_id + hash 唯一
        if Commit.query.filter_by(repo_id=repo.id, hash=c["hash"]).first():
            continue

        dev = get_or_create_developer(c.get("author_name"), c.get("author_email"))

        row = Commit(
            repo_id=repo.id,
            developer_id=(dev.id if dev else None),
            hash=c["hash"],
            committed_at=c["committed_at"],
            message=c.get("message"),
            is_merge=bool(c.get("is_merge")),
            files_changed=int(c.get("files_changed", 0) or 0),
            insertions=int(c.get("insertions", 0) or 0),
            deletions=int(c.get("deletions", 0) or 0),
        )
        db.session.add(row)
        db.session.flush()

        for f in c.get("files", []):
            db.session.add(FileChange(
                commit_id=row.id,
                file_path=f["file_path"],
                add_lines=int(f.get("add", 0) or 0),
                del_lines=int(f.get("delete", 0) or 0),
            ))

        inserted += 1

    # 更新 last_collected_commit（extract 是从新到旧，第一条是最新）
    if commits:
        repo.last_collected_commit = commits[0]["hash"]
        db.session.add(repo)

    db.session.commit()
    return inserted
