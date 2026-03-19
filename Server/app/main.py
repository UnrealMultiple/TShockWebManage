import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, websocket, rbac, servers, database, plugins
from app.core.config import AUTH_DB_PATH
from app.core.database import engine
from app.models.db_models import Base


def _run_migrations():
    """为已存在的数据库补齐新字段和新表"""
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(servers)")}
        if "is_public" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0")
        if "game_ip" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN game_ip TEXT DEFAULT ''")
        if "game_port" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN game_port INTEGER DEFAULT NULL")
        if "qq_group" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN qq_group TEXT DEFAULT ''")
        if "game_version" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN game_version TEXT DEFAULT ''")
        if "show_ip" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN show_ip INTEGER NOT NULL DEFAULT 1")
        if "local_start_enabled" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN local_start_enabled INTEGER NOT NULL DEFAULT 0")
        if "local_start_path" not in cols:
            conn.execute("ALTER TABLE servers ADD COLUMN local_start_path TEXT NOT NULL DEFAULT ''")

        # 面板权限组（每台服务器独立）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS server_panel_groups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id   INTEGER NOT NULL,
                name        TEXT    NOT NULL,
                description TEXT,
                is_builtin  INTEGER NOT NULL DEFAULT 0,
                UNIQUE(server_id, name),
                FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE
            )
        """)
        # 面板权限组的权限列表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS server_panel_group_perms (
                group_id    INTEGER NOT NULL,
                permission  TEXT    NOT NULL,
                PRIMARY KEY(group_id, permission),
                FOREIGN KEY(group_id) REFERENCES server_panel_groups(id) ON DELETE CASCADE
            )
        """)
        # 成员 → 面板权限组映射（每个成员在每台服务器只属于一个面板权限组）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS server_member_panel_groups (
                server_id   INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                group_id    INTEGER NOT NULL,
                PRIMARY KEY(server_id, user_id),
                FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE,
                FOREIGN KEY(group_id) REFERENCES server_panel_groups(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def create_app() -> FastAPI:
    # 自动创建 ORM 表（不影响已有表）
    Base.metadata.create_all(bind=engine)
    # 对旧数据库补齐新增字段
    _run_migrations()

    app = FastAPI(title="TShock Management Backend")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 包含路由
    app.include_router(auth.router)
    app.include_router(websocket.router)
    app.include_router(rbac.router)
    app.include_router(servers.router)
    app.include_router(database.router)
    app.include_router(plugins.router)

    return app

app = create_app()
