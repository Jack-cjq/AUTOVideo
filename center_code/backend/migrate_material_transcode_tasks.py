"""
数据库迁移脚本：
1) materials 表新增：status / original_path / meta_json
2) 新增 material_transcode_tasks 表（DB 作为队列）

支持 MySQL / SQLite（由 DB_TYPE 决定）。
"""

import os
import sys
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from sqlalchemy import inspect, text

from db import engine, get_db


def _dialect_name() -> str:
    try:
        return (engine.dialect.name or "").lower()
    except Exception:
        return ""


def _has_column(table: str, column: str) -> bool:
    insp = inspect(engine)
    try:
        cols = insp.get_columns(table)
    except Exception:
        return False
    return any((c.get("name") or "").lower() == column.lower() for c in cols)


def _has_table(table: str) -> bool:
    insp = inspect(engine)
    try:
        return table in insp.get_table_names()
    except Exception:
        return False


def _create_material_transcode_tasks_table() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        ddl = """
        CREATE TABLE IF NOT EXISTS material_transcode_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            input_path VARCHAR(500) NOT NULL,
            output_path VARCHAR(500) NOT NULL,
            kind VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            progress INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            locked_by VARCHAR(100),
            locked_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        idx = [
            "CREATE INDEX IF NOT EXISTS idx_material_transcode_tasks_material_id ON material_transcode_tasks(material_id);",
            "CREATE INDEX IF NOT EXISTS idx_material_transcode_tasks_status_time ON material_transcode_tasks(status, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_material_transcode_tasks_lock ON material_transcode_tasks(status, locked_at);",
        ]
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS material_transcode_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            material_id INT NOT NULL,
            input_path VARCHAR(500) NOT NULL,
            output_path VARCHAR(500) NOT NULL,
            kind VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            progress INT NOT NULL DEFAULT 0,
            error_message TEXT NULL,
            attempts INT NOT NULL DEFAULT 0,
            max_attempts INT NOT NULL DEFAULT 3,
            locked_by VARCHAR(100) NULL,
            locked_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_material_transcode_tasks_material_id (material_id),
            INDEX idx_material_transcode_tasks_status_time (status, created_at),
            INDEX idx_material_transcode_tasks_lock (status, locked_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        idx = []

    with get_db() as db:
        db.execute(text(ddl))
        for s in idx:
            db.execute(text(s))
        db.commit()


def _add_materials_columns() -> None:
    statements = []

    if not _has_column("materials", "status"):
        statements.append("ALTER TABLE materials ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'ready';")

    if not _has_column("materials", "original_path"):
        statements.append("ALTER TABLE materials ADD COLUMN original_path VARCHAR(500) NULL;")

    if not _has_column("materials", "meta_json"):
        statements.append("ALTER TABLE materials ADD COLUMN meta_json TEXT NULL;")

    # MySQL：尽量把 path 改成可空（方案C：processing 可能暂时无可播放文件）
    # SQLite：修改列约束较麻烦，保持现状即可（我们会给 path 写入占位输出路径）
    if _dialect_name() not in ("sqlite",):
        try:
            if _has_column("materials", "path"):
                statements.append("ALTER TABLE materials MODIFY COLUMN path VARCHAR(500) NULL;")
        except Exception:
            pass

    if not statements:
        return

    with get_db() as db:
        for stmt in statements:
            db.execute(text(stmt))
        db.commit()


def migrate() -> None:
    print("=" * 60)
    print("数据库迁移：materials + material_transcode_tasks")
    print("=" * 60)
    print(f"dialect={_dialect_name()}")
    print()

    if not _has_table("materials"):
        raise RuntimeError("未找到 materials 表，请先初始化数据库")

    _add_materials_columns()

    if not _has_table("material_transcode_tasks"):
        _create_material_transcode_tasks_table()

    print()
    print("=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    migrate()

