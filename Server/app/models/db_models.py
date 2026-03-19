import time
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Enum as SAEnum,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ServerMemberRole(str, enum.Enum):
    owner  = "owner"   # 认领者，享有完整管理权
    web_staff = "web_staff"  # 服主授权的平台管理
    member = "member"  # 加入者，普通成员


class Server(Base):
    """
    一个 Server 对应一个运行中的 TShock 服务端实例。
    agent_key 由 Agent 启动时生成（或在 Agent 配置中预填），
    用户凭此 key 完成"认领"成为 Owner。
    """
    __tablename__ = "servers"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(64), nullable=False)
    description = Column(String(256), default="")
    # Agent 连接时携带的唯一标识，用于认领和 WS 路由
    agent_key   = Column(String(64), unique=True, nullable=False, index=True)
    # owner_id 为空表示服务器尚未被认领（不声明 FK，users 表由 raw sqlite3 管理）
    owner_id    = Column(Integer, nullable=True)
    created_at  = Column(Integer, nullable=False, default=lambda: int(time.time()))
    # 公开可加入：其他用户可以在公共频道找到并加入服务器
    is_public   = Column(Boolean, nullable=False, default=False)

    # 游戏连接信息
    game_ip      = Column(String(128), nullable=True, default="")
    game_port    = Column(Integer, nullable=True, default=None)
    qq_group     = Column(String(32), nullable=True, default="")
    game_version = Column(String(32), nullable=True, default="")
    # True = 在公共频道/介绍页显示 IP，False = 隐藏
    show_ip      = Column(Boolean, nullable=False, default=True)

    # 同机直接启动配置（后端与 TShock 在同一台机器时使用）
    local_start_enabled = Column(Boolean, nullable=False, default=False)
    local_start_path    = Column(String(512), nullable=False, default="")

    # ORM 关系
    members = relationship(
        "ServerMember",
        back_populates="server",
        cascade="all, delete-orphan",
    )


class ServerMember(Base):
    """
    服务器成员表。
    Owner 认领时同样写入一条 role='owner' 的记录，
    便于统一查询"用户参与的所有服务器"。
    """
    __tablename__ = "server_members"

    id        = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    user_id   = Column(Integer, nullable=False)  # 指向 users.id，由 raw sqlite3 管理，不声明 FK
    role      = Column(SAEnum(ServerMemberRole), nullable=False, default=ServerMemberRole.member)
    joined_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    server = relationship("Server", back_populates="members")

    __table_args__ = (
        # 同一用户在同一服务器只能有一条成员记录
        UniqueConstraint("server_id", "user_id", name="uq_server_member"),
        Index("ix_server_members_user_id", "user_id"),
    )
