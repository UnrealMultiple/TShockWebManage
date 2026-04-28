"""
平台管理 API 路由
"""
import time
import json
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import List, Optional

from app.core.config import AUTH_DB_PATH
from app.core.database import get_db
from app.core.schema import init_platform_db
from app.models.schemas import UserOut, CloudBlacklistReviewReq
from app.models.db_models import Server, ServerMember
from app.models.platform_models import (
    User, AccountRestrictionType, AccountRestriction, Report, OperationLog,
    PlatformSettings, PlatformUser, Announcement,
    ReportStatus, OperationType
)
from app.api import deps
from app.services.agent_store_service import delete_character_on_agent
from app.services.notification_service import create_notification
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/platform", tags=["Platform"])

PLATFORM_PERMISSION_CATALOG = [
    {"key": "platform.dashboard.view", "label": "查看平台概览"},
    {"key": "platform.servers.view", "label": "查看服务器"},
    {"key": "platform.servers.audit", "label": "审核服务器"},
    {"key": "platform.servers.manage", "label": "管理服务器状态/公告"},
    {"key": "platform.servers.delete", "label": "删除服务器"},
    {"key": "platform.accounts.view", "label": "查看账号"},
    {"key": "platform.accounts.restrict", "label": "账号限制与封禁"},
    {"key": "platform.cloud_blacklist.audit", "label": "审核平台云黑"},
    {"key": "platform.reports.handle", "label": "处理举报"},
    {"key": "platform.logs.view", "label": "查看日志"},
    {"key": "platform.announcements.manage", "label": "管理平台公告"},
    {"key": "platform.settings.manage", "label": "管理平台设置"},
    {"key": "platform.rbac.manage", "label": "管理平台 RBAC"},
]

PLATFORM_SETTING_DEFAULTS = {
    "platform.server.require_audit_before_public": {
        "value": "true",
        "description": "新服务器需要平台人工审核后才可公开展示",
    },
    "platform.server.require_audit_before_online": {
        "value": "true",
        "description": "新服务器需要平台人工审核后才可上线",
    },
    "platform.max_servers_per_user": {
        "value": "3",
        "description": "单个账号最多可创建服务器数量，0 表示不限制",
    },
}


def _setting_value(db: Session, key: str) -> str:
    setting = db.query(PlatformSettings).filter(PlatformSettings.key == key).first()
    if setting and setting.value is not None:
        return str(setting.value)
    return PLATFORM_SETTING_DEFAULTS.get(key, {}).get("value", "")


def _setting_bool(db: Session, key: str) -> bool:
    return _setting_value(db, key).strip().lower() in {"1", "true", "yes", "on"}


_platform_tables_ensured = False

def _ensure_platform_permission_group_tables(db: Session):
    global _platform_tables_ensured
    if _platform_tables_ensured:
        return
    _platform_tables_ensured = True
    init_platform_db()
    now = int(time.time())
    db.execute(text("""
        DELETE FROM platform_member_roles
        WHERE group_id IN (
            SELECT id FROM platform_roles
            WHERE is_builtin = 1 AND name NOT IN ('超级管理', '管理', '成员')
        )
    """))
    db.execute(text("""
        DELETE FROM platform_roles
        WHERE is_builtin = 1 AND name NOT IN ('超级管理', '管理', '成员')
    """))
    defaults = [
        ("超级管理", "拥有全部平台权限", ["*"], 1),
        ("管理", "管理平台服务器、账号、公告、设置与权限组", [
            "platform.dashboard.view",
            "platform.servers.view",
            "platform.servers.audit",
            "platform.servers.manage",
            "platform.servers.delete",
            "platform.accounts.view",
            "platform.accounts.restrict",
            "platform.cloud_blacklist.audit",
            "platform.reports.handle",
            "platform.logs.view",
            "platform.announcements.manage",
            "platform.settings.manage",
            "platform.rbac.manage",
        ], 1),
        ("成员", "普通平台账号，无平台后台权限", [], 1),
    ]
    for name, description, permissions, is_builtin in defaults:
        exists = db.execute(
            text("SELECT id FROM platform_roles WHERE name=:name"),
            {"name": name},
        ).fetchone()
        if not exists:
            db.execute(text("""
                INSERT INTO platform_roles(name, description, permissions, is_builtin, created_at, updated_at)
                VALUES(:name, :description, :permissions, :is_builtin, :created_at, :updated_at)
            """), {
                "name": name,
                "description": description,
                "permissions": _permission_dump(permissions),
                "is_builtin": is_builtin,
                "created_at": now,
                "updated_at": now,
            })
        else:
            db.execute(text("""
                UPDATE platform_roles
                SET description=:description, permissions=:permissions, is_builtin=:is_builtin, updated_at=:updated_at
                WHERE name=:name
            """), {
                "name": name,
                "description": description,
                "permissions": _permission_dump(permissions),
                "is_builtin": is_builtin,
                "updated_at": now,
            })
    super_group = db.execute(
        text("SELECT id FROM platform_roles WHERE name='超级管理'")
    ).fetchone()
    if super_group:
        db.execute(text("""
            INSERT OR REPLACE INTO platform_member_roles(user_id, group_id, assigned_at)
            SELECT user_id, :group_id, :assigned_at
            FROM platform_members
            WHERE is_platform_admin = 1
        """), {"group_id": super_group[0], "assigned_at": now})


def _pick_related_email(value):
    if not value:
        return None
    if isinstance(value, list):
        if not value:
            return None
        return getattr(value[0], "email", None)
    return getattr(value, "email", None)


def _permission_dump(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _permission_load(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(v) for v in parsed if v]
    except Exception:
        pass
    return []


def _platform_role_permissions_for_user(conn: sqlite3.Connection, user_id: int) -> list:
    rows = conn.execute("""
        SELECT g.permissions
        FROM platform_member_roles ug
        JOIN platform_roles g ON g.id = ug.group_id
        WHERE ug.user_id = ?
    """, (user_id,)).fetchall()
    permissions = []
    for row in rows:
        if row and row[0]:
            permissions.extend(_permission_load(row[0]))
    return sorted(set(permissions))


@router.get("/me")
async def get_platform_me(
    current_user: UserOut = Depends(deps.require_platform_admin),
):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "is_platform_admin": bool(current_user.get("is_platform_admin")),
        "permissions": current_user.get("permissions") or [],
    }


@router.get("/permissions")
async def list_platform_permissions(
    current_user: UserOut = Depends(deps.require_platform_admin),
):
    return PLATFORM_PERMISSION_CATALOG


# ==================== 服务器管理 API ====================

@router.get("/servers/platform")
async def list_platform_servers(
    q: Optional[str] = Query(None, description="按名称、编号、简介搜索"),
    status: Optional[str] = Query(None, description="过滤状态: active/inactive/suspended"),
    audit_status: Optional[str] = Query(None, description="过滤审核状态: pending/approved/rejected"),
    is_public: Optional[bool] = Query(None, description="是否公开展示"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.view")),
    db: Session = Depends(get_db)
):
    """
    列表平台服务器（带审核状态和公开展示信息）
    仅平台管理员可访问
    """
    query = db.query(Server).filter(Server.platform_status != "deleted")

    if status:
        query = query.filter(Server.platform_status == status)
    if audit_status:
        query = query.filter(Server.platform_audit_status == audit_status)
    if is_public is not None:
        query = query.filter(Server.platform_is_public == is_public)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(or_(
            Server.name.ilike(pattern),
            Server.server_code.ilike(pattern),
            Server.description.ilike(pattern),
        ))

    total = query.count()
    servers = query.order_by(Server.created_at.desc(), Server.id.desc()).offset(skip).limit(limit).all()

    result = []
    for server in servers:
        result.append({
            "id": server.id,
            "name": server.name,
            "server_code": server.server_code,
            "description": server.description,
            "platform_status": server.platform_status,
            "platform_audit_status": server.platform_audit_status,
            "platform_audit_reason": server.platform_audit_reason,
            "platform_audit_by": server.platform_audit_by,
            "platform_audit_at": server.platform_audit_at,
            "platform_is_public": server.platform_is_public,
            "is_public": server.is_public,
            "owner_id": server.owner_id,
            "created_at": server.created_at,
            "join_requires_approval": server.join_requires_approval,
            "members_count": len(server.members) if server.members else 0
        })

    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/servers/{server_id}")
async def get_platform_server_detail(
    server_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.view")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    owner = db.query(User).filter(User.id == server.owner_id).first() if server.owner_id else None
    member_rows = db.query(ServerMember, User).join(
        User, ServerMember.user_id == User.id
    ).filter(
        ServerMember.server_id == server_id
    ).order_by(ServerMember.joined_at.desc(), User.id.asc()).all()
    members = []
    for member, user in member_rows:
        role = member.role.value if hasattr(member.role, "value") else str(member.role)
        is_owner = user.id == server.owner_id or role == "owner"
        members.append({
            "user_id": user.id,
            "email": user.email,
            "role": role,
            "is_owner": is_owner,
            "joined_at": member.joined_at,
        })
    return {
        "id": server.id,
        "name": server.name,
        "description": server.description,
        "server_code": server.server_code,
        "owner_id": server.owner_id,
        "owner_email": owner.email if owner else None,
        "members": members,
        "owner_accounts": [item for item in members if item["is_owner"]],
        "created_at": server.created_at,
        "game_ip": server.game_ip,
        "game_port": server.game_port,
        "qq_group": server.qq_group,
        "game_version": server.game_version,
        "show_ip": server.show_ip,
        "is_public": server.is_public,
        "join_requires_approval": server.join_requires_approval,
        "register_limit": server.register_limit,
        "platform_status": server.platform_status,
        "platform_audit_status": server.platform_audit_status,
        "platform_audit_reason": server.platform_audit_reason,
        "platform_audit_at": server.platform_audit_at,
        "platform_is_public": server.platform_is_public,
        "members_count": len(server.members) if server.members else 0,
    }


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    reason: str = Query(..., description="删除原因"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.delete")),
    db: Session = Depends(get_db)
):
    """
    删除服务器（软删除）
    仅平台管理员可访问
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    # 更新状态
    server.platform_status = "deleted"
    server.description = f"[已删除] {server.description}"
    server.name = f"[已删除] {server.name}"

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.server_delete,
        target_type="target_server",
        target_id=server_id,
        details=f"删除服务器: {server.name} (原因: {reason})",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return None


@router.delete("/servers/{server_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_server(
    server_id: int,
    reason: str = Query(..., description="硬删除原因"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.delete")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    group_ids = [
        row[0] for row in db.execute(
            text("SELECT id FROM server_roles WHERE server_id = :sid"),
            {"sid": server_id}
        ).fetchall()
    ]
    if group_ids:
        placeholders = ",".join(str(int(v)) for v in group_ids)
        db.execute(text(f"DELETE FROM server_role_permissions WHERE group_id IN ({placeholders})"))
    db.execute(text("DELETE FROM server_member_roles WHERE server_id = :sid"), {"sid": server_id})
    db.execute(text("DELETE FROM server_roles WHERE server_id = :sid"), {"sid": server_id})
    db.execute(text("DELETE FROM server_member_requests WHERE server_id = :sid"), {"sid": server_id})
    db.execute(text("DELETE FROM messages WHERE server_id = :sid"), {"sid": server_id})
    db.execute(text("DELETE FROM announcements WHERE server_id = :sid"), {"sid": server_id})
    db.delete(server)

    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.server_delete,
        target_type="target_server_hard",
        target_id=server_id,
        details=f"硬删除服务器: {server.name} (原因: {reason})",
        ip_address=None,
    )
    db.add(log)
    db.commit()
    return None


@router.post("/servers/{server_id}/audit")
async def audit_server(
    server_id: int,
    action: str = Query(..., description="审核动作: approve/reject"),
    reason: str = Query(None, description="审核原因"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.audit")),
    db: Session = Depends(get_db)
):
    """
    审核服务器
    仅平台管理员可访问
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    if action == "approve":
        if server.platform_audit_status == "approved":
            raise HTTPException(status_code=400, detail="该服务器已通过审核")
        server.platform_audit_status = "approved"
        server.platform_audit_reason = None
        server.platform_audit_by = current_user["id"]
        server.platform_audit_at = int(time.time())
        if _setting_bool(db, "platform.server.require_audit_before_online"):
            server.platform_status = "active"
        if server.is_public:
            server.platform_is_public = True
    elif action == "reject":
        if server.platform_audit_status != "pending":
            raise HTTPException(status_code=400, detail="只有待审核服务器可以驳回")
        server.platform_audit_status = "rejected"
        server.platform_audit_reason = reason or "未提供原因"
        server.platform_audit_by = current_user["id"]
        server.platform_audit_at = int(time.time())
        server.platform_status = "inactive"
        server.platform_is_public = False
    else:
        raise HTTPException(status_code=400, detail="无效的审核动作")

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.audit_approve if action == "approve" else OperationType.audit_reject,
        target_type="target_server",
        target_id=server_id,
        details=f"服务器审核: {server.name} - {'通过' if action == 'approve' else '拒绝'}",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return {"message": "审核完成", "status": server.platform_audit_status}


@router.post("/servers/{server_id}/status")
async def update_server_platform_status(
    server_id: int,
    platform_status: str = Query(..., description="active/inactive/suspended"),
    reason: str = Query("", description="状态变更原因"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.manage")),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    if platform_status not in {"active", "inactive", "suspended"}:
        raise HTTPException(status_code=400, detail="无效的平台状态")
    if (
        platform_status == "active"
        and _setting_bool(db, "platform.server.require_audit_before_online")
        and server.platform_audit_status != "approved"
    ):
        raise HTTPException(status_code=400, detail="该服务器尚未通过平台审核，不能上线")
    if platform_status == "suspended" and server.platform_status != "active":
        raise HTTPException(status_code=400, detail="只有运行中的服务器可以下架")

    server.platform_status = platform_status
    if platform_status != "active":
        server.platform_is_public = False

    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.server_update,
        target_type="target_server_status",
        target_id=server_id,
        details=f"设置平台状态为 {platform_status}，原因: {reason or '无'}",
        ip_address=None,
    )
    db.add(log)
    db.commit()
    return {"message": "平台状态已更新", "platform_status": server.platform_status}


@router.post("/servers/{server_id}/publish")
async def publish_server(
    server_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.manage")),
    db: Session = Depends(get_db)
):
    """
    公开展示服务器
    仅平台管理员可访问
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    if server.platform_status != "active":
        raise HTTPException(status_code=400, detail="服务器未上线，不能公开展示")
    if (
        _setting_bool(db, "platform.server.require_audit_before_public")
        and server.platform_audit_status != "approved"
    ):
        raise HTTPException(status_code=400, detail="该服务器尚未通过平台审核，不能公开展示")

    server.platform_is_public = True
    db.commit()
    return {"message": "服务器已公开展示"}


@router.post("/servers/{server_id}/unpublish")
async def unpublish_server(
    server_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.servers.manage")),
    db: Session = Depends(get_db)
):
    """
    取消公开展示
    仅平台管理员可访问
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    server.platform_is_public = False
    db.commit()
    return {"message": "服务器已取消公开展示"}


# ==================== 账号管理 API ====================

def _active_ban_query(db: Session, user_id: int):
    return db.query(AccountRestriction).filter(
        AccountRestriction.user_id == user_id,
        AccountRestriction.restriction_type == AccountRestrictionType.ban.value,
        AccountRestriction.is_active == True,
    )


def _platform_groups_for_user(db: Session, user_id: int) -> list:
    _ensure_platform_permission_group_tables(db)
    rows = db.execute(text("""
        SELECT g.id, g.name, g.description, g.permissions, g.is_builtin, ug.assigned_at
        FROM platform_member_roles ug
        JOIN platform_roles g ON g.id = ug.group_id
        WHERE ug.user_id = :user_id
        ORDER BY g.is_builtin DESC, g.id ASC
    """), {"user_id": user_id}).fetchall()
    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "permissions": _permission_load(row[3]),
            "is_builtin": bool(row[4]),
            "assigned_at": row[5],
        }
        for row in rows
    ]


def _sync_platform_user_from_groups(db: Session, user_id: int):
    groups = _platform_groups_for_user(db, user_id)
    has_super = any("*" in group["permissions"] for group in groups)
    pu = db.query(PlatformUser).filter(PlatformUser.user_id == user_id).first()
    now = int(time.time())
    if groups:
        if pu:
            pu.is_platform_admin = has_super
            pu.permissions = _permission_dump([])
            pu.updated_at = now
        else:
            db.add(PlatformUser(
                user_id=user_id,
                is_platform_admin=has_super,
                permissions=_permission_dump([]),
                created_at=now,
                updated_at=now,
            ))
    elif pu and not _permission_load(pu.permissions):
        db.delete(pu)
    elif pu:
        pu.is_platform_admin = False
        pu.updated_at = now


def _user_summary(db: Session, user: User) -> dict:
    server_count = db.query(ServerMember).filter(ServerMember.user_id == user.id).count()
    owned_count = db.query(Server).filter(
        Server.owner_id == user.id,
        Server.platform_status != "deleted",
    ).count()
    active_restrictions = db.query(AccountRestriction).filter(
        AccountRestriction.user_id == user.id,
        AccountRestriction.is_active == True,
    ).count()
    platform_user = db.query(PlatformUser).filter(PlatformUser.user_id == user.id).first()
    platform_groups = _platform_groups_for_user(db, user.id)
    group_names = [group["name"] for group in platform_groups]
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
        "server_count": server_count,
        "owned_server_count": owned_count,
        "active_restrictions_count": active_restrictions,
        "is_banned": _active_ban_query(db, user.id).first() is not None,
        "is_platform_admin": bool(platform_user and platform_user.is_platform_admin) or any("*" in group["permissions"] for group in platform_groups),
        "platform_group_count": len(platform_groups),
        "platform_group_names": group_names,
    }


@router.get("/accounts")
async def list_accounts(
    q: Optional[str] = Query(None, description="按邮箱或用户 ID 搜索"),
    status_filter: Optional[str] = Query(None, alias="status", description="all/banned/normal"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        keyword = q.strip()
        if keyword.isdigit():
            query = query.filter(or_(User.id == int(keyword), User.email.ilike(f"%{keyword}%")))
        else:
            query = query.filter(User.email.ilike(f"%{keyword}%"))

    if status_filter == "banned":
        banned_ids = db.query(AccountRestriction.user_id).filter(
            AccountRestriction.restriction_type == AccountRestrictionType.ban.value,
            AccountRestriction.is_active == True,
        )
        query = query.filter(User.id.in_(banned_ids))
    elif status_filter == "normal":
        banned_ids = db.query(AccountRestriction.user_id).filter(
            AccountRestriction.restriction_type == AccountRestrictionType.ban.value,
            AccountRestriction.is_active == True,
        )
        query = query.filter(~User.id.in_(banned_ids))

    total = query.count()
    users = query.order_by(User.created_at.desc(), User.id.desc()).offset(skip).limit(limit).all()
    return {
        "items": [_user_summary(db, user) for user in users],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/accounts/{user_id}")
async def get_account_detail(
    user_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")

    memberships = db.query(ServerMember, Server).join(Server, ServerMember.server_id == Server.id).filter(
        ServerMember.user_id == user_id,
        Server.platform_status != "deleted",
    ).order_by(ServerMember.joined_at.desc()).all()
    restrictions = db.query(AccountRestriction).filter(
        AccountRestriction.user_id == user_id,
        AccountRestriction.is_active == True,
    ).order_by(AccountRestriction.created_at.desc()).all()

    return {
        "user": _user_summary(db, user),
        "platform_groups": _platform_groups_for_user(db, user_id),
        "servers": [
            {
                "server_id": server.id,
                "server_name": server.name,
                "server_code": server.server_code,
                "role": member.role.value if hasattr(member.role, "value") else str(member.role),
                "joined_at": member.joined_at,
                "is_owner": server.owner_id == user_id,
                "platform_status": server.platform_status,
                "platform_audit_status": server.platform_audit_status,
                "platform_is_public": server.platform_is_public,
            }
            for member, server in memberships
        ],
        "restrictions": [
            {
                "id": item.id,
                "restriction_type": item.restriction_type,
                "value": item.value,
                "reason": item.reason,
                "created_by": item.created_by,
                "created_at": item.created_at,
                "expires_at": item.expires_at,
            }
            for item in restrictions
        ],
    }


@router.post("/accounts/{user_id}/ban")
async def ban_account(
    user_id: int,
    reason: str = Query(..., description="封禁原因"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="不能封禁当前登录账号")
    if _active_ban_query(db, user_id).first():
        raise HTTPException(status_code=400, detail="该账号已被封禁")

    restriction = AccountRestriction(
        user_id=user_id,
        restriction_type=AccountRestrictionType.ban.value,
        value=None,
        reason=reason,
        created_by=current_user["id"],
        created_at=int(time.time()),
        is_active=True,
    )
    db.add(restriction)
    db.add(OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.account_ban,
        target_type="target_account",
        target_id=user_id,
        details=f"封禁账号: {user.email}，原因: {reason}",
        ip_address=None,
    ))
    db.commit()
    return {"message": "账号已封禁"}


@router.post("/accounts/{user_id}/unban")
async def unban_account(
    user_id: int,
    reason: str = Query("", description="解封原因"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    active_bans = _active_ban_query(db, user_id).all()
    if not active_bans:
        raise HTTPException(status_code=400, detail="该账号没有生效中的封禁")

    for item in active_bans:
        item.is_active = False
    db.add(OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.account_unban,
        target_type="target_account",
        target_id=user_id,
        details=f"解除封禁: {user.email}，原因: {reason or '无'}",
        ip_address=None,
    ))
    db.commit()
    return {"message": "账号已解封"}


@router.delete("/accounts/{user_id}/servers/{server_id}/membership", status_code=status.HTTP_204_NO_CONTENT)
async def remove_account_from_server(
    user_id: int,
    server_id: int,
    reason: str = Query(..., description="移出原因"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    if server.owner_id == user_id:
        raise HTTPException(status_code=400, detail="服主不能从自己的服务器移出，请先处理服务器归属")
    member = db.query(ServerMember).filter(
        ServerMember.server_id == server_id,
        ServerMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="该账号不在此服务器中")

    character_rows = db.execute(
        text("SELECT character_name FROM agent_character_bindings_cache WHERE agent_key = :agent_key AND user_id = :uid"),
        {"agent_key": server.agent_key, "uid": user_id},
    ).fetchall()
    if server.agent_key in manager.active_agents:
        for row in character_rows:
            character_name = row[0]
            if not character_name:
                continue
            try:
                await delete_character_on_agent(server.agent_key, character_name, user_id)
            except HTTPException:
                pass

    db.delete(member)
    db.execute(
        text("DELETE FROM agent_character_bindings_cache WHERE agent_key = :agent_key AND user_id = :uid"),
        {"agent_key": server.agent_key, "uid": user_id},
    )
    db.execute(text("DELETE FROM server_member_roles WHERE server_id = :sid AND user_id = :uid"), {"sid": server_id, "uid": user_id})
    db.add(OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.server_update,
        target_type="target_account",
        target_id=user_id,
        details=f"从服务器 {server.name} 移出账号，原因: {reason}",
        ip_address=None,
    ))
    db.commit()
    return None

@router.get("/account-restrictions", response_model=List[dict])
async def list_account_restrictions(
    user_id: Optional[int] = Query(None, description="按用户 ID 过滤"),
    restriction_type: Optional[str] = Query(None, description="限制类型过滤"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db)
):
    """
    列表账号限制
    仅平台管理员可访问
    """
    query = db.query(AccountRestriction)

    if user_id:
        query = query.filter(AccountRestriction.user_id == user_id)
    if restriction_type:
        query = query.filter(AccountRestriction.restriction_type == restriction_type)
    if is_active is not None:
        query = query.filter(AccountRestriction.is_active == is_active)

    restrictions = query.order_by(AccountRestriction.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for r in restrictions:
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "restriction_type": r.restriction_type.value,
            "value": r.value,
            "reason": r.reason,
            "created_by": r.created_by,
            "created_at": r.created_at,
            "expires_at": r.expires_at,
            "is_active": r.is_active
        })

    return result


@router.post("/account-restrictions")
async def create_account_restriction(
    user_id: int = Query(..., description="用户 ID"),
    restriction_type: str = Query(..., description="限制类型: qq_limit/ban/role_limit"),
    value: str = Query(None, description="限制值"),
    reason: str = Query(None, description="限制原因"),
    expires_at: Optional[int] = Query(None, description="过期时间戳"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db)
):
    """
    添加账号限制
    仅平台管理员可访问
    """
    # 验证限制类型
    try:
        restriction_type_enum = AccountRestrictionType(restriction_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的限制类型")

    # 检查是否已存在
    existing = db.query(AccountRestriction).filter(
        AccountRestriction.user_id == user_id,
        AccountRestriction.restriction_type == restriction_type,
        AccountRestriction.is_active == True
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="该用户已有此类型限制")

    restriction = AccountRestriction(
        user_id=user_id,
        restriction_type=restriction_type_enum,
        value=value,
        reason=reason,
        created_by=current_user["id"],
        expires_at=expires_at,
        is_active=True
    )
    db.add(restriction)

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.account_ban,
        target_type="target_account",
        target_id=user_id,
        details=f"添加账号限制: {restriction_type} - {reason or '无原因'}",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return {"message": "账号限制已添加"}


@router.delete("/account-restrictions/{restriction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_account_restriction(
    restriction_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.accounts.restrict")),
    db: Session = Depends(get_db)
):
    """
    移除账号限制
    仅平台管理员可访问
    """
    restriction = db.query(AccountRestriction).filter(AccountRestriction.id == restriction_id).first()
    if not restriction:
        raise HTTPException(status_code=404, detail="限制不存在")

    restriction.is_active = False
    db.commit()
    return None


# ==================== 平台云黑审核 API ====================

@router.get("/cloud-blacklist-submissions", response_model=List[dict])
async def list_cloud_blacklist_submissions(
    status_filter: str = Query("pending", alias="status", description="状态: pending/approved/rejected/all"),
    q: str = Query("", description="搜索目标账号、来源服务器、原因、提交人"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.cloud_blacklist.audit")),
):
    if status_filter not in {"pending", "approved", "rejected", "all"}:
        raise HTTPException(status_code=400, detail="状态无效")
    clauses = []
    params: List[object] = []
    if status_filter != "all":
        clauses.append("c.status=?")
        params.append(status_filter)
    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword}%"
        clauses.append("""
            (
                c.target_email LIKE ?
                OR c.reason LIKE ?
                OR s.name LIKE ?
                OR su.email LIKE ?
                OR CAST(c.target_user_id AS TEXT) LIKE ?
                OR CAST(c.source_server_id AS TEXT) LIKE ?
            )
        """)
        params.extend([like, like, like, like, like, like])
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT
                c.id, c.target_user_id, c.target_email, c.source_server_id,
                s.name AS source_server_name,
                c.reason, c.status, c.submitted_by_user_id,
                su.email AS submitted_by_email,
                c.submitted_at, c.reviewed_by_user_id,
                ru.email AS reviewed_by_email,
                c.reviewed_at, c.review_note
            FROM cloud_blacklist_entries c
            LEFT JOIN servers s ON s.id = c.source_server_id
            LEFT JOIN users su ON su.id = c.submitted_by_user_id
            LEFT JOIN users ru ON ru.id = c.reviewed_by_user_id
            {where_sql}
            ORDER BY c.submitted_at DESC, c.id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, skip]),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/cloud-blacklist-submissions/{submission_id}/review")
async def review_cloud_blacklist_submission(
    submission_id: int,
    req: CloudBlacklistReviewReq,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.cloud_blacklist.audit")),
):
    action = (req.action or "").strip().lower()
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="action 仅支持 approve/reject")
    new_status = "approved" if action == "approve" else "rejected"
    now_ts = int(time.time())
    review_note = (req.review_note or "").strip()
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        cur = conn.execute(
            """
            UPDATE cloud_blacklist_entries
            SET status=?, reviewed_by_user_id=?, reviewed_at=?, review_note=?
            WHERE id=? AND status='pending'
            """,
            (new_status, current_user["id"], now_ts, review_note, submission_id),
        )
        conn.commit()
    if int(cur.rowcount or 0) <= 0:
        raise HTTPException(status_code=404, detail="云黑提交不存在或已审核")
    return {"message": "云黑审核已完成", "status": new_status}


@router.delete("/cloud-blacklist-submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cloud_blacklist_submission(
    submission_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.cloud_blacklist.audit")),
):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        cur = conn.execute("DELETE FROM cloud_blacklist_entries WHERE id=?", (submission_id,))
        conn.commit()
    if int(cur.rowcount or 0) <= 0:
        raise HTTPException(status_code=404, detail="云黑记录不存在")
    return None


# ==================== 举报管理 API ====================

@router.get("/reports", response_model=List[dict])
async def list_reports(
    status: Optional[str] = Query(None, description="过滤状态: pending/processing/resolved/ignored"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.reports.handle")),
    db: Session = Depends(get_db)
):
    """
    列表举报
    仅平台管理员可访问
    """
    query = db.query(Report)

    if status:
        query = query.filter(Report.status == status)

    reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for r in reports:
        result.append({
            "id": r.id,
            "reporter_id": r.reporter_id,
            "reported_user_id": r.reported_user_id,
            "reported_server_id": r.reported_server_id,
            "reason": r.reason,
            "description": r.description,
            "status": r.status.value,
            "created_at": r.created_at,
            "resolved_at": r.resolved_at,
            "resolved_by": r.resolved_by,
            "resolution": r.resolution
        })

    return result


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    resolution: str = Query(..., description="处理结果"),
    status: str = Query("resolved", description="处理状态: resolved/ignored"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.reports.handle")),
    db: Session = Depends(get_db)
):
    """
    处理举报
    仅平台管理员可访问
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")

    report.status = status
    report.resolved_at = int(time.time())
    report.resolved_by = current_user["id"]
    report.resolution = resolution

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.server_update,
        target_type="target_report",
        target_id=report_id,
        details=f"处理举报: {resolution}",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return {"message": "举报已处理"}


# ==================== 操作日志 API ====================

@router.get("/operation-logs", response_model=List[dict])
async def list_audit_logs(
    operator_id: Optional[int] = Query(None, description="按操作人过滤"),
    operation_type: Optional[str] = Query(None, description="操作类型过滤"),
    target_type: Optional[str] = Query(None, description="目标类型过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.logs.view")),
    db: Session = Depends(get_db)
):
    """
    列表操作日志
    仅平台管理员可访问
    """
    query = db.query(OperationLog)

    if operator_id:
        query = query.filter(OperationLog.operator_id == operator_id)
    if operation_type:
        query = query.filter(OperationLog.operation_type == operation_type)
    if target_type:
        query = query.filter(OperationLog.target_type == target_type)

    logs = query.order_by(OperationLog.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "operator_id": log.operator_id,
            "operator_name": _pick_related_email(log.operator),
            "operation_type": log.operation_type.value,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        })

    return result


# ==================== 统计 API ====================

@router.get("/stats")
async def get_platform_stats(
    current_user: UserOut = Depends(deps.require_platform_permission("platform.dashboard.view")),
    db: Session = Depends(get_db)
):
    """
    获取平台统计数据
    仅平台管理员可访问
    """
    # 服务器统计
    server_stats = {
        "total": db.query(Server).filter(Server.platform_status != "deleted").count(),
        "active": db.query(Server).filter(Server.platform_status == "active").count(),
        "inactive": db.query(Server).filter(Server.platform_status == "inactive").count(),
        "suspended": db.query(Server).filter(Server.platform_status == "suspended").count(),
        "pending_audit": db.query(Server).filter(Server.platform_audit_status == "pending").count(),
        "public": db.query(Server).filter(Server.platform_is_public == True).count()
    }

    # 限制统计
    restrictions = db.query(AccountRestriction).filter(AccountRestriction.is_active == True).all()
    restriction_stats = {
        "total": len(restrictions),
        "by_type": {}
    }
    for item in restrictions:
        key = str(item.restriction_type)
        restriction_stats["by_type"][key] = restriction_stats["by_type"].get(key, 0) + 1

    # 举报统计
    report_stats = {
        "total": db.query(Report).count(),
        "pending": db.query(Report).filter(Report.status == "pending").count(),
        "processing": db.query(Report).filter(Report.status == "processing").count(),
        "resolved": db.query(Report).filter(Report.status == "resolved").count(),
        "ignored": db.query(Report).filter(Report.status == "ignored").count()
    }

    # 用户统计
    user_stats = {
        "total_users": db.query(User).count(),
        "platform_admins": db.query(PlatformUser).filter(PlatformUser.is_platform_admin == True).count(),
        "owners": db.query(Server).filter(Server.owner_id != None).count()
    }

    return {
        "servers": server_stats,
        "restrictions": restriction_stats,
        "reports": report_stats,
        "users": user_stats
    }


# ==================== 公告 API ====================

def _announcement_receiver_ids(db: Session, target_type: str, server_id: Optional[int], target_account_id: Optional[int]) -> List[int]:
    """
    根据 target_type 获取公告接收人列表：
    - 'server':  仅该服务器拥有面板权限组的成员
    - 'account': 仅该账户本人
    - 'all':     平台全体用户
    """
    if target_type == "account":
        if not target_account_id:
            raise HTTPException(status_code=400, detail="target_type=account 时必须提供 target_account_id")
        exists = db.query(User).filter(User.id == target_account_id).first()
        if not exists:
            raise HTTPException(status_code=404, detail="目标账户不存在")
        return [int(target_account_id)]

    if target_type == "server":
        if not server_id:
            raise HTTPException(status_code=400, detail="target_type=server 时必须提供 server_id")
        server = db.query(Server).filter(Server.id == server_id, Server.platform_status != "deleted").first()
        if not server:
            raise HTTPException(status_code=404, detail="服务器不存在")
        # 仅该服务器拥有 panel.announcements 权限的用户
        rows = db.execute(text("""
            SELECT DISTINCT smpg.user_id
            FROM server_member_roles smpg
            JOIN server_role_permissions sgpp ON sgpp.group_id = smpg.group_id
            WHERE smpg.server_id = :sid
              AND (sgpp.permission = 'panel.announcements'
                   OR sgpp.permission = 'panel.*'
                   OR sgpp.permission = '*')
        """), {"sid": server_id}).fetchall()
        return sorted({int(r[0]) for r in rows})

    # target_type == "all"
    return [int(row[0]) for row in db.query(User.id).all()]


def _notify_announcement_receivers(
    db: Session,
    announcement_id: int,
    title: str,
    content: str,
    target_type: str,
    server_id: Optional[int],
    target_account_id: Optional[int],
    is_important: bool,
    sender_user_id: int,
) -> dict:
    receiver_ids = _announcement_receiver_ids(db, target_type, server_id, target_account_id)
    notify_server_id = server_id if target_type == "server" else None
    for receiver_id in receiver_ids:
        create_notification(
            receiver_user_id=receiver_id,
            msg_type="announcement",
            title=title,
            content=content,
            sender_user_id=sender_user_id,
            server_id=notify_server_id,
            ref_type="announcement",
            ref_id=announcement_id,
            payload={"is_important": bool(is_important), "target_type": target_type},
        )
    return {"receiver_count": len(receiver_ids)}


@router.get("/announcements", response_model=List[dict])
async def list_announcements(
    target_type: Optional[str] = Query(None, description="目标类型: server/account/all"),
    server_id: Optional[int] = Query(None, description="按服务器过滤"),
    is_important: Optional[bool] = Query(None, description="是否重要"),
    status: Optional[str] = Query("active", description="状态: active/archived"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.announcements.manage")),
    db: Session = Depends(get_db)
):
    """
    列表公告
    仅平台管理员可访问
    """
    query = db.query(Announcement).filter(Announcement.status == status)

    if target_type:
        query = query.filter(Announcement.target_type == target_type)
    if server_id:
        query = query.filter(Announcement.server_id == server_id)
    if is_important is not None:
        query = query.filter(Announcement.is_important == is_important)

    announcements = query.order_by(Announcement.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for a in announcements:
        result.append({
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "target_type": a.target_type,
            "server_id": a.server_id,
            "target_account_id": a.target_account_id,
            "is_important": a.is_important,
            "status": a.status,
            "created_by": a.created_by,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "expires_at": a.expires_at
        })

    return result


@router.post("/announcements")
async def create_announcement(
    title: str = Query(..., description="公告标题"),
    content: str = Query(..., description="公告内容"),
    target_type: str = Query(..., description="目标类型: server / account / all"),
    server_id: Optional[int] = Query(None, description="target_type=server 时必填"),
    target_account_id: Optional[int] = Query(None, description="target_type=account 时必填"),
    is_important: bool = Query(False, description="是否重要"),
    expires_at: Optional[int] = Query(None, description="过期时间戳（null 表示永久）"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.announcements.manage")),
    db: Session = Depends(get_db)
):
    """
    创建公告
    仅平台管理员可访问
    - target_type=server:  指定服务器，仅该服务器拥有面板权限的用户可见
    - target_type=account: 指定个体账户，仅该账户本人可见
    - target_type=all:     平台全体用户可见
    """
    if target_type not in ("server", "account", "all"):
        raise HTTPException(status_code=400, detail="target_type 必须为 server/account/all")
    if target_type == "server" and not server_id:
        raise HTTPException(status_code=400, detail="target_type=server 时必须提供 server_id")
    if target_type == "account" and not target_account_id:
        raise HTTPException(status_code=400, detail="target_type=account 时必须提供 target_account_id")

    receiver_ids = _announcement_receiver_ids(db, target_type, server_id, target_account_id)

    announcement = Announcement(
        title=title,
        content=content,
        target_type=target_type,
        server_id=server_id if target_type == "server" else None,
        target_account_id=target_account_id if target_type == "account" else None,
        is_important=is_important,
        status="active",
        created_by=current_user["id"],
        expires_at=expires_at
    )
    db.add(announcement)
    db.flush()

    # 记录操作日志
    target_label = {"server": f"服务器#{server_id}", "account": f"账户#{target_account_id}", "all": "全局"}[target_type]
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.announcement_create,
        target_type="target_announcement",
        target_id=announcement.id,
        details=f"创建公告[{target_label}]: {title}",
        ip_address=None
    )
    db.add(log)

    announcement_id = announcement.id
    db.commit()
    notification = _notify_announcement_receivers(
        db,
        announcement_id,
        title,
        content,
        target_type,
        server_id,
        target_account_id,
        is_important,
        current_user["id"],
    )
    notification["receiver_count"] = len(receiver_ids)
    return {"message": "公告已创建", "notification": notification}


@router.put("/announcements/{announcement_id}")
async def update_announcement(
    announcement_id: int,
    title: str = Query(..., description="公告标题"),
    content: str = Query(..., description="公告内容"),
    target_type: Optional[str] = Query(None, description="目标类型: server/account/all"),
    server_id: Optional[int] = Query(None, description="target_type=server 时必填"),
    target_account_id: Optional[int] = Query(None, description="target_type=account 时必填"),
    is_important: bool = Query(False, description="是否重要"),
    expires_at: Optional[int] = Query(None, description="过期时间戳"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.announcements.manage")),
    db: Session = Depends(get_db)
):
    """
    更新公告
    仅平台管理员可访问
    """
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    announcement.title = title
    announcement.content = content
    announcement.is_important = is_important
    announcement.expires_at = expires_at
    announcement.updated_at = int(time.time())

    if target_type:
        if target_type not in ("server", "account", "all"):
            raise HTTPException(status_code=400, detail="target_type 必须为 server/account/all")
        announcement.target_type = target_type
        announcement.server_id = server_id if target_type == "server" else None
        announcement.target_account_id = target_account_id if target_type == "account" else None

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.announcement_update,
        target_type="target_announcement",
        target_id=announcement_id,
        details=f"更新公告: {title}",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return {"message": "公告已更新"}


@router.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.announcements.manage")),
    db: Session = Depends(get_db)
):
    """
    删除公告
    仅平台管理员可访问
    """
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    deleted_title = announcement.title
    notification_result = db.execute(
        text("DELETE FROM messages WHERE ref_type = 'announcement' AND ref_id = :aid"),
        {"aid": announcement_id},
    )
    revoked_count = int(notification_result.rowcount or 0)
    db.delete(announcement)

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.announcement_delete,
        target_type="target_announcement",
        target_id=announcement_id,
        details=f"删除公告: {deleted_title}，撤回通知 {revoked_count} 条",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return None


# ==================== 平台设置 API ====================

@router.get("/platform-settings")
async def get_platform_settings(
    key: Optional[str] = Query(None, description="按 key 过滤"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.settings.manage")),
    db: Session = Depends(get_db)
):
    """
    获取平台设置
    仅平台管理员可访问
    """
    result = {
        setting_key: meta["value"]
        for setting_key, meta in PLATFORM_SETTING_DEFAULTS.items()
    }

    query = db.query(PlatformSettings)
    if key:
        query = query.filter(PlatformSettings.key == key)
        result = {key: result.get(key, "")}

    for s in query.all():
        result[s.key] = s.value

    return result


@router.put("/platform-settings/{key}")
async def update_platform_setting(
    key: str,
    value: str = Query(..., description="设置值"),
    description: str = Query(None, description="描述"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.settings.manage")),
    db: Session = Depends(get_db)
):
    """
    更新平台设置
    仅平台管理员可访问
    """
    setting = db.query(PlatformSettings).filter(PlatformSettings.key == key).first()

    if setting:
        setting.value = value
        setting.description = description
        setting.updated_at = int(time.time())
    else:
        setting = PlatformSettings(
            key=key,
            value=value,
            description=description,
            updated_at=int(time.time())
        )
        db.add(setting)

    db.commit()
    return {"message": "设置已更新"}


# ==================== 平台用户管理 API ====================

def _group_row_to_dict(row, member_count: int = 0) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2] or "",
        "permissions": _permission_load(row[3]),
        "is_builtin": bool(row[4]),
        "created_at": row[5],
        "updated_at": row[6],
        "member_count": member_count,
    }


@router.get("/platform-permission-groups")
async def list_platform_roles(
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db),
):
    _ensure_platform_permission_group_tables(db)
    rows = db.execute(text("""
        SELECT g.id, g.name, g.description, g.permissions, g.is_builtin, g.created_at, g.updated_at,
               COUNT(ug.user_id) AS member_count
        FROM platform_roles g
        LEFT JOIN platform_member_roles ug ON ug.group_id = g.id
        GROUP BY g.id
        ORDER BY g.is_builtin DESC, g.id ASC
    """)).fetchall()
    db.commit()
    return [
        _group_row_to_dict(row, row[7] or 0)
        for row in rows
    ]


@router.post("/platform-permission-groups")
async def create_platform_permission_group(
    name: str = Query(...),
    description: str = Query(""),
    permissions: str = Query("[]", description="JSON 数组字符串"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db),
):
    _ensure_platform_permission_group_tables(db)
    try:
        parsed = json.loads(permissions) if permissions else []
    except Exception:
        raise HTTPException(status_code=400, detail="permissions 必须是 JSON 数组")
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="permissions 必须是 JSON 数组")
    now = int(time.time())
    db.execute(text("""
        INSERT INTO platform_roles(name, description, permissions, is_builtin, created_at, updated_at)
        VALUES(:name, :description, :permissions, 0, :created_at, :updated_at)
    """), {
        "name": name.strip(),
        "description": description.strip(),
        "permissions": _permission_dump(parsed),
        "created_at": now,
        "updated_at": now,
    })
    db.commit()
    return {"message": "平台权限组已创建"}


@router.put("/platform-permission-groups/{group_id}")
async def update_platform_permission_group(
    group_id: int,
    name: str = Query(...),
    description: str = Query(""),
    permissions: str = Query("[]", description="JSON 数组字符串"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db),
):
    _ensure_platform_permission_group_tables(db)
    row = db.execute(text("SELECT id FROM platform_roles WHERE id=:id"), {"id": group_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="平台权限组不存在")
    try:
        parsed = json.loads(permissions) if permissions else []
    except Exception:
        raise HTTPException(status_code=400, detail="permissions 必须是 JSON 数组")
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="permissions 必须是 JSON 数组")
    db.execute(text("""
        UPDATE platform_roles
        SET name=:name, description=:description, permissions=:permissions, updated_at=:updated_at
        WHERE id=:id
    """), {
        "id": group_id,
        "name": name.strip(),
        "description": description.strip(),
        "permissions": _permission_dump(parsed),
        "updated_at": int(time.time()),
    })
    db.commit()
    return {"message": "平台权限组已更新"}


@router.delete("/platform-permission-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_permission_group(
    group_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db),
):
    _ensure_platform_permission_group_tables(db)
    row = db.execute(
        text("SELECT is_builtin FROM platform_roles WHERE id=:id"),
        {"id": group_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="平台权限组不存在")
    if row[0]:
        raise HTTPException(status_code=400, detail="内置平台权限组不可删除")
    db.execute(text("DELETE FROM platform_member_roles WHERE group_id=:id"), {"id": group_id})
    db.execute(text("DELETE FROM platform_roles WHERE id=:id"), {"id": group_id})
    db.commit()
    return None


@router.get("/platform-permission-groups/{group_id}/members")
async def list_platform_permission_group_members(
    group_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db),
):
    _ensure_platform_permission_group_tables(db)
    rows = db.execute(text("""
        SELECT u.id, u.email, u.created_at, ug.assigned_at
        FROM platform_member_roles ug
        JOIN users u ON u.id = ug.user_id
        WHERE ug.group_id = :group_id
        ORDER BY ug.assigned_at DESC
    """), {"group_id": group_id}).fetchall()
    return [
        {"user_id": row[0], "email": row[1], "created_at": row[2], "assigned_at": row[3]}
        for row in rows
    ]


@router.post("/platform-permission-groups/{group_id}/members/{user_id}")
async def assign_platform_permission_group_member(
    group_id: int,
    user_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db),
):
    _ensure_platform_permission_group_tables(db)
    group = db.execute(text("SELECT permissions FROM platform_roles WHERE id=:id"), {"id": group_id}).fetchone()
    if not group:
        raise HTTPException(status_code=404, detail="平台权限组不存在")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    now = int(time.time())
    db.execute(text("""
        INSERT OR REPLACE INTO platform_member_roles(user_id, group_id, assigned_at)
        VALUES(:user_id, :group_id, :assigned_at)
    """), {"user_id": user_id, "group_id": group_id, "assigned_at": now})
    _sync_platform_user_from_groups(db, user_id)
    db.commit()
    return {"message": "成员已加入平台权限组"}


@router.delete("/platform-permission-groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_platform_permission_group_member(
    group_id: int,
    user_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db),
):
    _ensure_platform_permission_group_tables(db)
    db.execute(
        text("DELETE FROM platform_member_roles WHERE user_id=:user_id AND group_id=:group_id"),
        {"user_id": user_id, "group_id": group_id},
    )
    _sync_platform_user_from_groups(db, user_id)
    db.commit()
    return None

@router.get("/platform-users", response_model=List[dict])
async def list_platform_members(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db)
):
    """
    列表平台用户
    仅平台管理员可访问
    """
    query = db.query(PlatformUser).join(User, PlatformUser.user_id == User.id)

    platform_members = query.offset(skip).limit(limit).all()

    result = []
    for pu in platform_members:
        result.append({
            "id": pu.id,
            "user_id": pu.user_id,
            "username": _pick_related_email(pu.user),
            "email": _pick_related_email(pu.user),
            "is_platform_admin": pu.is_platform_admin,
            "permissions": _permission_load(pu.permissions),
            "created_at": pu.created_at,
            "updated_at": pu.updated_at
        })

    return result


@router.post("/platform-users/{user_id}/admin")
async def grant_platform_admin(
    user_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db)
):
    """
    授予平台管理员权限
    仅平台管理员可访问
    """
    # 检查是否已经是管理员
    existing = db.query(PlatformUser).filter(PlatformUser.user_id == user_id).first()

    if existing:
        existing.is_platform_admin = True
    else:
        pu = PlatformUser(
            user_id=user_id,
            is_platform_admin=True,
            permissions=_permission_dump([])
        )
        db.add(pu)

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.permission_grant,
        target_type="target_user",
        target_id=user_id,
        details=f"授予平台管理员权限",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return {"message": "已授予平台管理员权限"}


@router.delete("/platform-users/{user_id}/admin", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_platform_admin(
    user_id: int,
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db)
):
    """
    撤销平台管理员权限
    仅平台管理员可访问
    """
    pu = db.query(PlatformUser).filter(PlatformUser.user_id == user_id).first()
    if not pu:
        raise HTTPException(status_code=404, detail="用户不是平台管理员")

    pu.is_platform_admin = False

    # 记录操作日志
    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.permission_revoke,
        target_type="target_user",
        target_id=user_id,
        details=f"撤销平台管理员权限",
        ip_address=None
    )
    db.add(log)

    db.commit()
    return None


@router.put("/platform-users/{user_id}/permissions")
async def update_platform_user_permissions(
    user_id: int,
    permissions: str = Query("", description="JSON 数组字符串"),
    current_user: UserOut = Depends(deps.require_platform_permission("platform.rbac.manage")),
    db: Session = Depends(get_db)
):
    try:
        parsed = json.loads(permissions) if permissions else []
    except Exception:
        raise HTTPException(status_code=400, detail="permissions 必须是 JSON 数组")
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="permissions 必须是 JSON 数组")
    parsed = [str(v) for v in parsed if v]

    pu = db.query(PlatformUser).filter(PlatformUser.user_id == user_id).first()
    if not pu:
        pu = PlatformUser(
            user_id=user_id,
            is_platform_admin=False,
            permissions=_permission_dump(parsed),
        )
        db.add(pu)
    else:
        pu.permissions = _permission_dump(parsed)
        pu.updated_at = int(time.time())

    log = OperationLog(
        operator_id=current_user["id"],
        operation_type=OperationType.server_update,
        target_type="target_platform_permissions",
        target_id=user_id,
        details=f"更新平台权限: {', '.join(parsed) if parsed else '(空)'}",
        ip_address=None,
    )
    db.add(log)
    db.commit()
    return {"message": "平台权限已更新", "permissions": parsed}
