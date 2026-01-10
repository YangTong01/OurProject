import pandas as pd
from pydriller import Repository
from datetime import timezone
from pathlib import Path
from .utils import ensure_dir


def collect_commits(repo_path: str, output_csv: str, since=None, to=None, limit=None):
    """
    Collect commit-level data from a local git repository.

    Parameters:
    - repo_path: local path to repo (e.g., ./flask)
    - output_csv: path to output raw csv
    - since/to: datetime range filter (optional)
    - limit: only take first N commits (optional, for quick test)
    """
    ensure_dir(str(Path(output_csv).parent))

    records = []
    count = 0

    repo_iter = Repository(
        repo_path,
        since=since,
        to=to
    ).traverse_commits()

    for commit in repo_iter:
        message_first_line = (commit.msg.splitlines()[0] if commit.msg else "").strip()

        dt = commit.committer_date
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

        records.append({
            "hash": commit.hash,
            "author_name": commit.author.name if commit.author else "",
            "author_email": commit.author.email if commit.author else "",
            "date": dt.isoformat(sep=" "),
            "message": message_first_line,
            "files_changed": commit.files,
            "insertions": commit.insertions,
            "deletions": commit.deletions,
            "is_merge": commit.merge,
        })

        count += 1
        if limit is not None and count >= limit:
            break

    df = pd.DataFrame(records)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return df
