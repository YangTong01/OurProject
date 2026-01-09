from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import timezone
from git import Repo

def _to_naive_utc(dt):
    # GitPython datetime 可能带 tz，统一存 naive UTC
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).replace(tzinfo=None)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def extract_commits(
    repo_path: str,
    since_commit: Optional[str] = None,
    max_count: Optional[int] = None
) -> List[Dict[str, Any]]:
    repo = Repo(repo_path)
    kwargs = {}
    if max_count:
        kwargs["max_count"] = int(max_count)

    out: List[Dict[str, Any]] = []
    # iter_commits 默认从新到旧
    for c in repo.iter_commits("HEAD", **kwargs):
        if since_commit and c.hexsha == since_commit:
            break

        stats = c.stats  # 包含每个文件 insertions/deletions
        files = []
        total_add = 0
        total_del = 0

        for fp, st in stats.files.items():
            add = int(st.get("insertions", 0) or 0)
            delete = int(st.get("deletions", 0) or 0)
            files.append({"file_path": fp, "add": add, "delete": delete})
            total_add += add
            total_del += delete

        out.append({
            "hash": c.hexsha,
            "author_name": getattr(c.author, "name", None),
            "author_email": getattr(c.author, "email", None),
            "committed_at": _to_naive_utc(c.committed_datetime),
            "message": (c.message or "").strip(),
            "is_merge": (len(c.parents) > 1),
            "files_changed": len(files),
            "insertions": total_add,
            "deletions": total_del,
            "files": files,
        })
    return out
