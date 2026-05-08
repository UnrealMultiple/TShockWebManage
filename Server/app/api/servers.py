import asyncio
import json
import re
import secrets
import sqlite3
import time
import unicodedata
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import AUTH_DB_PATH
from app.core.database import get_db
from app.core.qq_email import normalize_qq_email
from app.core.utils import verify_token, new_id, now_ms
from app.models.db_models import Server, ServerMember, ServerMemberRole
from app.models.schemas import (
    ServerClaimReq, ServerJoinReq, ServerUpdateReq,
    ServerOut, ServerDetailOut, ServerMemberOut,
    UpdateMemberRoleReq, BindVerifyReq,
    AssignCharacterOwnerReq,
    PanelGroupCreate, PanelGroupUpdate, PanelGroupOut, PanelMemberGroupUpdate,
    PanelFeatureSettingsOut, PanelFeatureSettingsUpdate,
    PanelMembershipInviteReq, PanelMembershipReviewReq,
    ServerApplyReq, JoinRequestReviewReq, JoinRequestOut,
    ServerInviteCreateReq, ServerInviteOut, BlacklistCreateReq,
)
from app.services.membership_service import add_member
from app.services.notification_service import create_notification
from app.services.agent_store_service import (
    add_blacklist_on_agent,
    assign_character_on_agent,
    bind_character_on_agent,
    delete_character_on_agent,
    remove_blacklist_on_agent,
)
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/servers", tags=["Servers"])

DEFAULT_CHARACTER_NAME_REGEX = r"^[\u4e00-\u9fffA-Za-z0-9:/\[\]]+$"
DEFAULT_CHARACTER_NAME_MAX_LENGTH = 20
BLOCKED_CHARACTER_NAME_CATEGORIES = {"Cc", "Cf", "Zs", "Zl", "Zp"}


def _normalize_server_code(v: str) -> str:
    return ''.join(ch for ch in str(v or '').upper() if ch.isalnum())


def _generate_server_code(db: Session) -> str:
    # 12 位十六进制：不可预测，便于输入
    while True:
        code = secrets.token_hex(6).upper()
        exists = db.query(Server).filter_by(server_code=code).first()
        if not exists:
            return code


# ── 面板权限组默认配置 ──────────────────────────────────────────────────────

_DEFAULT_PANEL_GROUPS = [
    {
        "name": "服主",
        "description": "服主，拥有该服务器全部面板权限",
        "is_builtin": 1,
        "permissions": ["*"],
    },
    {
        "name": "管理",
        "description": "管理员，拥有所有TShock管理权限",
        "is_builtin": 1,
        "permissions": [
            "tshock.*",
            "panel.console", "panel.users",
            "panel.files", "panel.files.write", "panel.files.delete",
            "panel.database", "panel.database.write", "panel.database.sql",
            "panel.dashboard", "panel.characters",
            "panel.membership.review", "panel.invites.manage",
            "panel.inventory.view.self", "panel.inventory.view.others",
            "panel.announcements", "panel.blacklist",
            "panel.tshock.*",
            "panel.tshock.config", "panel.plugins", "panel.minimap",
            "panel.bans", "panel.banlists", "panel.groups",
        ],
    },
    {
        "name": "成员",
        "description": "普通成员，仪表盘及我的角色",
        "is_builtin": 1,
        "permissions": [
            "panel.dashboard", "panel.characters",
            "panel.inventory.view.self", "panel.inventory.view.others",
            "panel.announcements",
        ],
    },
]

# 旧英文组名 → 新中文组名的迁移映射
_LEGACY_GROUP_RENAME = {"owner": "服主", "admin": "管理", "default": "成员"}


def _init_server_access_groups(server_id: int, db: Optional[Session] = None, conn: Optional[sqlite3.Connection] = None):
    """为服务器初始化/修复默认面板权限组（幂等）"""
    if db is not None:
        def execute(sql: str, params: dict):
            return db.execute(text(sql), params)
    else:
        owns_conn = conn is None
        if conn is None:
            conn = sqlite3.connect(AUTH_DB_PATH)

        def execute(sql: str, params: dict):
            return conn.execute(sql, params)

    try:
        # ① 将旧英文组名重命名为中文（保留成员分配关系）
        for old_name, new_name in _LEGACY_GROUP_RENAME.items():
            old_row = execute(
                "SELECT id FROM ServerAccessGroups WHERE server_id=:server_id AND name=:name",
                {"server_id": server_id, "name": old_name},
            ).fetchone()
            new_row = execute(
                "SELECT id FROM ServerAccessGroups WHERE server_id=:server_id AND name=:name",
                {"server_id": server_id, "name": new_name},
            ).fetchone()
            if old_row and not new_row:
                # 直接重命名旧组
                execute(
                    "UPDATE ServerAccessGroups SET name=:name WHERE id=:id",
                    {"name": new_name, "id": old_row[0]},
                )
            elif old_row and new_row:
                execute(
                    "UPDATE ServerMembers SET access_group_id=:new_id WHERE access_group_id=:old_id",
                    {"new_id": new_row[0], "old_id": old_row[0]},
                )
                execute("DELETE FROM ServerAccessGroups WHERE id=:id", {"id": old_row[0]})
        # ② 补充缺少的默认中文组
        for g in _DEFAULT_PANEL_GROUPS:
            permissions = json.dumps(g["permissions"], ensure_ascii=False)
            execute(
                """
                INSERT OR IGNORE INTO ServerAccessGroups(server_id, name, description, is_builtin, permissions)
                VALUES(:server_id, :name, :description, :is_builtin, :permissions)
                """,
                {
                    "server_id": server_id,
                    "name": g["name"],
                    "description": g["description"],
                    "is_builtin": g["is_builtin"],
                    "permissions": permissions,
                },
            )
            row = execute(
                "SELECT id FROM ServerAccessGroups WHERE server_id=:server_id AND name=:name",
                {"server_id": server_id, "name": g["name"]},
            ).fetchone()
            gid = row[0]
            execute(
                """
                UPDATE ServerAccessGroups
                SET description=:description, is_builtin=:is_builtin, permissions=:permissions
                WHERE id=:id
                """,
                {
                    "description": g["description"],
                    "is_builtin": g["is_builtin"],
                    "permissions": permissions,
                    "id": gid,
                },
            )
        if db is None and owns_conn:
            conn.commit()
    finally:
        if db is None and owns_conn:
            conn.close()


# ── 公共依赖 ─────────────────────────────────────────────────────

def _get_user_id(authorization: str = Header(...)) -> int:
    """从 Bearer Token 解析当前登录用户的 user_id"""
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    email = verify_token(token)
    if not email:
        raise HTTPException(401, "未登录或登录已过期")
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE email=? COLLATE NOCASE", (email,)
        ).fetchone()
        if row:
            banned = conn.execute(
                "SELECT 1 FROM AccountRestrictions WHERE user_id=? AND restriction_type='ban' AND is_active=1 LIMIT 1",
                (int(row[0]),),
            ).fetchone()
    if not row:
        raise HTTPException(401, "用户不存在")
    if banned:
        raise HTTPException(403, "账号已被平台封禁")
    return row[0]


def _get_user_email(user_id: int) -> str:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
    return row[0] if row else ""


def _get_user_id_by_email(email: str) -> Optional[int]:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE email=? COLLATE NOCASE",
            ((email or "").strip(),),
        ).fetchone()
    return int(row[0]) if row else None


def _get_platform_setting(key: str, default: str = "") -> str:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM PlatformSettings WHERE key=?",
            (key,),
        ).fetchone()
    return str(row[0]) if row and row[0] is not None else default


def _get_platform_bool_setting(key: str, default: bool = False) -> bool:
    raw = _get_platform_setting(key, "true" if default else "false")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _has_panel_perm(server_id: int, user_id: int, permission: str) -> bool:
    """检查用户在指定服务器是否拥有给定面板权限（支持 * 及前缀通配 tshock.*）"""
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        pg_row = conn.execute(
            "SELECT g.id FROM ServerMembers sm "
            "JOIN ServerAccessGroups g ON g.id = sm.access_group_id "
            "WHERE sm.server_id=? AND sm.user_id=?",
            (server_id, user_id),
        ).fetchone()
        if not pg_row:
            return False
        for p in _collect_panel_group_permissions(conn, server_id, pg_row[0]):
            if p == '*' or p == permission:
                return True
            if p.endswith('.*'):
                prefix = p[:-2]
                if permission == prefix or permission.startswith(prefix + '.'):
                    return True
        return False


def _collect_panel_group_permissions(conn: sqlite3.Connection, server_id: int, group_id: int) -> List[str]:
    """递归收集权限组权限（包含继承父组），并避免循环依赖。"""
    seen = set()
    perms = set()
    current_id = group_id

    while current_id and current_id not in seen:
        seen.add(current_id)
        parent_row = conn.execute(
            "SELECT permissions, parent_group_id FROM ServerAccessGroups WHERE id=? AND server_id=?",
            (current_id, server_id),
        ).fetchone()
        if not parent_row:
            break
        try:
            parsed = json.loads(parent_row[0] or "[]")
            if isinstance(parsed, list):
                for perm in parsed:
                    if perm:
                        perms.add(str(perm))
        except Exception:
            pass
        current_id = parent_row[1]

    return sorted(perms)


def _has_parent_cycle(conn: sqlite3.Connection, server_id: int, group_id: int, parent_group_id: Optional[int]) -> bool:
    """检查设置 parent_group_id 后是否形成循环。"""
    seen = {group_id}
    current_id = parent_group_id
    while current_id is not None:
        if current_id in seen:
            return True
        seen.add(current_id)
        row = conn.execute(
            "SELECT parent_group_id FROM ServerAccessGroups WHERE id=? AND server_id=?",
            (current_id, server_id),
        ).fetchone()
        if not row:
            break
        current_id = row[0]
    return False


def _server_access_group_id(server_id: int, name: str, db: Optional[Session] = None, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
    _init_server_access_groups(server_id, db=db, conn=conn)
    if db is not None:
        row = db.execute(
            text("SELECT id FROM ServerAccessGroups WHERE server_id=:server_id AND name=:name"),
            {"server_id": server_id, "name": name},
        ).fetchone()
    elif conn is not None:
        row = conn.execute(
            "SELECT id FROM ServerAccessGroups WHERE server_id=:server_id AND name=:name",
            {"server_id": server_id, "name": name},
        ).fetchone()
    else:
        with sqlite3.connect(AUTH_DB_PATH) as new_conn:
            row = new_conn.execute(
                "SELECT id FROM ServerAccessGroups WHERE server_id=:server_id AND name=:name",
                {"server_id": server_id, "name": name},
            ).fetchone()
    return int(row[0]) if row else None


def _caller_can_manage(server_id: int, user_id: int, db: Session, perm: str = "panel.users") -> bool:
    """检查 caller 是否有管理权限（owner_id 或角色 owner 直通，其他成员需面板权限）"""
    member = db.query(ServerMember).filter_by(server_id=server_id, user_id=user_id).first()
    if not member:
        return False
    server = db.query(Server).filter_by(id=server_id).first()
    if (server and server.owner_id == user_id) or member.role.value == "owner":
        return True
    return _has_panel_perm(server_id, user_id, perm)


def _caller_can_manage_any(server_id: int, user_id: int, db: Session, perms: List[str]) -> bool:
    for perm in perms:
        if _caller_can_manage(server_id, user_id, db, perm):
            return True
    return False


def _require_server_owner(server_id: int, user_id: int, db: Session) -> Server:
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    if server.owner_id != user_id:
        raise HTTPException(403, "仅服主可执行此操作")
    return server


def _require_server_manage_perms(
    server_id: int,
    user_id: int,
    db: Session,
    perms: List[str],
    denied_message: str,
) -> Server:
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    if not _caller_can_manage_any(server_id, user_id, db, perms):
        raise HTTPException(403, denied_message)
    return server


def _require_panel_features_manage(server_id: int, user_id: int, db: Session) -> Server:
    return _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.features", "panel.membership.review", "panel.invites.manage", "panel.users"],
        "无权限，需要服务器 Owner 或相关面板权限",
    )


def _normalize_register_limit(limit_value: Optional[int]) -> int:
    try:
        limit = int(limit_value if limit_value is not None else 1)
    except Exception:
        limit = 1
    return max(0, min(50, limit))


def _normalize_blacklist_auto_reject_count(value: Optional[int]) -> int:
    try:
        count = int(value if value is not None else 0)
    except Exception:
        count = 0
    return max(0, min(99, count))


def _normalize_character_name_max_length(value: Optional[int]) -> int:
    try:
        length = int(value if value is not None else DEFAULT_CHARACTER_NAME_MAX_LENGTH)
    except Exception:
        length = DEFAULT_CHARACTER_NAME_MAX_LENGTH
    return max(1, min(50, length))


def _normalize_character_name_regex(value: Optional[str]) -> str:
    pattern = str(value or DEFAULT_CHARACTER_NAME_REGEX).strip()
    if not pattern:
        pattern = DEFAULT_CHARACTER_NAME_REGEX
    if len(pattern) > 256:
        raise HTTPException(400, "玩家名字正则长度不能超过 256")
    try:
        re.compile(pattern)
    except re.error as e:
        raise HTTPException(400, f"玩家名字正则无效: {e}")
    return pattern


def _find_blocked_character_name_char(value: str) -> Optional[str]:
    for ch in value or "":
        if unicodedata.category(ch) in BLOCKED_CHARACTER_NAME_CATEGORIES:
            return ch
    return None


def _validate_character_name_policy(server: Server, character_name: str):
    name = "" if character_name is None else str(character_name)
    max_len = _normalize_character_name_max_length(getattr(server, "character_name_max_length", DEFAULT_CHARACTER_NAME_MAX_LENGTH))
    pattern = _normalize_character_name_regex(getattr(server, "character_name_regex", DEFAULT_CHARACTER_NAME_REGEX))
    if not name:
        raise HTTPException(400, "玩家名字不能为空")
    if name != name.strip():
        raise HTTPException(400, "玩家名字不能包含前后空白字符")
    blocked = _find_blocked_character_name_char(name)
    if blocked is not None:
        raise HTTPException(400, "玩家名字不能包含空白、零宽字符、控制字符或不可见格式字符")
    if len(name) > max_len:
        raise HTTPException(400, f"玩家名字长度不能超过 {max_len} 个字符")
    if not re.fullmatch(pattern, name):
        raise HTTPException(400, "玩家名字不符合服务器设置的命名规则")


def _count_registered_characters(conn: sqlite3.Connection, agent_key: str, user_id: Optional[int] = None) -> int:
    if user_id is None:
        row = conn.execute(
            "SELECT COUNT(*) FROM AgentCharacterBindingsCache WHERE agent_key=?",
            (agent_key,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) FROM AgentCharacterBindingsCache WHERE agent_key=? AND user_id=?",
            (agent_key, user_id),
        ).fetchone()
    return int(row[0] if row and row[0] is not None else 0)


def _assert_user_register_quota_available(conn: sqlite3.Connection, server: Server, user_id: int):
    limit = _normalize_register_limit(getattr(server, "register_limit", 1))
    current = _count_registered_characters(conn, server.agent_key, user_id=user_id)
    if current >= limit:
        raise HTTPException(400, f"当前账号可注册角色已达上限（{limit}）")


def _blacklist_summary_for_user(conn: sqlite3.Connection, server_id: int, user_id: int) -> dict:
    conn.row_factory = sqlite3.Row
    local_rows = conn.execute(
        """
        SELECT
            b.id, b.reason, b.created_at,
            cb.email AS created_by_email
        FROM AgentServerBlacklistCache b
        LEFT JOIN users cb ON cb.id = b.created_by_user_id
        WHERE b.server_id=? AND b.target_user_id=? AND b.status='active'
        ORDER BY b.created_at DESC, b.id DESC
        """,
        (server_id, user_id),
    ).fetchall()
    cloud_rows = conn.execute(
        """
        SELECT
            c.id, c.reason, c.submitted_at, c.reviewed_at, c.review_note,
            s.name AS source_server_name,
            sb.email AS submitted_by_email,
            rb.email AS reviewed_by_email
        FROM CloudBlacklistEntries c
        LEFT JOIN servers s ON s.id = c.source_server_id
        LEFT JOIN users sb ON sb.id = c.submitted_by_user_id
        LEFT JOIN users rb ON rb.id = c.reviewed_by_user_id
        WHERE c.target_user_id=? AND c.status='approved'
        ORDER BY c.reviewed_at DESC, c.submitted_at DESC, c.id DESC
        """,
        (user_id,),
    ).fetchall()
    local_count = len(local_rows)
    cloud_count = len(cloud_rows)
    details = []
    for row in local_rows:
        details.append({
            "id": int(row["id"]),
            "scope": "server",
            "label": "本服务器黑名单",
            "reason": row["reason"] or "",
            "source_server_name": "",
            "operator_email": row["created_by_email"] or "",
            "review_note": "",
            "created_at": int(row["created_at"] or 0),
        })
    for row in cloud_rows:
        details.append({
            "id": int(row["id"]),
            "scope": "cloud",
            "label": "平台云黑",
            "reason": row["reason"] or "",
            "source_server_name": row["source_server_name"] or "",
            "operator_email": row["submitted_by_email"] or "",
            "reviewed_by_email": row["reviewed_by_email"] or "",
            "review_note": row["review_note"] or "",
            "created_at": int(row["submitted_at"] or 0),
            "reviewed_at": int(row["reviewed_at"] or 0),
        })
    flags = []
    if local_count:
        flags.append("本服务器黑名单")
    if cloud_count:
        flags.append(f"平台云黑 {cloud_count} 条")
    return {
        "server_blacklist_count": local_count,
        "cloud_blacklist_count": cloud_count,
        "blacklist_flags": flags,
        "blacklist_details": details,
    }


def _join_request_rows_with_blacklist(rows: List[sqlite3.Row], server_id: int) -> List[JoinRequestOut]:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        result = []
        for r in rows:
            item = dict(r)
            item.update(_blacklist_summary_for_user(conn, server_id, int(item["applicant_user_id"])))
            result.append(JoinRequestOut(**item))
    return result


def _join_review_receiver_ids(db: Session, server_id: int, applicant_user_id: int) -> List[int]:
    ids = set()
    server = db.query(Server).filter_by(id=server_id).first()
    if server and server.owner_id and int(server.owner_id) != applicant_user_id:
        ids.add(int(server.owner_id))
    members = db.query(ServerMember).filter_by(server_id=server_id).all()
    for member in members:
        mid = int(member.user_id)
        if mid == applicant_user_id:
            continue
        if _caller_can_manage_any(server_id, mid, db, ["panel.membership.review", "panel.users"]):
            ids.add(mid)
    return sorted(ids)


def _blacklist_summary_text(summary: dict) -> str:
    flags = summary.get("blacklist_flags") or []
    return "；".join(flags) if flags else "无黑名单记录"


def _blacklist_primary_reason(summary: dict, preferred_scope: str = "") -> str:
    details = summary.get("blacklist_details") or []
    for item in details:
        if preferred_scope and item.get("scope") != preferred_scope:
            continue
        reason = (item.get("reason") or "").strip()
        if reason:
            return reason
    for item in details:
        reason = (item.get("reason") or "").strip()
        if reason:
            return reason
    return ""


async def _delete_user_server_local_state(db: Session, server_id: int, user_id: int, agent_key: str) -> None:
    if agent_key in manager.active_agents:
        rows = db.execute(
            text("SELECT character_name FROM AgentCharacterBindingsCache WHERE agent_key = :agent_key AND user_id = :uid"),
            {"agent_key": agent_key, "uid": user_id},
        ).fetchall()
        for row in rows:
            character_name = row[0]
            if not character_name:
                continue
            try:
                await delete_character_on_agent(agent_key, character_name, user_id)
            except HTTPException:
                pass

    db.execute(
        text("DELETE FROM AgentCharacterBindingsCache WHERE agent_key = :agent_key AND user_id = :uid"),
        {"agent_key": agent_key, "uid": user_id},
    )


def _notify_join_reviewers(
    db: Session,
    server: Server,
    request_id: int,
    applicant_user_id: int,
    status: str,
    blacklist_summary: dict,
    review_note: str = "",
):
    applicant_email = _get_user_email(applicant_user_id)
    status_label = {"pending": "待审批", "approved": "已自动通过", "rejected": "已自动拒绝"}.get(status, status)
    blacklist_text = _blacklist_summary_text(blacklist_summary)
    note_text = f"，原因：{review_note}" if review_note else ""
    content = f"{applicant_email} 申请加入服务器 {server.name}，状态：{status_label}{note_text}。黑名单记录：{blacklist_text}"
    for receiver_id in _join_review_receiver_ids(db, int(server.id), applicant_user_id):
        create_notification(
            receiver_user_id=receiver_id,
            sender_user_id=applicant_user_id,
            server_id=int(server.id),
            msg_type="join_request_pending" if status == "pending" else "join_request_result",
            ref_type="join_request",
            ref_id=request_id,
            title="新的入服申请",
            content=content,
            payload={
                "server_id": int(server.id),
                "request_id": request_id,
                "status": status,
                "blacklist": blacklist_summary,
                "review_note": review_note,
            },
        )


def _server_to_out(s: Server, db: Session, user_id: Optional[int] = None) -> ServerOut:
    server_role = None
    panel_group_name = None
    panel_permissions = None
    if user_id is not None:
        membership = db.query(ServerMember).filter_by(server_id=s.id, user_id=user_id).first()
        if membership:
            server_role = membership.role.value
            if membership.access_group_id:
                with sqlite3.connect(AUTH_DB_PATH) as _conn:
                    pg_row = _conn.execute(
                        "SELECT id, name FROM ServerAccessGroups WHERE id=? AND server_id=?",
                        (membership.access_group_id, s.id),
                    ).fetchone()
                    if pg_row:
                        panel_group_name = pg_row[1]
                        panel_permissions = _collect_panel_group_permissions(_conn, s.id, pg_row[0])

    return ServerOut(
        id=s.id,
        server_code=(s.server_code or ""),
        name=s.name,
        description=s.description or "",
        agent_key=s.agent_key,
        owner_id=s.owner_id,
        created_at=s.created_at,
        is_public=bool(s.is_public),
        join_requires_approval=bool(getattr(s, "join_requires_approval", False)),
        online=s.agent_key in manager.active_agents,
        member_count=db.query(ServerMember).filter_by(server_id=s.id).count(),
        server_role=server_role,
        panel_group_name=panel_group_name,
        panel_permissions=panel_permissions,
        game_ip=s.game_ip or "",
        game_port=s.game_port,
        qq_group=s.qq_group or "",
        game_version=s.game_version or "",
        show_ip=bool(s.show_ip) if s.show_ip is not None else True,
        register_limit=_normalize_register_limit(getattr(s, "register_limit", 1)),
        blacklist_auto_reject_count=_normalize_blacklist_auto_reject_count(getattr(s, "blacklist_auto_reject_count", 0)),
        character_name_regex=_normalize_character_name_regex(getattr(s, "character_name_regex", DEFAULT_CHARACTER_NAME_REGEX)),
        character_name_max_length=_normalize_character_name_max_length(getattr(s, "character_name_max_length", DEFAULT_CHARACTER_NAME_MAX_LENGTH)),
        platform_status=getattr(s, "platform_status", "active") or "active",
        platform_audit_status=getattr(s, "platform_audit_status", "pending") or "pending",
        platform_audit_reason=getattr(s, "platform_audit_reason", None),
        platform_is_public=bool(getattr(s, "platform_is_public", False)),
    )


# ── 认领服务器 ───────────────────────────────────────────────────

@router.post("/claim", response_model=ServerOut, summary="凭 agent_key 认领服务器")
def claim_server(
    req: ServerClaimReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        agent_key = (req.agent_key or "").strip()
        if not agent_key:
            raise HTTPException(400, "agent_key 不能为空")

        max_servers_raw = _get_platform_setting("platform.max_servers_per_user", "3")
        try:
            max_servers = int(max_servers_raw or 0)
        except Exception:
            max_servers = 0
        if max_servers > 0:
            owned_count = db.query(Server).filter(
                Server.owner_id == user_id,
                Server.platform_status != "deleted",
            ).count()
            if owned_count >= max_servers:
                raise HTTPException(403, f"你最多只能创建 {max_servers} 个服务器")

        # 认领前必须验证 Agent 当前在线，避免无效 key 被误认领
        if agent_key not in manager.active_agents:
            raise HTTPException(400, "该 Agent 当前未连接，无法认领，请先启动并连接 Agent")

        server = db.query(Server).filter_by(agent_key=agent_key).first()
        require_public_audit = _get_platform_bool_setting(
            "platform.server.require_audit_before_public", True
        )
        require_online_audit = _get_platform_bool_setting(
            "platform.server.require_audit_before_online", True
        )
        needs_audit = require_public_audit or require_online_audit
        initial_audit_status = "pending" if needs_audit else "approved"
        initial_platform_status = "inactive" if require_online_audit else "active"
        initial_platform_public = bool(req.is_public) and not require_public_audit and initial_platform_status == "active"

        if server is None:
            server = Server(
                name=req.name,
                description=req.description,
                agent_key=agent_key,
                server_code=_generate_server_code(db),
                owner_id=user_id,
                is_public=req.is_public,
                platform_status=initial_platform_status,
                platform_audit_status=initial_audit_status,
                platform_is_public=initial_platform_public,
                join_requires_approval=req.join_requires_approval,
                game_ip=req.game_ip or "",
                game_port=req.game_port,
                qq_group=req.qq_group or "",
                game_version=req.game_version or "",
                show_ip=req.show_ip,
                created_at=int(time.time()),
            )
            db.add(server)
            db.flush()
        elif server.owner_id is not None:
            raise HTTPException(409, "该服务器已被认领，无法重复认领")
        else:
            server.owner_id = user_id
            if not (server.server_code or "").strip():
                server.server_code = _generate_server_code(db)
            server.name = req.name
            server.description = req.description
            server.is_public = req.is_public
            server.platform_status = initial_platform_status
            server.platform_audit_status = initial_audit_status
            server.platform_audit_reason = None
            server.platform_audit_by = None
            server.platform_audit_at = None
            server.platform_is_public = initial_platform_public
            server.join_requires_approval = req.join_requires_approval
            server.game_ip = req.game_ip or ""
            server.game_port = req.game_port
            server.qq_group = req.qq_group or ""
            server.game_version = req.game_version or ""
            server.show_ip = req.show_ip

        _init_server_access_groups(server.id, db=db)
        add_member(
            db=db,
            server_id=server.id,
            user_id=user_id,
            source="owner_claim",
            role=ServerMemberRole.owner,
            access_group_id=_server_access_group_id(server.id, "服主", db=db),
            joined_by_user_id=user_id,
        )

        db.commit()
        db.refresh(server)
        return _server_to_out(server, db, user_id=user_id)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


# ── 统一入服申请 ────────────────────────────────────────────────

def _submit_join_request(
    server: Server,
    applicant_user_id: int,
    message: str,
    db: Session,
):
    server_id = int(server.id)
    if server.owner_id is None:
        raise HTTPException(400, "该服务器尚未被认领")
    if getattr(server, "platform_status", "active") != "active":
        raise HTTPException(403, "该服务器已被平台下架或未启用，暂不能申请加入")
    if getattr(server, "platform_audit_status", "pending") != "approved":
        raise HTTPException(403, "该服务器尚未通过平台审核，暂不能申请加入")

    existing_member = db.query(ServerMember).filter_by(server_id=server_id, user_id=applicant_user_id).first()
    if existing_member:
        raise HTTPException(409, "您已在该服务器中")

    now_ts = int(time.time())
    normalized_message = (message or "").strip()
    auto_reject = False
    auto_reject_note = ""
    reject_reason_text = ""
    auto_approve = not bool(getattr(server, "join_requires_approval", False))

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        blacklist_summary = _blacklist_summary_for_user(conn, server_id, applicant_user_id)
        cloud_threshold = _normalize_blacklist_auto_reject_count(getattr(server, "blacklist_auto_reject_count", 0))
        if blacklist_summary["server_blacklist_count"] > 0:
            auto_reject = True
            auto_reject_note = "该账号已在本服务器黑名单中"
        elif cloud_threshold > 0 and blacklist_summary["cloud_blacklist_count"] >= cloud_threshold:
            auto_reject = True
            auto_reject_note = f"平台云黑记录达到 {cloud_threshold} 条"

        if auto_reject:
            reject_detail = _blacklist_primary_reason(
                blacklist_summary,
                "server" if blacklist_summary["server_blacklist_count"] > 0 else "cloud",
            )
            reject_reason_text = f"{auto_reject_note}：{reject_detail}" if reject_detail else auto_reject_note
            return {
                "ok": True,
                "request_id": None,
                "status": "rejected",
                "auto_approved": False,
                "auto_rejected": True,
                "reject_reason": reject_reason_text,
                "blacklist": blacklist_summary,
            }

        status = "approved" if auto_approve else "pending"
        reviewed_by_user_id = int(server.owner_id) if auto_approve else None
        reviewed_at = now_ts if auto_approve else None
        review_note = "审核关闭，自动通过" if auto_approve else ""

        pending = conn.execute(
            """
            SELECT id FROM ServerMemberRequests
            WHERE server_id=? AND request_type='join' AND from_user_id=? AND status='pending'
            """,
            (server_id, applicant_user_id),
        ).fetchone()
        if pending:
            raise HTTPException(409, "您已有待处理申请，请勿重复提交")

        cur = conn.execute(
            """
            INSERT INTO ServerMemberRequests(
                server_id, request_type, from_user_id, to_user_id, message,
                status, reviewed_by_user_id, reviewed_at,
                review_note, withdrawn_at, expires_at, acted_at,
                created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                server_id,
                "join",
                applicant_user_id,
                None,
                normalized_message,
                status,
                reviewed_by_user_id,
                reviewed_at,
                review_note,
                None,
                None,
                None,
                now_ts,
                now_ts,
            ),
        )
        conn.commit()
        request_id = int(cur.lastrowid)

    if auto_approve:
        try:
            add_member(
                db=db,
                server_id=server_id,
                user_id=applicant_user_id,
                source="join_request_approved",
                role=ServerMemberRole.member,
                access_group_id=_server_access_group_id(server_id, "成员", db=db),
                source_ref_type="join_request",
                source_ref_id=request_id,
                joined_by_user_id=int(server.owner_id),
            )
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(500, f"数据库错误: {e}")

        create_notification(
            receiver_user_id=applicant_user_id,
            sender_user_id=int(server.owner_id) if server.owner_id else None,
            server_id=server_id,
            msg_type="join_request_result",
            ref_type="join_request",
            ref_id=request_id,
            title="入服申请结果",
            content="你的入服申请已自动通过",
            payload={"server_id": server_id, "request_id": request_id, "status": "approved", "auto": True},
        )

    _notify_join_reviewers(
        db=db,
        server=server,
        request_id=request_id,
        applicant_user_id=applicant_user_id,
        status=status,
        blacklist_summary=blacklist_summary,
        review_note=review_note,
    )

    return {
        "ok": True,
        "request_id": request_id,
        "status": status,
        "auto_approved": auto_approve,
        "auto_rejected": False,
        "reject_reason": "",
        "blacklist": blacklist_summary,
    }


@router.post("/apply", summary="按服务器编号提交入服申请")
def apply_join_request_by_code(
    req: ServerJoinReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    code = _normalize_server_code(req.server_code)
    if not code:
        raise HTTPException(400, "服务器编号不能为空")
    server = db.query(Server).filter_by(server_code=code).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    return _submit_join_request(server, user_id, "", db)


@router.post("/{server_id}/apply", summary="提交入服申请")
def apply_join_request(
    server_id: int,
    req: ServerApplyReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    return _submit_join_request(server, user_id, req.message or "", db)


@router.get("/{server_id}/join-requests", response_model=List[JoinRequestOut], summary="列出入服申请（服主/授权管理）")
def list_join_requests(
    server_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.membership.review", "panel.users"],
        "仅服主或具备审批权限的管理员可查看申请",
    )
    valid_status = {"pending", "approved", "rejected", "withdrawn"}
    if status and status not in valid_status:
        raise HTTPException(400, "状态无效")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT
                r.id, r.server_id, r.applicant_user_id, au.email AS applicant_email,
                r.message, r.status, r.reviewed_by_user_id,
                ru.email AS reviewed_by_email,
                r.review_note, r.created_at, r.updated_at, r.withdrawn_at
            FROM (
                SELECT *, from_user_id AS applicant_user_id
                FROM ServerMemberRequests
                WHERE request_type='join'
            ) r
            JOIN users au ON au.id = r.applicant_user_id
            LEFT JOIN users ru ON ru.id = r.reviewed_by_user_id
            WHERE r.server_id=?
        """
        params = [server_id]
        if status:
            sql += " AND r.status=?"
            params.append(status)
        sql += " ORDER BY r.created_at DESC, r.id DESC"
        rows = conn.execute(sql, tuple(params)).fetchall()

    return _join_request_rows_with_blacklist(rows, server_id)


@router.post("/{server_id}/join-requests/{request_id}/withdraw", summary="撤回入服申请（申请人）")
def withdraw_join_request(
    server_id: int,
    request_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")

    now_ts = int(time.time())
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT id, status FROM ServerMemberRequests
            WHERE id=? AND server_id=? AND request_type='join' AND from_user_id=?
            """,
            (request_id, server_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "申请不存在")
        if row[1] != "pending":
            raise HTTPException(409, f"当前申请状态为 {row[1]}，不可撤回")

        conn.execute(
            """
            UPDATE ServerMemberRequests
            SET status='withdrawn', withdrawn_at=?, updated_at=?
            WHERE id=? AND request_type='join'
            """,
            (now_ts, now_ts, request_id),
        )
        conn.commit()

    return {"ok": True, "status": "withdrawn"}


@router.post("/{server_id}/join-requests/{request_id}/approve", summary="批准入服申请（服主/授权管理）")
def approve_join_request(
    server_id: int,
    request_id: int,
    req: JoinRequestReviewReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.membership.review", "panel.users"],
        "仅服主或具备审批权限的管理员可批准申请",
    )

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, applicant_user_id, status
            FROM (
                SELECT *, from_user_id AS applicant_user_id
                FROM ServerMemberRequests
                WHERE request_type='join'
            )
            WHERE id=? AND server_id=?
            """,
            (request_id, server_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "申请不存在")
    if row["status"] != "pending":
        raise HTTPException(409, f"当前申请状态为 {row['status']}，不可批准")

    applicant_user_id = int(row["applicant_user_id"])
    existing_member = db.query(ServerMember).filter_by(server_id=server_id, user_id=applicant_user_id).first()
    if not existing_member:
        try:
            add_member(
                db=db,
                server_id=server_id,
                user_id=applicant_user_id,
                source="join_request_approved",
                role=ServerMemberRole.member,
                access_group_id=_server_access_group_id(server_id, "成员", db=db),
                source_ref_type="join_request",
                source_ref_id=request_id,
                joined_by_user_id=user_id,
            )
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(500, f"数据库错误: {e}")

    now_ts = int(time.time())
    review_note = (req.note or "").strip()
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.execute(
            """
            UPDATE ServerMemberRequests
            SET status='approved', reviewed_by_user_id=?, reviewed_at=?, review_note=?, updated_at=?
            WHERE id=? AND request_type='join'
            """,
            (user_id, now_ts, review_note, now_ts, request_id),
        )
        conn.commit()

    create_notification(
        receiver_user_id=applicant_user_id,
        sender_user_id=user_id,
        server_id=server_id,
        msg_type="join_request_result",
        ref_type="join_request",
        ref_id=request_id,
        title="入服申请结果",
        content="你的入服申请已通过",
        payload={"server_id": server_id, "request_id": request_id, "status": "approved"},
    )

    return {"ok": True, "status": "approved"}


@router.post("/{server_id}/join-requests/{request_id}/reject", summary="拒绝入服申请（服主/授权管理）")
def reject_join_request(
    server_id: int,
    request_id: int,
    req: JoinRequestReviewReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.membership.review", "panel.users"],
        "仅服主或具备审批权限的管理员可拒绝申请",
    )

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, applicant_user_id, status
            FROM (
                SELECT *, from_user_id AS applicant_user_id
                FROM ServerMemberRequests
                WHERE request_type='join'
            )
            WHERE id=? AND server_id=?
            """,
            (request_id, server_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "申请不存在")
        if row["status"] != "pending":
            raise HTTPException(409, f"当前申请状态为 {row['status']}，不可拒绝")

        now_ts = int(time.time())
        review_note = (req.note or "").strip()
        conn.execute(
            """
            UPDATE ServerMemberRequests
            SET status='rejected', reviewed_by_user_id=?, reviewed_at=?, review_note=?, updated_at=?
            WHERE id=? AND request_type='join'
            """,
            (user_id, now_ts, review_note, now_ts, request_id),
        )
        conn.commit()

    create_notification(
        receiver_user_id=int(row["applicant_user_id"]),
        sender_user_id=user_id,
        server_id=server_id,
        msg_type="join_request_rejected",
        ref_type="join_request",
        ref_id=request_id,
        title="入服申请结果",
        content=f"你的入服申请未通过{('，原因：' + review_note) if review_note else ''}",
        payload={"server_id": server_id, "request_id": request_id, "status": "rejected", "note": review_note},
    )

    return {"ok": True, "status": "rejected"}


@router.post("/{server_id}/invites", summary="服主/授权管理邀请用户加入服务器")
def create_server_invite(
    server_id: int,
    req: ServerInviteCreateReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.invites.manage", "panel.membership.review", "panel.users"],
        "仅服主或具备邀请权限的管理员可发送邀请",
    )
    invitee_email = normalize_qq_email(req.invitee_email, "请输入受邀用户的 QQ 号或 QQ 邮箱")
    invitee_user_id = _get_user_id_by_email(invitee_email)
    if not invitee_user_id:
        raise HTTPException(404, "受邀用户不存在")
    if invitee_user_id == user_id:
        raise HTTPException(400, "不能邀请自己")

    existing_member = db.query(ServerMember).filter_by(server_id=server_id, user_id=invitee_user_id).first()
    if existing_member:
        raise HTTPException(409, "该用户已是服务器成员")

    now_ts = int(time.time())
    expires_in_hours = int(req.expires_in_hours or 72)
    expires_at = now_ts + max(1, min(720, expires_in_hours)) * 3600
    message = (req.message or "").strip()

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        pending = conn.execute(
            """
            SELECT id FROM ServerMemberRequests
            WHERE server_id=? AND request_type='invite' AND to_user_id=? AND status='pending'
            """,
            (server_id, invitee_user_id),
        ).fetchone()
        if pending:
            raise HTTPException(409, "该用户已有待处理邀请")

        cur = conn.execute(
            """
            INSERT INTO ServerMemberRequests(
                server_id, request_type, from_user_id, to_user_id,
                message, status, expires_at, acted_at,
                created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                server_id,
                "invite",
                user_id,
                invitee_user_id,
                message,
                "pending",
                expires_at,
                None,
                now_ts,
                now_ts,
            ),
        )
        conn.commit()
        invite_id = int(cur.lastrowid)

    create_notification(
        receiver_user_id=invitee_user_id,
        sender_user_id=user_id,
        server_id=server_id,
        msg_type="invite",
        ref_type="invite",
        ref_id=invite_id,
        title="收到服务器邀请",
        content=f"你收到加入服务器 {server.name} 的邀请",
        payload={"server_id": server_id, "invite_id": invite_id, "expires_at": expires_at},
    )

    return {"ok": True, "invite_id": invite_id, "status": "pending", "expires_at": expires_at}


@router.get("/{server_id}/invites", response_model=List[ServerInviteOut], summary="列出服务器邀请记录（服主/授权管理）")
def list_server_invites(
    server_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.invites.manage", "panel.membership.review", "panel.users"],
        "仅服主或具备邀请权限的管理员可查看邀请记录",
    )
    valid_status = {"pending", "accepted", "rejected", "canceled", "expired"}
    if status and status not in valid_status:
        raise HTTPException(400, "状态无效")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT
                i.id, i.server_id, COALESCE(s.name, '') AS server_name,
                COALESCE(s.server_code, '') AS server_code,
                i.inviter_user_id, inviter.email AS inviter_email,
                i.invitee_user_id, invitee.email AS invitee_email,
                i.message, i.status, i.expires_at, i.acted_at,
                i.created_at, i.updated_at
            FROM (
                SELECT *, from_user_id AS inviter_user_id, to_user_id AS invitee_user_id
                FROM ServerMemberRequests
                WHERE request_type='invite'
            ) i
            LEFT JOIN servers s ON s.id = i.server_id
            JOIN users inviter ON inviter.id = i.inviter_user_id
            JOIN users invitee ON invitee.id = i.invitee_user_id
            WHERE i.server_id=?
        """
        params = [server_id]
        if status:
            sql += " AND i.status=?"
            params.append(status)
        sql += " ORDER BY i.created_at DESC, i.id DESC"
        rows = conn.execute(sql, tuple(params)).fetchall()

    return [ServerInviteOut(**dict(r)) for r in rows]


# ── 查询当前用户参与的服务器 ─────────────────────────────────────

@router.get("", response_model=List[ServerOut], summary="列出当前用户参与的所有服务器")
def list_my_servers(
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        memberships = db.query(ServerMember).filter_by(user_id=user_id).all()
        result = []
        for m in memberships:
            s = db.query(Server).filter_by(id=m.server_id).first()
            if s:
                result.append(_server_to_out(s, db, user_id=user_id))
        return result
    except SQLAlchemyError as e:
        raise HTTPException(500, f"数据库错误: {e}")

# ── 公开服务器列表（登录后可阅览）────────────────────────────────

@router.get("/public", response_model=List[ServerOut], summary="列出所有公开的服务器")
def list_public_servers(
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        servers_q = db.query(Server).filter(
            Server.is_public == True,
            Server.platform_is_public == True,
            Server.platform_status == "active",
            Server.platform_audit_status == "approved",
        ).all()
        result = []
        for s in servers_q:
            out = _server_to_out(s, db, user_id=user_id)
            out_dict = out.model_dump()
            out_dict['agent_key'] = ''   # 公开列表不返回 agent_key
            result.append(ServerOut(**out_dict))
        return result
    except SQLAlchemyError as e:
        raise HTTPException(500, f"数据库错误: {e}")

# ── 服务器详情（含成员列表）──────────────────────────────────────

@router.get("/{server_id}", response_model=ServerDetailOut, summary="获取服务器详情")
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        member = db.query(ServerMember).filter_by(
            server_id=server_id, user_id=user_id
        ).first()
        if not member:
            raise HTTPException(403, "无访问权限")

        server = db.query(Server).filter_by(id=server_id).first()
        if not server:
            raise HTTPException(404, "服务器不存在")

        members_out: List[ServerMemberOut] = []
        with sqlite3.connect(AUTH_DB_PATH) as _conn:
            for m in db.query(ServerMember).filter_by(server_id=server_id).all():
                pg_row = None
                if m.access_group_id:
                    pg_row = _conn.execute(
                        "SELECT id, name FROM ServerAccessGroups WHERE id=? AND server_id=?",
                        (m.access_group_id, server_id),
                    ).fetchone()
                members_out.append(ServerMemberOut(
                    user_id=m.user_id,
                    email=_get_user_email(m.user_id),
                    role=m.role.value,
                    joined_at=m.joined_at,
                    panel_group_id=pg_row[0] if pg_row else None,
                    panel_group_name=pg_row[1] if pg_row else None,
                ))

        base = _server_to_out(server, db, user_id=user_id)
        return ServerDetailOut(**base.model_dump(), members=members_out)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(500, f"数据库错误: {e}")


# ── 离开服务器 ───────────────────────────────────────────────────

@router.delete("/{server_id}/leave", summary="离开服务器")
async def leave_server(
    server_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        server = db.query(Server).filter_by(id=server_id).first()
        if not server:
            raise HTTPException(404, "服务器不存在")
        if server.owner_id == user_id:
            raise HTTPException(400, "Owner 无法直接离开，请先转让或解散服务器")

        member = db.query(ServerMember).filter_by(
            server_id=server_id, user_id=user_id
        ).first()
        if not member:
            raise HTTPException(404, "您不在该服务器中")

        db.delete(member)
        await _delete_user_server_local_state(db, server_id, user_id, server.agent_key)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


# ── 踢出成员（Owner 专属）────────────────────────────────────────

@router.delete("/{server_id}/members/{target_user_id}", summary="踢出成员（Owner 专属）")
async def kick_member(
    server_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        server = db.query(Server).filter_by(id=server_id).first()
        if not server:
            raise HTTPException(404, "服务器不存在")
        if server.owner_id != user_id:
            raise HTTPException(403, "仅 Owner 可踢出成员")
        if target_user_id == user_id:
            raise HTTPException(400, "不能踢出自己")

        member = db.query(ServerMember).filter_by(
            server_id=server_id, user_id=target_user_id
        ).first()
        if not member:
            raise HTTPException(404, "目标用户不在该服务器中")

        db.delete(member)
        await _delete_user_server_local_state(db, server_id, target_user_id, server.agent_key)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


# ── 黑名单管理 ───────────────────────────────────────────────────

@router.get("/{server_id}/blacklist", summary="列出本服务器黑名单")
def list_server_blacklist(
    server_id: int,
    q: str = "",
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.blacklist", "panel.users"],
        "无权限，需要服务器 Owner 或黑名单管理权限",
    )
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        where_sql = "b.server_id=? AND b.status='active'"
        params = [server_id]
        keyword = (q or "").strip()
        if keyword:
            like = f"%{keyword}%"
            where_sql += """
                AND (
                    b.target_email LIKE ?
                    OR b.reason LIKE ?
                    OR cu.email LIKE ?
                    OR CAST(b.target_user_id AS TEXT) LIKE ?
                )
            """
            params.extend([like, like, like, like])
        rows = conn.execute(
            f"""
            SELECT
                b.id, b.server_id, b.target_user_id, b.target_email,
                b.reason, b.status, b.created_by_user_id,
                cu.email AS created_by_email,
                b.created_at, b.removed_by_user_id, b.removed_at
            FROM AgentServerBlacklistCache b
            LEFT JOIN users cu ON cu.id = b.created_by_user_id
            WHERE {where_sql}
            ORDER BY b.created_at DESC, b.id DESC
            """,
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/{server_id}/blacklist", summary="加入本服务器黑名单")
async def add_server_blacklist(
    server_id: int,
    req: BlacklistCreateReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.blacklist", "panel.users"],
        "无权限，需要服务器 Owner 或黑名单管理权限",
    )
    target_user_id = int(req.target_user_id)
    if target_user_id == server.owner_id:
        raise HTTPException(400, "不能将服务器服主加入本服务器黑名单")
    target_email = _get_user_email(target_user_id)
    if not target_email:
        raise HTTPException(404, "目标账号不存在")

    now_ts = int(time.time())
    reason = (req.reason or "").strip()
    operator_email = _get_user_email(user_id) or ""
    agent_row = await add_blacklist_on_agent(
        server.agent_key,
        target_user_id,
        target_email,
        reason,
        user_id,
        operator_email,
    )
    created_at = int(agent_row.get("created_at") or now_ts)
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO AgentServerBlacklistCache(
                    server_id, target_user_id, target_email, reason,
                    status, created_by_user_id, created_at
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (server_id, target_user_id, target_email, reason, "active", user_id, created_at),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        pass

    return {"ok": True}


@router.delete("/{server_id}/blacklist/{entry_id}", summary="移除本服务器黑名单")
async def remove_server_blacklist(
    server_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.blacklist", "panel.users"],
        "无权限，需要服务器 Owner 或黑名单管理权限",
    )
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT target_user_id FROM AgentServerBlacklistCache WHERE id=? AND server_id=? AND status='active'",
            (entry_id, server_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "黑名单记录不存在")

    operator_email = _get_user_email(user_id) or ""
    agent_row = await remove_blacklist_on_agent(
        server.agent_key,
        int(row[0]),
        user_id,
        operator_email,
    )
    now_ts = int(agent_row.get("removed_at") or time.time())
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        cur = conn.execute(
            """
            UPDATE AgentServerBlacklistCache
            SET status='removed', removed_by_user_id=?, removed_at=?
            WHERE id=? AND server_id=? AND status='active'
            """,
            (user_id, now_ts, entry_id, server_id),
        )
        conn.commit()
    if int(cur.rowcount or 0) <= 0:
        raise HTTPException(404, "黑名单记录不存在")
    return {"ok": True}


@router.post("/{server_id}/cloud-blacklist-submissions", summary="提交平台云黑审核")
def submit_cloud_blacklist(
    server_id: int,
    req: BlacklistCreateReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_server_manage_perms(
        server_id,
        user_id,
        db,
        ["panel.blacklist", "panel.users"],
        "无权限，需要服务器 Owner 或黑名单管理权限",
    )
    target_user_id = int(req.target_user_id)
    if target_user_id == server.owner_id:
        raise HTTPException(400, "不能将服务器服主提交到平台云黑")
    reason = (req.reason or "").strip()
    if not reason:
        raise HTTPException(400, "提交平台云黑必须填写原因")
    target_email = _get_user_email(target_user_id)
    if not target_email:
        raise HTTPException(404, "目标账号不存在")

    now_ts = int(time.time())
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cur = conn.execute(
                """
                INSERT INTO CloudBlacklistEntries(
                    target_user_id, target_email, source_server_id,
                    reason, status, submitted_by_user_id, submitted_at
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (target_user_id, target_email, server_id, reason, "pending", user_id, now_ts),
            )
            conn.commit()
            submission_id = int(cur.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "该账号已有来自本服务器的待审核或已通过云黑记录")

    return {"ok": True, "submission_id": submission_id, "status": "pending"}


# ── 解散服务器（Owner 专属）──────────────────────────────────────

@router.delete("/{server_id}", summary="解散服务器（Owner 专属）")
def dissolve_server(
    server_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        server = db.query(Server).filter_by(id=server_id).first()
        if not server:
            raise HTTPException(404, "服务器不存在")
        if server.owner_id != user_id:
            raise HTTPException(403, "仅 Owner 可解散服务器")

        agent_key = server.agent_key
        db.execute(text("DELETE FROM ServerAccessGroups WHERE server_id = :sid"), {"sid": server_id})
        db.execute(text("DELETE FROM ServerMemberRequests WHERE server_id = :sid"), {"sid": server_id})
        db.execute(text("DELETE FROM AgentServerBlacklistCache WHERE server_id = :sid"), {"sid": server_id})
        db.execute(text("DELETE FROM CloudBlacklistEntries WHERE source_server_id = :sid"), {"sid": server_id})
        db.execute(text("DELETE FROM messages WHERE server_id = :sid"), {"sid": server_id})
        db.execute(text("DELETE FROM announcements WHERE server_id = :sid"), {"sid": server_id})
        if agent_key:
            db.execute(text("DELETE FROM AgentCharacterBindingsCache WHERE agent_key = :agent_key"), {"agent_key": agent_key})
        db.delete(server)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


# ── 更新服务器信息（Owner 专属）──────────────────────────────────

@router.patch("/{server_id}", response_model=ServerOut, summary="更新服务器名称/描述/可见性（Owner 专属）")
def update_server(
    server_id: int,
    req: ServerUpdateReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    if server.owner_id != user_id:
        raise HTTPException(403, "仅 Owner 可修改服务器信息")
    if req.name is not None:
        req.name = req.name.strip()
        if not req.name:
            raise HTTPException(400, "服务器名称不能为空")
        server.name = req.name
    if req.description is not None:
        server.description = req.description
    if req.is_public is not None:
        was_user_public = bool(server.is_public)
        was_platform_public = bool(getattr(server, "platform_is_public", False))
        require_public_audit = _get_platform_bool_setting("platform.server.require_audit_before_public", True)
        server.is_public = req.is_public
        if not req.is_public:
            server.platform_is_public = False
        elif require_public_audit:
            already_publicly_approved = (
                was_user_public
                and was_platform_public
                and server.platform_audit_status == "approved"
            )
            if not already_publicly_approved:
                server.platform_is_public = False
                server.platform_audit_status = "pending"
                server.platform_audit_reason = "申请公开展示，等待平台审核"
                server.platform_audit_by = None
                server.platform_audit_at = None
        elif (
            server.platform_status == "active"
            and server.platform_audit_status == "approved"
        ):
            server.platform_is_public = True
        else:
            server.platform_is_public = False
    if req.join_requires_approval is not None:
        server.join_requires_approval = req.join_requires_approval
    if req.game_ip is not None:
        server.game_ip = req.game_ip
    if req.game_port is not None:
        server.game_port = req.game_port
    if req.qq_group is not None:
        server.qq_group = req.qq_group
    if req.game_version is not None:
        server.game_version = req.game_version
    if req.show_ip is not None:
        server.show_ip = req.show_ip
    try:
        db.commit()
        db.refresh(server)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")
    member_count = db.query(ServerMember).filter_by(server_id=server_id).count()
    return ServerOut(
        id=server.id,
        server_code=(server.server_code or ""),
        name=server.name,
        description=server.description or "",
        agent_key=server.agent_key, owner_id=server.owner_id,
        created_at=server.created_at, is_public=bool(server.is_public),
        join_requires_approval=bool(getattr(server, "join_requires_approval", False)),
        online=server.agent_key in manager.active_agents,
        member_count=member_count,
        game_ip=server.game_ip or "",
        game_port=server.game_port,
        qq_group=server.qq_group or "",
        game_version=server.game_version or "",
        show_ip=bool(server.show_ip) if server.show_ip is not None else True,
        register_limit=_normalize_register_limit(getattr(server, "register_limit", 1)),
        character_name_regex=_normalize_character_name_regex(getattr(server, "character_name_regex", DEFAULT_CHARACTER_NAME_REGEX)),
        character_name_max_length=_normalize_character_name_max_length(getattr(server, "character_name_max_length", DEFAULT_CHARACTER_NAME_MAX_LENGTH)),
        platform_status=getattr(server, "platform_status", "active") or "active",
        platform_audit_status=getattr(server, "platform_audit_status", "pending") or "pending",
        platform_audit_reason=getattr(server, "platform_audit_reason", None),
        platform_is_public=bool(getattr(server, "platform_is_public", False)),
    )


# ── 更新成员面板角色（Owner 专属）────────────────────────────────

@router.patch("/{server_id}/members/{target_user_id}/role", summary="修改成员面板角色（Owner 专属）")
def update_member_role(
    server_id: int,
    target_user_id: int,
    req: UpdateMemberRoleReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        server = db.query(Server).filter_by(id=server_id).first()
        if not server:
            raise HTTPException(404, "服务器不存在")
        if server.owner_id != user_id:
            raise HTTPException(403, "仅 Owner 可修改成员角色")
        if target_user_id == user_id:
            raise HTTPException(400, "不能修改自己的角色")

        allowed_roles = {r.value for r in ServerMemberRole}
        if req.role not in allowed_roles:
            raise HTTPException(400, f"无效角色，可选: {allowed_roles}")

        member = db.query(ServerMember).filter_by(
            server_id=server_id, user_id=target_user_id
        ).first()
        if not member:
            raise HTTPException(404, "目标用户不在该服务器中")

        member.role = ServerMemberRole(req.role)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


# ── 获取指定成员在服务器的游戏角色（Owner 或具备 panel.users）──────────────

@router.get("/{server_id}/members/{target_user_id}/characters", summary="获取指定成员的游戏角色（Owner 或具备 panel.users）")
def get_member_characters(
    server_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    if not _caller_can_manage(server_id, user_id, db, "panel.users"):
        raise HTTPException(403, "无管理权限")
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        rows = conn.execute(
            "SELECT character_name, registered_at FROM AgentCharacterBindingsCache "
            "WHERE user_id=? AND agent_key=? ORDER BY registered_at DESC",
            (target_user_id, server.agent_key),
        ).fetchall()
    return [{"character_name": r[0], "registered_at": r[1]} for r in rows]


# ── 获取当前用户自己在服务器的游戏角色（所有成员可用）──────────────────────

@router.get("/{server_id}/my-characters", summary="获取当前用户在该服务器的游戏角色")
def get_my_characters(
    server_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    member = db.query(ServerMember).filter_by(server_id=server_id, user_id=user_id).first()
    if not member:
        raise HTTPException(403, "您不是该服务器成员")
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        rows = conn.execute(
            "SELECT character_name, registered_at FROM AgentCharacterBindingsCache "
            "WHERE user_id=? AND agent_key=? ORDER BY registered_at DESC",
            (user_id, server.agent_key),
        ).fetchall()
    return [{"character_name": r[0], "registered_at": r[1]} for r in rows]


# ── 玩家删除自己的游戏角色 ────────────────────────────────────────────────

@router.delete("/{server_id}/my-characters/{character_name}", summary="玩家删除自己的游戏角色绑定")
async def delete_my_character(
    server_id: int,
    character_name: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    member = db.query(ServerMember).filter_by(server_id=server_id, user_id=user_id).first()
    if not member:
        raise HTTPException(403, "您不是该服务器成员")
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")

    await delete_character_on_agent(server.agent_key, character_name, user_id)

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM AgentCharacterBindingsCache WHERE user_id=? AND agent_key=? AND character_name=?",
            (user_id, server.agent_key, character_name),
        ).fetchone()
        if row:
            conn.execute("DELETE FROM AgentCharacterBindingsCache WHERE id=?", (row[0],))
            conn.commit()

    operator_email = _get_user_email(user_id)
    _fire_delete_user(server.agent_key, character_name, operator_email)
    return {"ok": True}


# ── 服主/管理员删除成员的游戏角色 ────────────────────────────────────────

@router.delete("/{server_id}/members/{target_user_id}/characters/{character_name}",
               summary="服主/管理员删除成员的游戏角色")
async def delete_member_character(
    server_id: int,
    target_user_id: int,
    character_name: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    if not _caller_can_manage(server_id, user_id, db, "panel.users"):
        raise HTTPException(403, "无管理权限")
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")

    await delete_character_on_agent(server.agent_key, character_name, target_user_id)

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM AgentCharacterBindingsCache WHERE user_id=? AND agent_key=? AND character_name=?",
            (target_user_id, server.agent_key, character_name),
        ).fetchone()
        if row:
            conn.execute("DELETE FROM AgentCharacterBindingsCache WHERE id=?", (row[0],))
            conn.commit()

    operator_email = _get_user_email(user_id)
    _fire_delete_user(server.agent_key, character_name, operator_email)
    return {"ok": True}


def _is_agent_connected(agent_key: str) -> bool:
    try:
        return bool(agent_key) and (agent_key in manager.active_agents)
    except Exception:
        return False


def _has_any_agent_connected() -> bool:
    try:
        return len(manager.active_agents) > 0
    except Exception:
        return False


def _fire_delete_user(agent_key: str, username: str, operator_email: str) -> bool:
    """fire-and-forget：发送 delete_user 到 Agent，让其删除 TShock 账号并留痕"""
    try:
        if not _has_any_agent_connected():
            return False

        msg = json.dumps({
            "type": "delete_user",
            "msg_id": new_id(),
            "timestamp": now_ms(),
            "payload": {
                "username": username,
                "operator_email": operator_email,
            },
        })

        # 该函数在同步路由中也会被调用：优先挂到当前事件循环；若无，则回投到 WS 主循环。
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            coro = manager.send_agent(agent_key, msg)
            try:
                loop.create_task(coro)
                return True
            except Exception:
                try:
                    coro.close()
                except Exception:
                    pass

        bg_loop = getattr(manager, "loop", None)
        if bg_loop and bg_loop.is_running():
            coro = manager.send_agent(agent_key, msg)
            try:
                asyncio.run_coroutine_threadsafe(coro, bg_loop)
                return True
            except Exception:
                try:
                    coro.close()
                except Exception:
                    pass

        return False
    except Exception:
        return False


def _extract_color_tag_name(raw: str) -> str:
    text = (raw or "").strip()
    if not text.lower().startswith("[c/"):
        return text
    colon_idx = text.find(":")
    end_idx = text.rfind("]")
    if colon_idx > 0 and end_idx > colon_idx:
        inner = text[colon_idx + 1:end_idx].strip()
        if inner:
            return inner
    return text


def _trim_tail_punctuation(raw: str) -> str:
    text = (raw or "").strip()
    tail = {".", "。", ",", "，", "!", "！", "?", "？", ";", "；", ":", "："}
    while text and text[-1] in tail:
        text = text[:-1].rstrip()
    return text


def _canonicalize_character_name(raw: str) -> str:
    return _trim_tail_punctuation(_extract_color_tag_name(raw or "")).strip()


def _resolve_character_binding(conn: sqlite3.Connection, agent_key: str, raw_name: str):
    # 1) 先按原名匹配（忽略大小写）
    trimmed = (raw_name or "").strip()
    if not trimmed:
        return None

    row = conn.execute(
        "SELECT id, character_name FROM AgentCharacterBindingsCache WHERE agent_key=? AND character_name=? COLLATE NOCASE",
        (agent_key, trimmed),
    ).fetchone()
    if row:
        return row

    # 2) 再按规范化后的名称匹配（处理彩字名、尾标点）
    canonical = _canonicalize_character_name(trimmed)
    if canonical and canonical.lower() != trimmed.lower():
        row = conn.execute(
            "SELECT id, character_name FROM AgentCharacterBindingsCache WHERE agent_key=? AND character_name=? COLLATE NOCASE",
            (agent_key, canonical),
        ).fetchone()
        if row:
            return row

    # 3) 最后做一次模糊规范化比较，避免历史脏数据导致漏删
    rows = conn.execute(
        "SELECT id, character_name FROM AgentCharacterBindingsCache WHERE agent_key=?",
        (agent_key,),
    ).fetchall()
    matched = [
        r for r in rows
        if _canonicalize_character_name(r[1]).lower() == canonical.lower()
    ]
    if len(matched) == 1:
        return matched[0]
    if len(matched) > 1:
        names = ", ".join([m[1] for m in matched[:5]])
        raise HTTPException(409, f"匹配到多个相似角色名，请使用更精确名称重试：{names}")
    return None


async def _delete_game_account_impl(
    server_id: int,
    character_name: str,
    db: Session,
    user_id: int,
):
    if not _caller_can_manage(server_id, user_id, db, "panel.users"):
        raise HTTPException(403, "无管理权限")

    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")

    incoming_name = (character_name or "").strip()
    if not incoming_name:
        raise HTTPException(400, "character_name 不能为空")

    removed_binding = False
    resolved_name = incoming_name
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = _resolve_character_binding(conn, server.agent_key, incoming_name)
        if row:
            bind_id, stored_name = row
            removed_binding = True
            resolved_name = stored_name or incoming_name

    operator_email = _get_user_email(user_id)
    dispatch_name = _canonicalize_character_name(resolved_name) or resolved_name
    if removed_binding:
        await delete_character_on_agent(server.agent_key, dispatch_name)
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            conn.execute(
                "DELETE FROM AgentCharacterBindingsCache WHERE agent_key=? AND character_name=? COLLATE NOCASE",
                (server.agent_key, dispatch_name),
            )
            conn.commit()
    agent_key_matched = _is_agent_connected(server.agent_key)
    agent_connected = _has_any_agent_connected()
    agent_dispatched = _fire_delete_user(server.agent_key, dispatch_name, operator_email)

    warning = None
    if not agent_connected:
        warning = "Agent 未在线，仅删除绑定记录；游戏账号删除将在 Agent 在线后可重试"
    elif not agent_key_matched:
        warning = "未找到匹配的 Agent Key，已向在线 Agent 广播删除请求"
    elif not agent_dispatched:
        warning = "已处理绑定记录，但通知 Agent 删除游戏账号失败，请稍后重试"

    return {
        "ok": True,
        "removed_binding": removed_binding,
        "character_name": dispatch_name,
        "agent_connected": agent_connected,
        "agent_dispatched": agent_dispatched,
        "agent_warning": warning,
    }


# ── 绑定已有游戏角色（验证码校验）────────────────────────────────────────

@router.post("/{server_id}/bind-verify", summary="验证绑定验证码并完成角色绑定")
async def bind_verify(
    server_id: int,
    req: BindVerifyReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    from app.api.websocket import _bind_codes, BIND_CODE_EXPIRE  # 避免循环导入

    member = db.query(ServerMember).filter_by(server_id=server_id, user_id=user_id).first()
    if not member:
        raise HTTPException(403, "您不是该服务器成员")
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")

    _validate_character_name_policy(server, req.username)
    key = (server.agent_key, req.username.lower())
    entry = _bind_codes.get(key)
    if not entry:
        raise HTTPException(400, "验证码不存在或已过期，请重新发送")
    if time.time() > entry["expires_at"]:
        _bind_codes.pop(key, None)
        raise HTTPException(400, "验证码已过期，请重新发送")

    cur_email = _get_user_email(user_id)
    if entry["email"].lower() != (cur_email or "").lower():
        raise HTTPException(403, "验证码不属于当前登录账号")

    if entry["code"] != req.code.strip():
        raise HTTPException(400, "验证码错误")

    # 一次性消费
    _bind_codes.pop(key, None)

    real_username = req.username
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        existing = conn.execute(
            "SELECT id FROM AgentCharacterBindingsCache WHERE agent_key=? AND character_name=? COLLATE NOCASE",
            (server.agent_key, real_username),
        ).fetchone()
        if existing:
            raise HTTPException(400, "该游戏账号已被绑定，无法重复绑定")

        _assert_user_register_quota_available(conn, server, user_id)

    cur_email = _get_user_email(user_id) or ""
    agent_row = await bind_character_on_agent(
        server.agent_key,
        user_id,
        cur_email,
        real_username,
        "bind_verify",
    )

    registered_at = int(agent_row.get("registered_at") or time.time())
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO AgentCharacterBindingsCache (user_id, agent_key, character_name, registered_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, server.agent_key, real_username, registered_at),
        )
        conn.commit()

    return {"ok": True, "msg": "绑定成功"}


# ── 获取服务器所有角色绑定映射（管理员用于在线玩家查询）──────────────────

@router.get("/{server_id}/character-map", summary="获取服务器所有角色→面板账号映射")
def get_character_map(
    server_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    if not _caller_can_manage(server_id, user_id, db, "panel.users"):
        raise HTTPException(403, "无管理权限")
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT gc.character_name, u.email
            FROM AgentCharacterBindingsCache gc
            JOIN users u ON u.id = gc.user_id
            WHERE gc.agent_key = ?
            """,
            (server.agent_key,),
        ).fetchall()

    return {r[0]: r[1] for r in rows}


@router.post("/{server_id}/characters/assign", summary="手动分配/修改游戏账号归属（Owner/管理员）")
async def assign_character_owner(
    server_id: int,
    req: AssignCharacterOwnerReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    if not _caller_can_manage(server_id, user_id, db, "panel.users"):
        raise HTTPException(403, "无管理权限")

    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")

    target_user_id = int(req.target_user_id) if req.target_user_id is not None else None
    if target_user_id is not None:
        target_member = db.query(ServerMember).filter_by(server_id=server_id, user_id=target_user_id).first()
        if not target_member:
            raise HTTPException(404, "目标成员不在该服务器中")

    character_name = "" if req.character_name is None else str(req.character_name)
    if not character_name:
        raise HTTPException(400, "character_name 不能为空")
    if target_user_id is not None:
        _validate_character_name_policy(server, character_name)

    target_email = _get_user_email(target_user_id) if target_user_id else ""
    agent_resp = await assign_character_on_agent(
        server.agent_key,
        character_name,
        target_user_id,
        target_email or "",
    )

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        exists = conn.execute(
            "SELECT id, user_id, character_name FROM AgentCharacterBindingsCache WHERE agent_key=? AND character_name=? COLLATE NOCASE",
            (server.agent_key, character_name),
        ).fetchone()

        prev_user_id = None
        if target_user_id is None:
            # 允许设置为“无”：删除现有绑定
            if exists:
                bind_id, prev_user_id, canonical_name = exists
                conn.execute("DELETE FROM AgentCharacterBindingsCache WHERE id=?", (bind_id,))
                bound_name = canonical_name or character_name
                action = "cleared"
            else:
                bound_name = character_name
                action = "unchanged"
        else:
            if exists:
                bind_id, prev_user_id, canonical_name = exists
                action = "unchanged"
                if int(prev_user_id) != target_user_id:
                    conn.execute(
                        "UPDATE AgentCharacterBindingsCache SET user_id=? WHERE id=?",
                        (target_user_id, bind_id),
                    )
                    action = "reassigned"
                bound_name = canonical_name or character_name
            else:
                conn.execute(
                    "INSERT INTO AgentCharacterBindingsCache (user_id, agent_key, character_name, registered_at) "
                    "VALUES (?, ?, ?, ?)",
                    (target_user_id, server.agent_key, character_name, int(time.time())),
                )
                bound_name = character_name
                action = "created"
        conn.commit()

    previous_email = _get_user_email(prev_user_id) if prev_user_id else None
    return {
        "ok": True,
        "action": agent_resp.get("action") or action,
        "character_name": bound_name,
        "target_user_id": target_user_id,
        "target_email": target_email,
        "previous_user_id": prev_user_id,
        "previous_email": previous_email,
    }


@router.delete("/{server_id}/characters", summary="删除游戏账号（绑定+TShock 账号）")
async def delete_game_account(
    server_id: int,
    character_name: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    if not isinstance(character_name, str) or not character_name.strip():
        raise HTTPException(400, "character_name 不能为空")
    return await _delete_game_account_impl(server_id, character_name.strip(), db, user_id)


# ── 面板功能管理 ───────────────────────────────────────────────────────────

@router.get("/{server_id}/panel-features", response_model=PanelFeatureSettingsOut,
            summary="获取面板功能配置")
def get_panel_features(
    server_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_panel_features_manage(server_id, user_id, db)

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        current = _count_registered_characters(conn, server.agent_key, user_id=user_id)

    return PanelFeatureSettingsOut(
        register_limit=_normalize_register_limit(getattr(server, "register_limit", 1)),
        registered_count=current,
        join_requires_approval=bool(getattr(server, "join_requires_approval", False)),
        blacklist_auto_reject_count=_normalize_blacklist_auto_reject_count(getattr(server, "blacklist_auto_reject_count", 0)),
        character_name_regex=_normalize_character_name_regex(getattr(server, "character_name_regex", DEFAULT_CHARACTER_NAME_REGEX)),
        character_name_max_length=_normalize_character_name_max_length(getattr(server, "character_name_max_length", DEFAULT_CHARACTER_NAME_MAX_LENGTH)),
        server_code=(server.server_code or ""),
    )


@router.put("/{server_id}/panel-features", response_model=PanelFeatureSettingsOut,
            summary="更新面板功能配置")
def update_panel_features(
    server_id: int,
    req: PanelFeatureSettingsUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_panel_features_manage(server_id, user_id, db)

    server.register_limit = _normalize_register_limit(req.register_limit)
    server.blacklist_auto_reject_count = _normalize_blacklist_auto_reject_count(req.blacklist_auto_reject_count)
    server.character_name_regex = _normalize_character_name_regex(req.character_name_regex)
    server.character_name_max_length = _normalize_character_name_max_length(req.character_name_max_length)
    try:
        db.commit()
        db.refresh(server)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        current = _count_registered_characters(conn, server.agent_key, user_id=user_id)

    return PanelFeatureSettingsOut(
        register_limit=_normalize_register_limit(getattr(server, "register_limit", 1)),
        registered_count=current,
        join_requires_approval=bool(getattr(server, "join_requires_approval", False)),
        blacklist_auto_reject_count=_normalize_blacklist_auto_reject_count(getattr(server, "blacklist_auto_reject_count", 0)),
        character_name_regex=_normalize_character_name_regex(getattr(server, "character_name_regex", DEFAULT_CHARACTER_NAME_REGEX)),
        character_name_max_length=_normalize_character_name_max_length(getattr(server, "character_name_max_length", DEFAULT_CHARACTER_NAME_MAX_LENGTH)),
        server_code=(server.server_code or ""),
    )


@router.put("/{server_id}/panel-features/join-approval", response_model=PanelFeatureSettingsOut,
            summary="更新入服审核开关（面板功能）")
def update_panel_join_approval(
    server_id: int,
    req: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = _require_panel_features_manage(server_id, user_id, db)
    if server.owner_id != user_id:
        raise HTTPException(403, "仅服主可修改入服审核开关")

    value = bool(req.get("join_requires_approval", False))
    server.join_requires_approval = value
    try:
        db.commit()
        db.refresh(server)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        current = _count_registered_characters(conn, server.agent_key, user_id=user_id)

    return PanelFeatureSettingsOut(
        register_limit=_normalize_register_limit(getattr(server, "register_limit", 1)),
        registered_count=current,
        join_requires_approval=bool(getattr(server, "join_requires_approval", False)),
        blacklist_auto_reject_count=_normalize_blacklist_auto_reject_count(getattr(server, "blacklist_auto_reject_count", 0)),
        character_name_regex=_normalize_character_name_regex(getattr(server, "character_name_regex", DEFAULT_CHARACTER_NAME_REGEX)),
        character_name_max_length=_normalize_character_name_max_length(getattr(server, "character_name_max_length", DEFAULT_CHARACTER_NAME_MAX_LENGTH)),
        server_code=(server.server_code or ""),
    )


@router.get("/{server_id}/panel-features/join-requests", response_model=List[JoinRequestOut],
            summary="面板功能：列出待审批申请")
def list_panel_join_requests(
    server_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    _require_panel_features_manage(server_id, user_id, db)
    valid_status = {"pending", "approved", "rejected", "withdrawn"}
    if status and status not in valid_status:
        raise HTTPException(400, "状态无效")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT
                r.id, r.server_id, r.applicant_user_id, au.email AS applicant_email,
                r.message, r.status, r.reviewed_by_user_id,
                ru.email AS reviewed_by_email,
                r.review_note, r.created_at, r.updated_at, r.withdrawn_at
            FROM (
                SELECT *, from_user_id AS applicant_user_id
                FROM ServerMemberRequests
                WHERE request_type='join'
            ) r
            JOIN users au ON au.id = r.applicant_user_id
            LEFT JOIN users ru ON ru.id = r.reviewed_by_user_id
            WHERE r.server_id=?
        """
        params = [server_id]
        if status:
            sql += " AND r.status=?"
            params.append(status)
        sql += " ORDER BY r.created_at DESC, r.id DESC"
        rows = conn.execute(sql, tuple(params)).fetchall()

    return _join_request_rows_with_blacklist(rows, server_id)


@router.post("/{server_id}/panel-features/join-requests/{request_id}/approve", summary="面板功能：批准申请")
def approve_panel_join_request(
    server_id: int,
    request_id: int,
    req: PanelMembershipReviewReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    _require_panel_features_manage(server_id, user_id, db)
    return approve_join_request(server_id, request_id, JoinRequestReviewReq(note=req.note), db, user_id)


@router.post("/{server_id}/panel-features/join-requests/{request_id}/reject", summary="面板功能：拒绝申请")
def reject_panel_join_request(
    server_id: int,
    request_id: int,
    req: PanelMembershipReviewReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    _require_panel_features_manage(server_id, user_id, db)
    return reject_join_request(server_id, request_id, JoinRequestReviewReq(note=req.note), db, user_id)


@router.post("/{server_id}/panel-features/invites", summary="面板功能：发送邀请")
def create_panel_invite(
    server_id: int,
    req: PanelMembershipInviteReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    _require_panel_features_manage(server_id, user_id, db)
    return create_server_invite(
        server_id,
        ServerInviteCreateReq(
            invitee_email=req.invitee_email,
            message=req.message,
            expires_in_hours=req.expires_in_hours,
        ),
        db,
        user_id,
    )


# ── 面板权限组管理 ────────────────────────────────────────────────────────────

@router.get("/{server_id}/panel-groups", summary="列出服务器的面板权限组（所有成员可见）")
def list_panel_groups(
    server_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    member = db.query(ServerMember).filter_by(server_id=server_id, user_id=user_id).first()
    if not member:
        raise HTTPException(403, "无访问权限")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        groups = conn.execute(
            """
            SELECT g.id, g.name, g.description, g.parent_group_id, p.name, g.is_builtin, g.permissions
            FROM ServerAccessGroups g
            LEFT JOIN ServerAccessGroups p ON p.id = g.parent_group_id
            WHERE g.server_id=?
            ORDER BY g.id
            """,
            (server_id,),
        ).fetchall()
        # 检测三个必备默认中文组是否齐全，缺少或有旧英文组则自动修复
        existing_names = {g[1] for g in groups}
        needs_init = not {'服主', '管理', '成员'}.issubset(existing_names) \
                     or any(n in existing_names for n in ('owner', 'admin', 'default'))
        if needs_init:
            _init_server_access_groups(server_id, conn=conn)
            groups = conn.execute(
                """
                SELECT g.id, g.name, g.description, g.parent_group_id, p.name, g.is_builtin, g.permissions
                FROM ServerAccessGroups g
                LEFT JOIN ServerAccessGroups p ON p.id = g.parent_group_id
                WHERE g.server_id=?
                ORDER BY g.id
                """,
                (server_id,),
            ).fetchall()
        result = []
        for gid, name, desc, parent_group_id, parent_group_name, is_builtin, perms_raw in groups:
            try:
                direct_perms = json.loads(perms_raw or "[]")
                if not isinstance(direct_perms, list):
                    direct_perms = []
            except Exception:
                direct_perms = []
            effective_perms = _collect_panel_group_permissions(conn, server_id, gid)
            member_count = conn.execute(
                "SELECT COUNT(*) FROM ServerMembers WHERE access_group_id=?",
                (gid,),
            ).fetchone()[0]
            result.append({
                "id": gid,
                "server_id": server_id,
                "name": name,
                "description": desc,
                "parent_group_id": parent_group_id,
                "parent_group_name": parent_group_name,
                "is_builtin": bool(is_builtin),
                "permissions": [str(p) for p in direct_perms if p],
                "effective_permissions": effective_perms,
                "member_count": member_count,
            })
    return {"ok": True, "data": result}


@router.post("/{server_id}/panel-groups", summary="创建面板权限组（Owner 专属）")
def create_panel_group(
    server_id: int,
    req: PanelGroupCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    if server.owner_id != user_id:
        raise HTTPException(403, "仅 Owner 可创建权限组")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        try:
            if req.parent_group_id is not None:
                parent = conn.execute(
                    "SELECT id FROM ServerAccessGroups WHERE id=? AND server_id=?",
                    (req.parent_group_id, server_id),
                ).fetchone()
                if not parent:
                    raise HTTPException(400, "父组不存在")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ServerAccessGroups(server_id, name, description, parent_group_id, is_builtin, permissions) VALUES(?,?,?,?,0,?)",
                (server_id, req.name.strip(), req.description, req.parent_group_id, json.dumps(req.permissions, ensure_ascii=False)),
            )
            gid = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(400, "权限组名已存在")
    return {"ok": True, "id": gid}


@router.put("/{server_id}/panel-groups/{group_id}", summary="更新面板权限组（Owner 专属）")
def update_panel_group(
    server_id: int,
    group_id: int,
    req: PanelGroupUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    if server.owner_id != user_id:
        raise HTTPException(403, "仅 Owner 可修改权限组")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, is_builtin FROM ServerAccessGroups WHERE id=? AND server_id=?",
            (group_id, server_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "权限组不存在")
        is_builtin = row[1]

        if req.name is not None:
            if is_builtin:
                raise HTTPException(400, "内置权限组不可修改名称")
            try:
                conn.execute(
                    "UPDATE ServerAccessGroups SET name=? WHERE id=?",
                    (req.name.strip(), group_id),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(400, "权限组名已存在")

        if req.description is not None:
            conn.execute(
                "UPDATE ServerAccessGroups SET description=? WHERE id=?",
                (req.description, group_id),
            )

        parent_specified = 'parent_group_id' in getattr(req, 'model_fields_set', set())
        if parent_specified:
            if req.parent_group_id is None:
                conn.execute(
                    "UPDATE ServerAccessGroups SET parent_group_id=NULL WHERE id=?",
                    (group_id,),
                )
            else:
                if req.parent_group_id == group_id:
                    raise HTTPException(400, "父组不能是自己")
                parent = conn.execute(
                    "SELECT id FROM ServerAccessGroups WHERE id=? AND server_id=?",
                    (req.parent_group_id, server_id),
                ).fetchone()
                if not parent:
                    raise HTTPException(400, "父组不存在")
                if _has_parent_cycle(conn, server_id, group_id, req.parent_group_id):
                    raise HTTPException(400, "父组继承形成循环，请重新选择")
                conn.execute(
                    "UPDATE ServerAccessGroups SET parent_group_id=? WHERE id=?",
                    (req.parent_group_id, group_id),
                )

        if req.permissions is not None:
            conn.execute(
                "UPDATE ServerAccessGroups SET permissions=? WHERE id=?",
                (json.dumps([p.strip() for p in req.permissions if p.strip()], ensure_ascii=False), group_id),
            )

        conn.commit()
    return {"ok": True}


@router.delete("/{server_id}/panel-groups/{group_id}", summary="删除面板权限组（Owner 专属）")
def delete_panel_group(
    server_id: int,
    group_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    server = db.query(Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "服务器不存在")
    if server.owner_id != user_id:
        raise HTTPException(403, "仅 Owner 可删除权限组")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT is_builtin FROM ServerAccessGroups WHERE id=? AND server_id=?",
            (group_id, server_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "权限组不存在")
        if row[0]:
            raise HTTPException(400, "内置权限组不可删除")

        conn.execute("UPDATE ServerMembers SET access_group_id=NULL WHERE access_group_id=?", (group_id,))
        conn.execute("DELETE FROM ServerAccessGroups WHERE id=?", (group_id,))
        conn.commit()
    return {"ok": True}


@router.put("/{server_id}/members/{target_user_id}/panel-group",
            summary="分配成员到面板权限组（Owner 或具备 panel.groups 权限）")
def assign_member_panel_group(
    server_id: int,
    target_user_id: int,
    req: PanelMemberGroupUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    if not _caller_can_manage(server_id, user_id, db, "panel.groups"):
        raise HTTPException(403, "无权限，需要服务器 Owner 或 panel.groups 权限")

    target = db.query(ServerMember).filter_by(server_id=server_id, user_id=target_user_id).first()
    if not target:
        raise HTTPException(404, "目标成员不在该服务器中")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        group = conn.execute(
            "SELECT id FROM ServerAccessGroups WHERE id=? AND server_id=?",
            (req.group_id, server_id),
        ).fetchone()
        if not group:
            raise HTTPException(404, "权限组不存在或不属于该服务器")

        # 查出组名，用来同步底层 role
        group_name = conn.execute(
            "SELECT name FROM ServerAccessGroups WHERE id=?", (req.group_id,)
        ).fetchone()[0]

        target.access_group_id = req.group_id

    # 同步底层 role：服主组 → owner；管理组 → web_staff；其余 → member
    role_map = {"服主": ServerMemberRole.owner, "管理": ServerMemberRole.web_staff}
    new_role = role_map.get(group_name, ServerMemberRole.member)
    # 不能降级服务器所有者
    srv = db.query(Server).filter_by(id=server_id).first()
    if target_user_id != srv.owner_id:
        target.role = new_role
    db.commit()

    return {"ok": True}


@router.get("/{server_id}/members/{target_user_id}/panel-group",
            summary="获取成员当前所属面板权限组")
def get_member_panel_group(
    server_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    # 自己查自己，或者有管理权限的用户查他人
    if user_id != target_user_id:
        if not _caller_can_manage(server_id, user_id, db, "panel.users"):
            raise HTTPException(403, "无权限")

    target = db.query(ServerMember).filter_by(server_id=server_id, user_id=target_user_id).first()
    if not target:
        raise HTTPException(404, "目标用户不在该服务器中")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT spg.id, spg.name, spg.description, spg.is_builtin
            FROM ServerMembers sm
            JOIN ServerAccessGroups spg ON spg.id = sm.access_group_id
            WHERE sm.server_id=? AND sm.user_id=?
            """,
            (server_id, target_user_id),
        ).fetchone()

    if not row:
        return {"ok": True, "data": None}
    return {"ok": True, "data": {
        "id": row[0], "name": row[1], "description": row[2], "is_builtin": bool(row[3]),
    }}
