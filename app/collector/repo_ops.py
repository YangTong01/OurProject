from __future__ import annotations
import os
os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = r"D:\APP\Git\Git\mingw64\bin\git.exe"
import re
from git import Repo

def sanitize_repo_name(url: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", url.strip())
    s = s.strip("_")
    return (s[-120:] or "repo")

def prepare_repo(repo_url_or_path: str, base_dir: str = "data/repos") -> str:
    os.makedirs(base_dir, exist_ok=True)

    # local repo
    if os.path.isdir(repo_url_or_path) and os.path.isdir(os.path.join(repo_url_or_path, ".git")):
        repo = Repo(repo_url_or_path)
        try:
            if repo.remotes:
                repo.remotes.origin.fetch()
        except Exception:
            pass
        return repo_url_or_path

    # remote url
    local_path = os.path.join(base_dir, sanitize_repo_name(repo_url_or_path))
    if os.path.isdir(os.path.join(local_path, ".git")):
        repo = Repo(local_path)
        repo.remotes.origin.fetch()
    else:
        Repo.clone_from(repo_url_or_path, local_path)

    return local_path
