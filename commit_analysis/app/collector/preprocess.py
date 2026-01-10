from __future__ import annotations
import re
from typing import Any, Dict, List

MAX_MESSAGE_LEN = 2000

def _norm_email(email):
    if not email:
        return None
    e = email.strip().lower()
    return e if "@" in e else None

def _norm_name(name):
    if not name:
        return None
    return re.sub(r"\s+", " ", name.strip())[:255] or None

def preprocess_commits(raw: List[Dict[str, Any]], drop_merge: bool = False) -> List[Dict[str, Any]]:
    seen = set()
    out = []

    for c in raw:
        h = c["hash"]
        if h in seen:
            continue
        seen.add(h)

        if drop_merge and c.get("is_merge"):
            continue

        c2 = dict(c)
        c2["author_email"] = _norm_email(c.get("author_email"))
        c2["author_name"] = _norm_name(c.get("author_name"))

        msg = (c.get("message") or "").replace("\x00", "").strip()
        c2["message"] = msg[:MAX_MESSAGE_LEN]

        clean_files = []
        for f in c.get("files", []):
            fp = (f.get("file_path") or "").strip().replace("\\", "/")
            if not fp:
                continue
            clean_files.append({
                "file_path": fp,
                "add": int(f.get("add", 0) or 0),
                "delete": int(f.get("delete", 0) or 0),
            })

        c2["files"] = clean_files
        c2["files_changed"] = len(clean_files)
        c2["insertions"] = sum(x["add"] for x in clean_files)
        c2["deletions"] = sum(x["delete"] for x in clean_files)

        out.append(c2)

    return out
