import time
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Text, DateTime,
    Enum as SAEnum, Index,
)
from sqlalchemy.orm import relationship, foreign
from app.core.database import Base


class User(Base):
    """
    用户表（仅用于 ORM 关联，不创建表）
    映射 auth_db 中的 Users 表
    """
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(128), unique=True, nullable=False)
    pw_hash = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    access_group_id = Column(Integer, nullable=True)
    created_at = Column(Integer, nullable=False)


# Python 原生枚举（用于存储和比较）
class PlatformStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class AuditStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class AccountRestrictionType(str, enum.Enum):
    qq_limit = "qq_limit"
    ban = "ban"
    role_limit = "role_limit"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    resolved = "resolved"
    ignored = "ignored"


class OperationType(str, enum.Enum):
    server_create = "server_create"
    server_delete = "server_delete"
    server_update = "server_update"
    account_ban = "account_ban"
    account_unban = "account_unban"
    announcement_create = "announcement_create"
    announcement_update = "announcement_update"
    announcement_delete = "announcement_delete"
    audit_approve = "audit_approve"
    audit_reject = "audit_reject"
    permission_grant = "permission_grant"
    permission_revoke = "permission_revoke"


class AccountRestriction(Base):
    """
    账号限制表
    记录对特定用户的限制（QQ号限制、封禁等）
    """
    __tablename__ = "AccountRestrictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # 被限制的用户 ID
    restriction_type = Column(String(32), nullable=False)  # 使用字符串存储枚举
    value = Column(String(64), nullable=True)  # 限制的具体值（如 QQ 号）
    reason = Column(Text, nullable=True)  # 限制原因
    created_by = Column(Integer, nullable=False)  # 创建者 user_id
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    expires_at = Column(Integer, nullable=True)  # 过期时间（null 表示永久）
    is_active = Column(Boolean, nullable=False, default=True)

    # 关系（使用 foreign() 明确外键列）
    creator = relationship("User", primaryjoin="AccountRestriction.created_by == foreign(User.id)", viewonly=True)


class Report(Base):
    """
    举报表
    记录用户举报的信息
    """
    __tablename__ = "UserReports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, nullable=False)  # 举报人 user_id
    reported_user_id = Column(Integer, nullable=False)  # 被举报用户 user_id
    reported_server_id = Column(Integer, nullable=False)  # 涉及的服务器 ID
    reason = Column(Text, nullable=False)  # 举报原因
    description = Column(Text, nullable=True)  # 详细描述
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    resolved_at = Column(Integer, nullable=True)
    resolved_by = Column(Integer, nullable=True)  # 处理人 user_id
    resolution = Column(Text, nullable=True)  # 处理结果

    # 关系（使用 foreign() 明确外键列）
    reporter = relationship("User", primaryjoin="Report.reporter_id == foreign(User.id)", viewonly=True)
    reported_user = relationship("User", primaryjoin="Report.reported_user_id == foreign(User.id)", viewonly=True)
    resolver = relationship("User", primaryjoin="Report.resolved_by == foreign(User.id)", viewonly=True)


class OperationLog(Base):
    """
    操作日志表
    记录平台管理员的操作历史
    """
    __tablename__ = "AuditLogs"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, nullable=False)  # 操作人 user_id
    operation_type = Column(String(64), nullable=False)
    target_type = Column(String(32), nullable=False)  # target_server / target_account / target_announcement
    target_id = Column(Integer, nullable=False)  # 目标 ID
    details = Column(Text, nullable=True)  # 操作详情
    ip_address = Column(String(64), nullable=True)  # 操作 IP
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    # 关系（使用 foreign() 明确外键列）
    operator = relationship("User", primaryjoin="OperationLog.operator_id == foreign(User.id)", viewonly=True)


class PlatformSettings(Base):
    """
    平台设置表
    存储全局平台配置
    """
    __tablename__ = "PlatformSettings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(String(256), nullable=True)
    updated_at = Column(Integer, nullable=False, default=lambda: int(time.time()))

    # 单例表，只有一个记录
    __table_args__ = (
        Index("ix_platform_settings_key", "key"),
    )


class Announcement(Base):
    """
    公告表
    平台发布的通知公告
    target_type: 'server' 指定服务器 / 'account' 指定个体账户 / 'all' 所有账户
    """
    __tablename__ = "Announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    target_type = Column(String(32), nullable=False, default="all")  # server / account / all
    server_id = Column(Integer, nullable=True)  # target_type='server' 时使用
    target_account_id = Column(Integer, nullable=True)  # target_type='account' 时使用
    is_important = Column(Boolean, nullable=False, default=False)  # 是否重要
    status = Column(String(32), nullable=False, default="active")  # active/archived
    created_by = Column(Integer, nullable=False)  # 创建人 user_id
    created_at = Column(Integer, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(Integer, nullable=True)
    expires_at = Column(Integer, nullable=True)  # 过期时间（null 表示永久）

    # 关系（使用 foreign() 明确外键列）
    creator = relationship("User", primaryjoin="Announcement.created_by == foreign(User.id)", viewonly=True)
