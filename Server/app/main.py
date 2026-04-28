from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, websocket, rbac, servers, database, plugins, messages, platform
from app.core.database import engine
from app.core.schema import init_platform_db
from app.models.db_models import Base


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""

    # 自动创建 ORM 表（不影响已有表）
    Base.metadata.create_all(bind=engine)
    init_platform_db()

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
    app.include_router(messages.router)
    app.include_router(database.router)
    app.include_router(plugins.router)
    app.include_router(platform.router)

    return app

app = create_app()
