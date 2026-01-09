from __future__ import annotations
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Repository(db.Model):
    __tablename__ = "repositories"
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(512), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    local_path = db.Column(db.String(1024), nullable=False)
    last_collected_commit = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Developer(db.Model):
    __tablename__ = "developers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=True)
    name = db.Column(db.String(255), nullable=True)

class Commit(db.Model):
    __tablename__ = "commits"
    id = db.Column(db.Integer, primary_key=True)
    repo_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False, index=True)
    developer_id = db.Column(db.Integer, db.ForeignKey("developers.id"), nullable=True, index=True)

    hash = db.Column(db.String(64), nullable=False)
    committed_at = db.Column(db.DateTime, nullable=False, index=True)  # naive UTC
    message = db.Column(db.Text, nullable=True)

    is_merge = db.Column(db.Boolean, default=False, nullable=False)
    files_changed = db.Column(db.Integer, default=0, nullable=False)
    insertions = db.Column(db.Integer, default=0, nullable=False)
    deletions = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (db.UniqueConstraint("repo_id", "hash", name="uq_repo_hash"),)

class FileChange(db.Model):
    __tablename__ = "file_changes"
    id = db.Column(db.Integer, primary_key=True)
    commit_id = db.Column(db.Integer, db.ForeignKey("commits.id"), nullable=False, index=True)

    file_path = db.Column(db.String(1024), nullable=False, index=True)
    add_lines = db.Column(db.Integer, default=0, nullable=False)
    del_lines = db.Column(db.Integer, default=0, nullable=False)
