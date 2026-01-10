from __future__ import annotations
import os
from flask import Flask
from app.models import db
from app.routes.repo import bp as repo_bp
from app.routes.stats import bp as stats_bp
from app.routes.debug import bp as debug_bp
from app.routes.contributors import bp as contributors_bp
def create_app():
    app = Flask(__name__)

    # 1) 计算项目根目录（OPEN）
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 2) 确保 instance 目录存在
    instance_dir = os.path.join(base_dir, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    # 3) 用绝对路径指定 sqlite 文件
    db_path = os.path.join(instance_dir, "app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path.replace("\\", "/")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    app.register_blueprint(repo_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(debug_bp)
    app.register_blueprint(contributors_bp)

    with app.app_context():
        db.create_all()

    @app.get("/")
    def health():
        return {"ok": True}

    return app
