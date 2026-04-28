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
    # 对外展示与申请使用的服务器编号（随机且不可预测）
    server_code = Column(String(32), unique=True, nullable=False, index=True)
    # owner_id 为空表示服务器尚未被认领（不声明 FK，users 表由 raw sqlite3 管理）
    owner_id    = Column(Integer, nullable=True)
    created_at  = Column(Integer, nullable=False, default=lambda: int(time.time()))
    # 是否在公共频道展示
    is_public   = Column(Boolean, nullable=False, default=False)
    # 入服申请是否需要人工审核：False=自动通过，True=待审批
    join_requires_approval = Column(Boolean, nullable=False, default=False)

    # 游戏连接信息
    game_ip      = Column(String(128), nullable=True, default="")
    game_port    = Column(Integer, nullable=True, default=None)
    qq_group     = Column(String(32), nullable=True, default="")
    game_version = Column(String(32), nullable=True, default="")
    # True = 在公共频道/介绍页显示 IP，False = 隐藏
    show_ip      = Column(Boolean, nullable=False, default=True)
    # 面板功能：每个面板账号在该服务器可绑定/注册的角色总数上限（0-50，默认 1）
    register_limit = Column(Integer, nullable=False, default=1)
    # 面板功能：云黑记录达到该数量时自动拒绝入服申请；0 表示关闭
    blacklist_auto_reject_count = Column(Integer, nullable=False, default=0)
    # 面板功能：玩家注册名字规则与最大长度
    character_name_regex = Column(String(256), nullable=False, default=r"^[\u4e00-\u9fffA-Za-z0-9:/\[\]]+$")
    character_name_max_length = Column(Integer, nullable=False, default=20)

    # 平台管理功能
    platform_status = Column(String(32), nullable=False, default="active")  # active/inactive/suspended
    platform_audit_status = Column(String(32), nullable=False, default="pending")  # pending/approved/rejected
    platform_audit_reason = Column(String(512), nullable=True, default=None)
    platform_audit_by = Column(Integer, nullable=True, default=None)  # 审核人 user_id
    platform_audit_at = Column(Integer, nullable=True, default=None)  # 审核时间戳
    platform_is_public = Column(Boolean, nullable=False, default=False)  # 平台是否公开展示

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
    # 入会来源追踪：public_direct_join / invite_accepted / join_request_approved / owner_claim / legacy
    join_source = Column(String(32), nullable=False, default="legacy")
    join_source_ref_type = Column(String(32), nullable=True, default=None)
    join_source_ref_id = Column(Integer, nullable=True, default=None)
    joined_by_user_id = Column(Integer, nullable=True, default=None)

    server = relationship("Server", back_populates="members")

    __table_args__ = (
        # 同一用户在同一服务器只能有一条成员记录
        UniqueConstraint("server_id", "user_id", name="uq_server_member"),
        Index("ix_server_members_user_id", "user_id"),
    )
