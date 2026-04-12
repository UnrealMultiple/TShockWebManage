import asyncio
import json
import sqlite3
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import AUTH_DB_PATH
from app.core.database import get_db
from app.core.utils import verify_token, new_id, now_ms
from app.models.db_models import Server, ServerMember, ServerMemberRole
from app.models.schemas import (
    ServerClaimReq, ServerJoinReq, ServerUpdateReq,
    ServerOut, ServerDetailOut, ServerMemberOut,
    UpdateMemberRoleReq, BindVerifyReq,
    PanelGroupCreate, PanelGroupUpdate, PanelGroupOut, PanelMemberGroupUpdate,
)
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/servers", tags=["Servers"])


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
            "panel.console", "panel.users", "panel.files",
            "panel.database", "panel.dashboard", "panel.characters",
            "panel.inventory.view.self", "panel.inventory.view.others",
        ],
    },
    {
        "name": "成员",
        "description": "普通成员，仪表盘及我的角色",
        "is_builtin": 1,
        "permissions": [
            "panel.dashboard", "panel.characters",
            "panel.inventory.view.self", "panel.inventory.view.others",
        ],
    },
]

# 旧英文组名 → 新中文组名的迁移映射
_LEGACY_GROUP_RENAME = {"owner": "服主", "admin": "管理", "default": "成员"}


def _init_server_panel_groups(server_id: int):
    """为设备组（或旧服务器迁移）初始化/修复默认面板权限组（幂等）"""
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        # ① 将旧英文组名重命名为中文（保留成员分配关系）
        for old_name, new_name in _LEGACY_GROUP_RENAME.items():
            old_row = conn.execute(
                "SELECT id FROM server_panel_groups WHERE server_id=? AND name=?",
                (server_id, old_name),
            ).fetchone()
            new_row = conn.execute(
                "SELECT id FROM server_panel_groups WHERE server_id=? AND name=?",
                (server_id, new_name),
            ).fetchone()
            if old_row and not new_row:
                # 直接重命名旧组
                conn.execute(
                    "UPDATE server_panel_groups SET name=? WHERE id=?",
                    (new_name, old_row[0]),
                )
            elif old_row and new_row:
                # 两者共存：将旧组成员迁移到新组，再删除旧组
                conn.execute(
                    "UPDATE OR IGNORE server_member_panel_groups SET group_id=? WHERE group_id=?",
                    (new_row[0], old_row[0]),
                )
                conn.execute("DELETE FROM server_panel_groups WHERE id=?", (old_row[0],))
        # ② 补充缺少的默认中文组
        for g in _DEFAULT_PANEL_GROUPS:
            conn.execute(
                "INSERT OR IGNORE INTO server_panel_groups(server_id, name, description, is_builtin) "
                "VALUES(?,?,?,?)",
                (server_id, g["name"], g["description"], g["is_builtin"]),
            )
            row = conn.execute(
                "SELECT id FROM server_panel_groups WHERE server_id=? AND name=?",
                (server_id, g["name"]),
            ).fetchone()
            gid = row[0]
            for perm in g["permissions"]:
                conn.execute(
                    "INSERT OR IGNORE INTO server_panel_group_perms(group_id, permission) VALUES(?,?)",
                    (gid, perm),
                )
        conn.commit()


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
    if not row:
        raise HTTPException(401, "用户不存在")
    return row[0]


def _get_user_email(user_id: int) -> str:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
    return row[0] if row else ""


def _has_panel_perm(server_id: int, user_id: int, permission: str) -> bool:
    """检查用户在指定服务器是否拥有给定面板权限（支持 * 及前缀通配 tshock.*）"""
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        pg_row = conn.execute(
            "SELECT spg.id FROM server_member_panel_groups smpg "
            "JOIN server_panel_groups spg ON spg.id = smpg.group_id "
            "WHERE smpg.server_id=? AND smpg.user_id=?",
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
        rows = conn.execute(
            "SELECT permission FROM server_panel_group_perms WHERE group_id=?",
            (current_id,),
        ).fetchall()
        for (perm,) in rows:
            perms.add(perm)
        parent_row = conn.execute(
            "SELECT parent_group_id FROM server_panel_groups WHERE id=? AND server_id=?",
            (current_id, server_id),
        ).fetchone()
        current_id = parent_row[0] if parent_row else None

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
            "SELECT parent_group_id FROM server_panel_groups WHERE id=? AND server_id=?",
            (current_id, server_id),
        ).fetchone()
        if not row:
            break
        current_id = row[0]
    return False


def _caller_can_manage(server_id: int, user_id: int, db: Session, perm: str = "panel.users") -> bool:
    """检查 caller 是否有管理权限（owner_id 或角色 owner 直通，其他成员需面板权限）"""
    member = db.query(ServerMember).filter_by(server_id=server_id, user_id=user_id).first()
    if not member:
        return False
    server = db.query(Server).filter_by(id=server_id).first()
    if (server and server.owner_id == user_id) or member.role.value == "owner":
        return True
    return _has_panel_perm(server_id, user_id, perm)


def _server_to_out(s: Server, db: Session, user_id: Optional[int] = None) -> ServerOut:
    server_role = None
    panel_group_name = None
    panel_permissions = None
    if user_id is not None:
        membership = db.query(ServerMember).filter_by(server_id=s.id, user_id=user_id).first()
        if membership:
            server_role = membership.role.value
        with sqlite3.connect(AUTH_DB_PATH) as _conn:
            pg_row = _conn.execute(
                "SELECT spg.id, spg.name FROM server_member_panel_groups smpg "
                "JOIN server_panel_groups spg ON spg.id = smpg.group_id "
                "WHERE smpg.server_id=? AND smpg.user_id=?",
                (s.id, user_id),
            ).fetchone()
            if pg_row:
                panel_group_name = pg_row[1]
                panel_permissions = _collect_panel_group_permissions(_conn, s.id, pg_row[0])

    return ServerOut(
        id=s.id,
        name=s.name,
        description=s.description or "",
        agent_key=s.agent_key,
        owner_id=s.owner_id,
        created_at=s.created_at,
        is_public=bool(s.is_public),
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
        local_start_enabled=bool(s.local_start_enabled) if s.local_start_enabled is not None else False,
        local_start_path=s.local_start_path or "",
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

        # 认领前必须验证 Agent 当前在线，避免无效 key 被误认领
        if agent_key not in manager.active_agents:
            raise HTTPException(400, "该 Agent 当前未连接，无法认领，请先启动并连接 Agent")

        server = db.query(Server).filter_by(agent_key=agent_key).first()

        if server is None:
            server = Server(
                name=req.name,
                description=req.description,
                agent_key=agent_key,
                owner_id=user_id,
                is_public=req.is_public,
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
            server.name = req.name
            server.description = req.description
            server.is_public = req.is_public
            server.game_ip = req.game_ip or ""
            server.game_port = req.game_port
            server.qq_group = req.qq_group or ""
            server.game_version = req.game_version or ""
            server.show_ip = req.show_ip

        existing = db.query(ServerMember).filter_by(
            server_id=server.id, user_id=user_id
        ).first()
        if not existing:
            db.add(ServerMember(
                server_id=server.id,
                user_id=user_id,
                role=ServerMemberRole.owner,
                joined_at=int(time.time()),
            ))

        db.commit()
        db.refresh(server)
        # 为服务器初始化默认面板权限组
        _init_server_panel_groups(server.id)
        return _server_to_out(server, db, user_id=user_id)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


# ── 加入服务器 ───────────────────────────────────────────────────

@router.post("/join", response_model=ServerOut, summary="加入已认领的服务器成为 Member")
def join_server(
    req: ServerJoinReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    try:
        server = db.query(Server).filter_by(id=req.server_id).first()
        if not server:
            raise HTTPException(404, "服务器不存在")
        if server.owner_id is None:
            raise HTTPException(400, "该服务器尚未被认领，无法加入")

        existing = db.query(ServerMember).filter_by(
            server_id=server.id, user_id=user_id
        ).first()
        if existing:
            raise HTTPException(409, "您已在该服务器中")

        db.add(ServerMember(
            server_id=server.id,
            user_id=user_id,
            role=ServerMemberRole.member,
            joined_at=int(time.time()),
        ))
        db.commit()
        db.refresh(server)
        return _server_to_out(server, db, user_id=user_id)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


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
        servers_q = db.query(Server).filter_by(is_public=True).all()
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
                pg_row = _conn.execute(
                    "SELECT spg.id, spg.name FROM server_member_panel_groups smpg "
                    "JOIN server_panel_groups spg ON spg.id = smpg.group_id "
                    "WHERE smpg.server_id=? AND smpg.user_id=?",
                    (server_id, m.user_id),
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
def leave_server(
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
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


# ── 踢出成员（Owner 专属）────────────────────────────────────────

@router.delete("/{server_id}/members/{target_user_id}", summary="踢出成员（Owner 专属）")
def kick_member(
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
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")


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
        server.is_public = req.is_public
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
    if req.local_start_enabled is not None:
        server.local_start_enabled = req.local_start_enabled
    if req.local_start_path is not None:
        # 校验路径扩展名，只允许 .bat / .sh
        path = req.local_start_path.strip()
        if path and not (path.endswith(".bat") or path.endswith(".sh")):
            raise HTTPException(400, "local_start_path 只允许 .bat 或 .sh 脚本")
        server.local_start_path = path
    try:
        db.commit()
        db.refresh(server)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"数据库错误: {e}")
    member_count = db.query(ServerMember).filter_by(server_id=server_id).count()
    return ServerOut(
        id=server.id, name=server.name, description=server.description or "",
        agent_key=server.agent_key, owner_id=server.owner_id,
        created_at=server.created_at, is_public=bool(server.is_public),
        online=server.agent_key in manager.active_agents,
        member_count=member_count,
        game_ip=server.game_ip or "",
        game_port=server.game_port,
        qq_group=server.qq_group or "",
        game_version=server.game_version or "",
        show_ip=bool(server.show_ip) if server.show_ip is not None else True,
        local_start_enabled=bool(server.local_start_enabled) if server.local_start_enabled is not None else False,
        local_start_path=server.local_start_path or "",
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
            "SELECT character_name, registered_at FROM game_characters "
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
            "SELECT character_name, registered_at FROM game_characters "
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

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM game_characters WHERE user_id=? AND agent_key=? AND character_name=?",
            (user_id, server.agent_key, character_name),
        ).fetchone()
        if not row:
            raise HTTPException(404, "角色不存在或不属于您")
        conn.execute("DELETE FROM game_characters WHERE id=?", (row[0],))
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

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM game_characters WHERE user_id=? AND agent_key=? AND character_name=?",
            (target_user_id, server.agent_key, character_name),
        ).fetchone()
        if not row:
            raise HTTPException(404, "角色不存在")
        conn.execute("DELETE FROM game_characters WHERE id=?", (row[0],))
        conn.commit()

    operator_email = _get_user_email(user_id)
    _fire_delete_user(server.agent_key, character_name, operator_email)
    return {"ok": True}


def _fire_delete_user(agent_key: str, username: str, operator_email: str):
    """fire-and-forget：发送 delete_user 到 Agent，让其删除 TShock 账号并留痕"""
    try:
        msg = json.dumps({
            "type": "delete_user",
            "msg_id": new_id(),
            "timestamp": now_ms(),
            "payload": {
                "username": username,
                "operator_email": operator_email,
            },
        })
        asyncio.create_task(manager.send_agent(agent_key, msg))
    except Exception:
        pass


# ── 绑定已有游戏角色（验证码校验）────────────────────────────────────────

@router.post("/{server_id}/bind-verify", summary="验证绑定验证码并完成角色绑定")
def bind_verify(
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

    key = (server.agent_key, req.username.strip().lower())
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

    real_username = req.username.strip()
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        existing = conn.execute(
            "SELECT id FROM game_characters WHERE agent_key=? AND character_name=? COLLATE NOCASE",
            (server.agent_key, real_username),
        ).fetchone()
        if existing:
            raise HTTPException(400, "该游戏账号已被绑定，无法重复绑定")

        conn.execute(
            "INSERT INTO game_characters (user_id, agent_key, character_name, registered_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, server.agent_key, real_username, int(time.time())),
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
            FROM game_characters gc
            JOIN users u ON u.id = gc.user_id
            WHERE gc.agent_key = ?
            """,
            (server.agent_key,),
        ).fetchall()

    return {r[0]: r[1] for r in rows}


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
            SELECT g.id, g.name, g.description, g.parent_group_id, p.name, g.is_builtin
            FROM server_panel_groups g
            LEFT JOIN server_panel_groups p ON p.id = g.parent_group_id
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
            _init_server_panel_groups(server_id)
            groups = conn.execute(
                """
                SELECT g.id, g.name, g.description, g.parent_group_id, p.name, g.is_builtin
                FROM server_panel_groups g
                LEFT JOIN server_panel_groups p ON p.id = g.parent_group_id
                WHERE g.server_id=?
                ORDER BY g.id
                """,
                (server_id,),
            ).fetchall()
        result = []
        for gid, name, desc, parent_group_id, parent_group_name, is_builtin in groups:
            direct_perms = conn.execute(
                "SELECT permission FROM server_panel_group_perms WHERE group_id=? ORDER BY permission",
                (gid,),
            ).fetchall()
            effective_perms = _collect_panel_group_permissions(conn, server_id, gid)
            member_count = conn.execute(
                "SELECT COUNT(*) FROM server_member_panel_groups WHERE group_id=?",
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
                "permissions": [p[0] for p in direct_perms],
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
                    "SELECT id FROM server_panel_groups WHERE id=? AND server_id=?",
                    (req.parent_group_id, server_id),
                ).fetchone()
                if not parent:
                    raise HTTPException(400, "父组不存在")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO server_panel_groups(server_id, name, description, parent_group_id, is_builtin) VALUES(?,?,?,?,0)",
                (server_id, req.name.strip(), req.description, req.parent_group_id),
            )
            gid = cursor.lastrowid
            for perm in req.permissions:
                cursor.execute(
                    "INSERT OR IGNORE INTO server_panel_group_perms(group_id, permission) VALUES(?,?)",
                    (gid, perm.strip()),
                )
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
            "SELECT id, is_builtin FROM server_panel_groups WHERE id=? AND server_id=?",
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
                    "UPDATE server_panel_groups SET name=? WHERE id=?",
                    (req.name.strip(), group_id),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(400, "权限组名已存在")

        if req.description is not None:
            conn.execute(
                "UPDATE server_panel_groups SET description=? WHERE id=?",
                (req.description, group_id),
            )

        parent_specified = 'parent_group_id' in getattr(req, 'model_fields_set', set())
        if parent_specified:
            if req.parent_group_id is None:
                conn.execute(
                    "UPDATE server_panel_groups SET parent_group_id=NULL WHERE id=?",
                    (group_id,),
                )
            else:
                if req.parent_group_id == group_id:
                    raise HTTPException(400, "父组不能是自己")
                parent = conn.execute(
                    "SELECT id FROM server_panel_groups WHERE id=? AND server_id=?",
                    (req.parent_group_id, server_id),
                ).fetchone()
                if not parent:
                    raise HTTPException(400, "父组不存在")
                if _has_parent_cycle(conn, server_id, group_id, req.parent_group_id):
                    raise HTTPException(400, "父组继承形成循环，请重新选择")
                conn.execute(
                    "UPDATE server_panel_groups SET parent_group_id=? WHERE id=?",
                    (req.parent_group_id, group_id),
                )

        if req.permissions is not None:
            conn.execute("DELETE FROM server_panel_group_perms WHERE group_id=?", (group_id,))
            for perm in req.permissions:
                conn.execute(
                    "INSERT OR IGNORE INTO server_panel_group_perms(group_id, permission) VALUES(?,?)",
                    (group_id, perm.strip()),
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
            "SELECT is_builtin FROM server_panel_groups WHERE id=? AND server_id=?",
            (group_id, server_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "权限组不存在")
        if row[0]:
            raise HTTPException(400, "内置权限组不可删除")

        conn.execute("DELETE FROM server_panel_groups WHERE id=?", (group_id,))
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
            "SELECT id FROM server_panel_groups WHERE id=? AND server_id=?",
            (req.group_id, server_id),
        ).fetchone()
        if not group:
            raise HTTPException(404, "权限组不存在或不属于该服务器")

        # 查出组名，用来同步底层 role
        group_name = conn.execute(
            "SELECT name FROM server_panel_groups WHERE id=?", (req.group_id,)
        ).fetchone()[0]

        conn.execute(
            "INSERT OR REPLACE INTO server_member_panel_groups(server_id, user_id, group_id) VALUES(?,?,?)",
            (server_id, target_user_id, req.group_id),
        )
        conn.commit()

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
            FROM server_member_panel_groups smpg
            JOIN server_panel_groups spg ON spg.id = smpg.group_id
            WHERE smpg.server_id=? AND smpg.user_id=?
            """,
            (server_id, target_user_id),
        ).fetchone()

    if not row:
        return {"ok": True, "data": None}
    return {"ok": True, "data": {
        "id": row[0], "name": row[1], "description": row[2], "is_builtin": bool(row[3]),
    }}
