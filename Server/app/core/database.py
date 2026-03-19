from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import AUTH_DB_PATH

SQLALCHEMY_DATABASE_URL = f"sqlite:///{AUTH_DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需要此选项
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI Depends 用的数据库 Session 生成器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
