import json
import os
import random
import secrets
import sqlite3
import subprocess
import sys
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.config import AUTH_DB_PATH
from app.core.utils import verify_token, new_id, now_ms
from app.services.ws_manager import manager

# 绑定验证码临时存储: {(agent_key, username_lower): {code, email, expires_at}}
_bind_codes: dict = {}
BIND_CODE_EXPIRE = 600  # 10 分钟

# 本地进程追踪: {agent_key: subprocess.Popen}
_local_processes: dict = {}

router = APIRouter()

WEB_CLIENT_EMAILS = {}


def _normalize_agent_key(v: str) -> str:
    return (v or "").strip()


def with_operator(payload: dict, email: str) -> dict:
    p = dict(payload or {})
    if email:
        p["operator_email"] = email
    return p


def has_console_access(email: str, agent_key: str) -> bool:
    agent_key = _normalize_agent_key(agent_key)
    if not agent_key:
        return False
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT sm.user_id, sm.role, s.id, s.owner_id
                FROM users u
                JOIN server_members sm ON sm.user_id = u.id
                JOIN servers s ON s.id = sm.server_id
                WHERE u.email=? COLLATE NOCASE
                  AND s.agent_key=?
                LIMIT 1
                """,
                (email, agent_key),
            ).fetchone()
            if not row:
                return False
            user_id, role, server_id, owner_id = row
            # 服务器所有者（owner_id）或成员角色为 owner 直通
            if owner_id == user_id or role == 'owner':
                return True
            # 检查面板权限组是否含 panel.console 或通配权限
            pg_row = conn.execute(
                "SELECT spg.id FROM server_member_panel_groups smpg "
                "JOIN server_panel_groups spg ON spg.id = smpg.group_id "
                "WHERE smpg.server_id=? AND smpg.user_id=?",
                (server_id, user_id),
            ).fetchone()
            if not pg_row:
                return False
            perms = conn.execute(
                "SELECT permission FROM server_panel_group_perms WHERE group_id=?",
                (pg_row[0],),
            ).fetchall()
            for (p,) in perms:
                if p == '*' or p == 'panel.console':
                    return True
                if p.endswith('.*'):
                    prefix = p[:-2]
                    if 'panel.console' == prefix or 'panel.console'.startswith(prefix + '.'):
                        return True
            return False
    except Exception:
        return False


def has_panel_permission(email: str, agent_key: str, permission: str) -> bool:
    agent_key = _normalize_agent_key(agent_key)
    if not agent_key:
        return False
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT sm.user_id, sm.role, s.id, s.owner_id
                FROM users u
                JOIN server_members sm ON sm.user_id = u.id
                JOIN servers s ON s.id = sm.server_id
                WHERE u.email=? COLLATE NOCASE
                  AND s.agent_key=?
                LIMIT 1
                """,
                (email, agent_key),
            ).fetchone()
            if not row:
                return False
            user_id, role, server_id, owner_id = row
            if owner_id == user_id or role == 'owner':
                return True

            pg_row = conn.execute(
                "SELECT spg.id FROM server_member_panel_groups smpg "
                "JOIN server_panel_groups spg ON spg.id = smpg.group_id "
                "WHERE smpg.server_id=? AND smpg.user_id=?",
                (server_id, user_id),
            ).fetchone()
            if not pg_row:
                return False
            perms = conn.execute(
                "SELECT permission FROM server_panel_group_perms WHERE group_id=?",
                (pg_row[0],),
            ).fetchall()
            for (p,) in perms:
                if p == '*' or p == permission:
                    return True
                if p.endswith('.*'):
                    prefix = p[:-2]
                    if permission == prefix or permission.startswith(prefix + '.'):
                        return True
            return False
    except Exception:
        return False


def is_character_owner(email: str, agent_key: str, username: str) -> bool:
    agent_key = _normalize_agent_key(agent_key)
    if not agent_key or not username:
        return False
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM users u
                JOIN game_characters gc ON gc.user_id = u.id
                WHERE u.email=? COLLATE NOCASE
                  AND gc.agent_key=?
                  AND gc.character_name=? COLLATE NOCASE
                LIMIT 1
                """,
                (email, agent_key, username),
            ).fetchone()
        return row is not None
    except Exception:
        return False


def is_server_member(email: str, agent_key: str) -> bool:
    """Check if the user is any member (including basic member) of the server."""
    agent_key = _normalize_agent_key(agent_key)
    if not agent_key:
        return False
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM users u
                JOIN server_members sm ON sm.user_id = u.id
                JOIN servers s ON s.id = sm.server_id
                WHERE u.email=? COLLATE NOCASE
                  AND s.agent_key=?
                LIMIT 1
                """,
                (email, agent_key),
            ).fetchone()
        return row is not None
    except Exception:
        return False


def list_member_agent_keys(email: str):
    """Return all agent_keys for servers the user has joined."""
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT s.agent_key
                FROM users u
                JOIN server_members sm ON sm.user_id = u.id
                JOIN servers s ON s.id = sm.server_id
                WHERE u.email=? COLLATE NOCASE
                """,
                (email,),
            ).fetchall()
        return [r[0] for r in rows if r and r[0]]
    except Exception:
        return []


async def broadcast_agent_to_authorized_webs(agent_key: str, message: str):
    # 将 agent_key 注入 metadata，前端凭此判断是哪个服务器发来的
    try:
        pkt = json.loads(message)
        if not isinstance(pkt.get("metadata"), dict):
            pkt["metadata"] = {}
        pkt["metadata"]["agent_key"] = agent_key
        tagged = json.dumps(pkt)
    except Exception:
        tagged = message

    dead = []
    for cid, ws in list(manager.active_webs.items()):
        email = WEB_CLIENT_EMAILS.get(cid)
        if not email or not has_console_access(email, agent_key):
            continue
        try:
            await ws.send_text(tagged)
        except Exception:
            dead.append(cid)

    for cid in dead:
        manager.active_webs.pop(cid, None)
        WEB_CLIENT_EMAILS.pop(cid, None)


async def broadcast_agent_to_members(agent_key: str, message: str):
    """Broadcast to all members (including basic members), used for agent_status and register_user_resp."""
    try:
        pkt = json.loads(message)
        if not isinstance(pkt.get("metadata"), dict):
            pkt["metadata"] = {}
        pkt["metadata"]["agent_key"] = agent_key
        tagged = json.dumps(pkt)
    except Exception:
        tagged = message

    dead = []
    for cid, ws in list(manager.active_webs.items()):
        email = WEB_CLIENT_EMAILS.get(cid)
        if not email or not is_server_member(email, agent_key):
            continue
        try:
            await ws.send_text(tagged)
        except Exception:
            dead.append(cid)

    for cid in dead:
        manager.active_webs.pop(cid, None)
        WEB_CLIENT_EMAILS.pop(cid, None)

def lookup_ts_info(email: str, agent_key: str = ""):
    """
        通过面板邮箱获取对应的 TShock 执行身份。
        优先级：
            1. 服务器所有者（owner_id）或成员角色为 owner，或具备 panel.console → superadmin 控制台权限
            2. 平台 RBAC groups 表中有 superadmin 组 → 控制台权限
            3. 平台 RBAC groups 表中有其他组 → 对应 TShock 组权限
            4. 兜底 → default 组（无特殊权限）
    """
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            # ① 优先：服务器 owner（owner_id 或成员角色）或具备 panel.console
            if agent_key:
                role_row = conn.execute(
                    """
                    SELECT sm.user_id, sm.role, s.owner_id FROM users u
                    JOIN server_members sm ON sm.user_id = u.id
                    JOIN servers s ON s.id = sm.server_id
                    WHERE u.email=? COLLATE NOCASE AND s.agent_key=?
                    LIMIT 1
                    """,
                    (email, agent_key),
                ).fetchone()
                if role_row and (role_row[0] == role_row[2] or role_row[1] == 'owner'):
                    return {"ts_user": "Console", "ts_group": "superadmin", "is_console": True}
                if has_panel_permission(email, agent_key, "panel.console"):
                    return {"ts_user": "Console", "ts_group": "superadmin", "is_console": True}

            # ② 回退：查平台 RBAC 组（兼容旧逻辑）
            row = conn.execute("""
                SELECT g.name FROM groups g
                JOIN user_groups ug ON g.id = ug.group_id
                JOIN users u ON u.id = ug.user_id
                WHERE u.email=? COLLATE NOCASE LIMIT 1
            """, (email,)).fetchone()

            if not row:
                return {"ts_user": "Guest", "ts_group": "default", "is_console": False}

            group_name = row[0]
            if group_name == "superadmin":
                return {"ts_user": "Console", "ts_group": "superadmin", "is_console": True}

            return {"ts_user": email.split("@")[0], "ts_group": group_name, "is_console": False}
    except Exception as e:
        print(f"Lookup error: {e}")
        return {"ts_user": "Guest", "ts_group": "default", "is_console": False}

@router.websocket("/ws/web")
async def web_endpoint(websocket: WebSocket, token: str = Query(default="")):
    client_id = None
    try:
        await websocket.accept()
        email = verify_token(token)
        if not email:
            await websocket.send_text(json.dumps({"type": "error", "msg": "未授权"}))
            await websocket.close(code=4001)
            return

        client_id = new_id()
        manager.active_webs[client_id] = websocket
        WEB_CLIENT_EMAILS[client_id] = email
        print(f"[Web上线] {email}")

        # Web 客户端认证成功，一并返回当前在线的 Agent 列表
        # 管理员看所有有控制台权限的；成员也能看到自己加入的服务器是否在线
        member_keys = {str(k).strip() for k in list_member_agent_keys(email)}
        online_agents = [k for k in list(manager.active_agents) if str(k).strip() in member_keys]
        await websocket.send_text(manager.make_envelope("auth", {
            "client_id": client_id, "role": "web", "email": email,
            "online_agents": online_agents
        }))

        while True:
            raw = await websocket.receive_text()
            try:
                packet = json.loads(raw)
            except Exception as e:
                print(f"[WS] 解析消息失败: {e}")
                continue

            if packet.get("type") == "cmd":
                payload = packet.get("payload", {})
                target_key = payload.get("agent_key")

                # 必须指定目标服务器，禁止广播命令
                if not target_key:
                    await websocket.send_text(manager.make_envelope("cmd_resp", {
                        "ref_id": packet.get("msg_id"),
                        "success": False,
                        "output": "必须指定目标服务器"
                    }))
                    continue

                # 仅 owner / web_staff 可连接并使用该服务器控制台
                if not has_console_access(email, target_key):
                    await websocket.send_text(manager.make_envelope("cmd_resp", {
                        "ref_id": packet.get("msg_id"),
                        "success": False,
                        "output": "无控制台权限，需要服务器 Owner 或 panel.console 权限"
                    }))
                    continue

                # 获取该面板用户对应的 TShock 映射身份
                executor = lookup_ts_info(email, target_key)

                if target_key not in manager.active_agents:
                    await websocket.send_text(manager.make_envelope("cmd_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd = json.dumps({
                    "type": "cmd", "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": {
                        "raw_cmd": payload.get("raw_cmd"),
                        "executor": executor,
                        "operator_email": email,
                    }
                })
                await manager.send_agent(target_key, fwd)

            elif packet.get("type") == "server_ctrl":
                payload = packet.get("payload", {})
                target_key = payload.get("agent_key")

                if not target_key:
                    await websocket.send_text(manager.make_envelope("server_ctrl_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                if not has_console_access(email, target_key):
                    await websocket.send_text(manager.make_envelope("server_ctrl_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限，需要服务器 Owner 或 panel.console 权限"
                    }))
                    continue

                if target_key not in manager.active_agents:
                    await websocket.send_text(manager.make_envelope("server_ctrl_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd = json.dumps({
                    "type": "server_ctrl", "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": {
                        "action": payload.get("action"),
                        "operator": email,
                        "operator_email": email,
                    }
                })
                await manager.send_agent(target_key, fwd)

            elif packet.get("type") == "file_list":
                payload = packet.get("payload", {})
                target_key = payload.get("agent_key")

                if not target_key:
                    await websocket.send_text(manager.make_envelope("file_list_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                if not has_console_access(email, target_key):
                    await websocket.send_text(manager.make_envelope("file_list_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限"
                    }))
                    continue

                if target_key not in manager.active_agents:
                    await websocket.send_text(manager.make_envelope("file_list_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd = json.dumps({
                    "type": "file_list", "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": {"operator_email": email}
                })
                await manager.send_agent(target_key, fwd)

            elif packet.get("type") == "register_user":
                payload    = packet.get("payload", {})
                target_key = payload.get("agent_key")

                if not target_key:
                    await websocket.send_text(manager.make_envelope("register_user_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                if not is_server_member(email, target_key):
                    await websocket.send_text(manager.make_envelope("register_user_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限，请先加入该服务器"
                    }))
                    continue

                # 密码黑名单检查
                username = (payload.get("username") or "").strip()
                password = payload.get("password") or ""
                BLACKLIST = {
                    "123456", "password", "123456789", "12345678", "12345",
                    "1234567", "111111", "000000", "qwerty", "abc123",
                    "letmein", "admin", "welcome", "monkey", "master",
                }
                if not username:
                    await websocket.send_text(manager.make_envelope("register_user_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "用户名不能为空"
                    }))
                    continue
                if len(password) < 6:
                    await websocket.send_text(manager.make_envelope("register_user_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "密码至少6位"
                    }))
                    continue
                if password.lower() in BLACKLIST:
                    await websocket.send_text(manager.make_envelope("register_user_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "密码过于简单，请更换密码"
                    }))
                    continue

                if target_key not in manager.active_agents:
                    await websocket.send_text(manager.make_envelope("register_user_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd = json.dumps({
                    "type": "register_user", "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": {
                        "username": username,
                        "password": password,
                        "panel_user_email": email,   # 让 Agent 回显，供干库写入使用
                        "operator_email": email,
                    }
                })
                await manager.send_agent(target_key, fwd)

            elif packet.get("type") == "send_bind_code":
                payload    = packet.get("payload", {})
                target_key = payload.get("agent_key")
                bnd_username = (payload.get("username") or "").strip()

                if not target_key or not bnd_username:
                    await websocket.send_text(manager.make_envelope("send_bind_code_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "参数不完整"
                    }))
                    continue

                if not is_server_member(email, target_key):
                    await websocket.send_text(manager.make_envelope("send_bind_code_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限"
                    }))
                    continue

                # 检查是否已被绑定
                with sqlite3.connect(AUTH_DB_PATH) as _chk:
                    already_bound = _chk.execute(
                        "SELECT id FROM game_characters "
                        "WHERE agent_key=? AND character_name=? COLLATE NOCASE",
                        (target_key, bnd_username),
                    ).fetchone()
                if already_bound:
                    await websocket.send_text(manager.make_envelope("send_bind_code_resp", {
                        "ref_id": packet.get("msg_id"), "success": False,
                        "msg": "该游戏账号已绑定到面板账号，无法重复绑定"
                    }))
                    continue

                # 生成 6 位数字验证码
                code = "".join([str(random.randint(0, 9)) for _ in range(6)])
                _bind_codes[(target_key, bnd_username.lower())] = {
                    "code": code,
                    "email": email,
                    "expires_at": time.time() + BIND_CODE_EXPIRE,
                }

                if target_key not in manager.active_agents:
                    # 离线时清除已生成的验证码，避免泵用
                    _bind_codes.pop((target_key, bnd_username.lower()), None)
                    await websocket.send_text(manager.make_envelope("send_bind_code_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd = json.dumps({
                    "type": "send_bind_code", "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": {
                        "username": bnd_username,
                        "code": code,
                        "operator_email": email,
                    }
                })
                await manager.send_agent(target_key, fwd)

            elif packet.get("type") == "get_char_info":
                payload    = packet.get("payload", {})
                target_key = payload.get("agent_key")

                if not target_key:
                    await websocket.send_text(manager.make_envelope("get_char_info_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                if not is_server_member(email, target_key):
                    await websocket.send_text(manager.make_envelope("get_char_info_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "未加入该服务器"
                    }))
                    continue

                if target_key not in manager.active_agents:
                    await websocket.send_text(manager.make_envelope("get_char_info_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd = json.dumps({
                    "type": "get_char_info", "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": {
                        "username": payload.get("username"),
                        "operator_email": email,
                    }
                })
                await manager.send_agent(target_key, fwd)

            elif packet.get("type") in ("player_list", "player_action",
                                          "world_progress", "player_stats"):
                payload    = packet.get("payload", {})
                target_key = payload.get("agent_key")
                resp_type  = packet.get("type") + "_resp"

                if not target_key:
                    await websocket.send_text(manager.make_envelope(resp_type, {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                # world_progress 和 player_stats 所有成员可查
                if packet.get("type") in ("player_list", "player_action"):
                    if not has_console_access(email, target_key):
                        await websocket.send_text(manager.make_envelope(resp_type, {
                            "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限，需要服务器 Owner 或 panel.console 权限"
                        }))
                        continue
                else:
                    if not is_server_member(email, target_key):
                        await websocket.send_text(manager.make_envelope(resp_type, {
                            "ref_id": packet.get("msg_id"), "success": False, "msg": "未加入该服务器"
                        }))
                        continue

                if target_key not in manager.active_agents:
                    await websocket.send_text(manager.make_envelope(resp_type, {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd_payload = with_operator({k: v for k, v in payload.items() if k != "agent_key"}, email)
                fwd = json.dumps({
                    "type": packet.get("type"), "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": fwd_payload
                })
                await manager.send_agent(target_key, fwd)

            elif packet.get("type") == "local_server_start":
                # 由 Python 后端直接启动 TShock（无需 Agent 在线）
                payload    = packet.get("payload", {})
                target_key = payload.get("agent_key")

                if not target_key:
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                if not has_console_access(email, target_key):
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限，需要服务器 Owner 或 panel.console 权限"
                    }))
                    continue

                # 查 DB 取 local_start_path
                try:
                    with sqlite3.connect(AUTH_DB_PATH) as _conn:
                        row = _conn.execute(
                            "SELECT local_start_path FROM servers WHERE agent_key=?",
                            (target_key,),
                        ).fetchone()
                except Exception as _e:
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": f"数据库查询失败: {_e}"
                    }))
                    continue

                script_path = (row[0] if row else "").strip()
                if not script_path:
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "启动脚本路径未配置"
                    }))
                    continue

                if not (script_path.endswith(".bat") or script_path.endswith(".sh")):
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "脚本路径非法，仅允许 .bat / .sh"
                    }))
                    continue

                if not os.path.isfile(script_path):
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": f"脚本文件不存在: {script_path}"
                    }))
                    continue

                # 检查是否已有追踪进程仍在运行
                existing_proc = _local_processes.get(target_key)
                if existing_proc is not None and existing_proc.poll() is None:
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "服务器进程已在后台运行"
                    }))
                    continue

                try:
                    cwd = os.path.dirname(os.path.abspath(script_path))
                    if sys.platform == "win32":
                        proc = subprocess.Popen(
                            [script_path],
                            cwd=cwd,
                            creationflags=subprocess.CREATE_NEW_CONSOLE,
                        )
                    else:
                        proc = subprocess.Popen(
                            ["bash", script_path],
                            cwd=cwd,
                        )
                    _local_processes[target_key] = proc
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": True,
                        "msg": f"已启动服务器进程 (PID {proc.pid})", "pid": proc.pid
                    }))
                except Exception as _e:
                    await websocket.send_text(manager.make_envelope("local_server_start_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": f"启动失败: {_e}"
                    }))

            elif packet.get("type") == "local_force_kill":
                # 由 Python 后端直接强杀已追踪的 TShock 进程
                payload    = packet.get("payload", {})
                target_key = payload.get("agent_key")

                if not target_key:
                    await websocket.send_text(manager.make_envelope("local_force_kill_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                if not has_console_access(email, target_key):
                    await websocket.send_text(manager.make_envelope("local_force_kill_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限，需要服务器 Owner 或 panel.console 权限"
                    }))
                    continue

                proc = _local_processes.get(target_key)
                if proc is None or proc.poll() is not None:
                    _local_processes.pop(target_key, None)
                    await websocket.send_text(manager.make_envelope("local_force_kill_resp", {
                        "ref_id": packet.get("msg_id"), "success": False,
                        "msg": "无追踪进程（服务器可能未由面板启动，或已退出）"
                    }))
                    continue

                try:
                    proc.kill()
                    _local_processes.pop(target_key, None)
                    await websocket.send_text(manager.make_envelope("local_force_kill_resp", {
                        "ref_id": packet.get("msg_id"), "success": True,
                        "msg": f"已强制终止进程 (PID {proc.pid})"
                    }))
                except Exception as _e:
                    await websocket.send_text(manager.make_envelope("local_force_kill_resp", {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": f"强杀失败: {_e}"
                    }))

            elif packet.get("type") in ("file_read", "file_write", "file_delete", "db_query", "db_exec", "db_update_row", "db_delete_row", "db_insert_row",
                                          "read_tshock_config", "write_tshock_config", "reload_tshock",
                                          "read_startup_script", "write_startup_script",
                                          "read_motd", "write_motd",
                                          "plugin_list_configs", "plugin_cloud_list",
                                          "plugin_check_apm", "plugin_install_apm",
                                          "plugin_local_list", "plugin_install", "plugin_uninstall",
                                          "plugin_check_updates", "plugin_update",
                                          "plugin_disable", "plugin_enable", "plugin_blacklist",
                                          "get_minimap", "get_player_positions",
                                          "get_inventory", "save_inventory",
                                          "list_bans", "unban_by_ticket", "update_ban_expiration",
                                          "get_groups", "list_game_groups",
                                          "create_game_group", "update_game_group", "delete_game_group"):
                payload    = packet.get("payload", {})
                target_key = payload.get("agent_key")
                resp_type  = packet.get("type") + "_resp"

                if not target_key:
                    await websocket.send_text(manager.make_envelope(resp_type, {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "必须指定目标服务器"
                    }))
                    continue

                if not has_console_access(email, target_key):
                    req_type = packet.get("type")
                    # 背包查看支持细粒度权限：自己 / 他人
                    if req_type == "get_inventory":
                        username = (payload.get("username") or "").strip()
                        is_self = is_character_owner(email, target_key, username)
                        needed = "panel.inventory.view.self" if is_self else "panel.inventory.view.others"
                        if not has_panel_permission(email, target_key, needed):
                            hint = "无权限，缺少查看自己背包权限" if is_self else "无权限，缺少查看他人背包权限"
                            await websocket.send_text(manager.make_envelope(resp_type, {
                                "ref_id": packet.get("msg_id"), "success": False, "msg": hint
                            }))
                            continue
                    elif req_type == "save_inventory":
                        await websocket.send_text(manager.make_envelope(resp_type, {
                            "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限，仅服务器 Owner 可修改背包"
                        }))
                        continue
                    else:
                        await websocket.send_text(manager.make_envelope(resp_type, {
                            "ref_id": packet.get("msg_id"), "success": False, "msg": "无权限，需要服务器 Owner 或对应权限"
                        }))
                        continue

                if target_key not in manager.active_agents:
                    await websocket.send_text(manager.make_envelope(resp_type, {
                        "ref_id": packet.get("msg_id"), "success": False, "msg": "Agent 当前离线"
                    }))
                    continue
                fwd_payload = with_operator({k: v for k, v in payload.items() if k != "agent_key"}, email)
                fwd = json.dumps({
                    "type": packet.get("type"), "msg_id": packet.get("msg_id"), "timestamp": now_ms(),
                    "payload": fwd_payload
                })
                await manager.send_agent(target_key, fwd)

    except WebSocketDisconnect:
        print(f"[Web离线] {WEB_CLIENT_EMAILS.get(client_id, 'unknown')}")
    except Exception as e:
        print(f"[WS] Web连接异常: {type(e).__name__}: {e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if client_id:
            manager.active_webs.pop(client_id, None)
            WEB_CLIENT_EMAILS.pop(client_id, None)

@router.websocket("/ws/agent")
async def agent_endpoint(websocket: WebSocket, agent_key: str = Query(default="")):
    try:
        await websocket.accept()

        agent_key = _normalize_agent_key(agent_key)

        # 用 agent_key 作为唯一识别 KEY；未传时倒退
        if not agent_key:
            await websocket.send_text(json.dumps({"type": "error", "msg": "缺少 agent_key"}))
            await websocket.close(code=4003)
            return

        # 如果同一 key 已经在线，断开旧连接
        if agent_key in manager.active_agents:
            try:
                await manager.active_agents[agent_key].close(code=4000)
            except Exception:
                pass

        manager.active_agents[agent_key] = websocket
        print(f"[Agent上线] key={agent_key}")
        await websocket.send_text(manager.make_envelope("auth", {"agent_key": agent_key, "role": "agent"}))

        # 通知已连接的 Web 客户端：Agent 已上线
        online_notif = json.dumps({"type": "agent_status", "msg_id": new_id(), "timestamp": now_ms(),
                                   "payload": {"agent_key": agent_key, "online": True}})
        await broadcast_agent_to_members(agent_key, online_notif)

        # 主动向 Agent 请求启动脚本路径，成功后自动写入 DB
        await websocket.send_text(json.dumps({
            "type": "read_startup_script", "msg_id": "__auto_probe__", "timestamp": now_ms(),
            "payload": {}
        }))

        while True:
            raw = await websocket.receive_text()
            try:
                packet = json.loads(raw)
            except Exception as e:
                print(f"[WS] Agent消息解析失败: {e}")
                continue
            if packet.get("type") == "status":
                # 状态包含玩家信息，全体成员可见
                gv = packet.get("payload", {}).get("game_version", "")
                if gv:
                    try:
                        with sqlite3.connect(AUTH_DB_PATH) as _conn:
                            _conn.execute(
                                "UPDATE servers SET game_version=? WHERE agent_key=?",
                                (gv, agent_key),
                            )
                            _conn.commit()
                    except Exception as _db_err:
                        print(f"[DB] 更新 game_version 失败: {_db_err}")
                await broadcast_agent_to_members(agent_key, raw)

            elif packet.get("type") == "register_user_resp":                # 拦截注册响应：成功则写入 DB
                p = packet.get("payload", {})
                if p.get("success"):
                    pu_email  = p.get("panel_user_email", "")
                    char_name = p.get("username", "")
                    try:
                        with sqlite3.connect(AUTH_DB_PATH) as conn:
                            uid_row = conn.execute(
                                "SELECT id FROM users WHERE email=? COLLATE NOCASE", (pu_email,)
                            ).fetchone()
                            if uid_row and char_name:
                                conn.execute(
                                    """
                                    INSERT OR IGNORE INTO game_characters
                                        (user_id, agent_key, character_name, registered_at)
                                    VALUES (?, ?, ?, strftime('%s','now'))
                                    """,
                                    (uid_row[0], agent_key, char_name),
                                )
                                conn.commit()
                    except Exception as db_err:
                        print(f"[DB] 写入 game_characters 失败: {db_err}")
                await broadcast_agent_to_members(agent_key, raw)

            elif packet.get("type") in ("get_char_info_resp", "send_bind_code_resp",
                                        "world_progress_resp", "player_stats_resp"):
                await broadcast_agent_to_members(agent_key, raw)

            elif packet.get("type") == "read_startup_script_resp":
                # 拦截启动脚本读取响应：若成功则自动将脚本路径写入 DB
                p = packet.get("payload", {})
                if p.get("success") and p.get("path"):
                    try:
                        with sqlite3.connect(AUTH_DB_PATH) as _conn:
                            _conn.execute(
                                "UPDATE servers SET local_start_path=? WHERE agent_key=?",
                                (p["path"], agent_key),
                            )
                            _conn.commit()
                    except Exception as _db_err:
                        print(f"[DB] 更新 local_start_path 失败: {_db_err}")
                # 仅当 ref_id 不是内部探针时才转发到前端
                if p.get("ref_id") != "__auto_probe__":
                    await broadcast_agent_to_authorized_webs(agent_key, raw)

            elif packet.get("type") in ("log", "cmd_resp", "chat",
                                       "file_list_resp", "server_ctrl_resp",
                                       "file_read_resp", "file_write_resp", "file_delete_resp",
                                       "db_query_resp", "db_exec_resp", "db_update_row_resp",
                                       "db_delete_row_resp", "db_insert_row_resp",
                                       "player_list_resp", "player_action_resp",
                                       "delete_user_resp", "read_tshock_config_resp", "write_tshock_config_resp",
                                       "write_startup_script_resp",
                                       "read_motd_resp", "write_motd_resp",
                                       "reload_tshock_resp",
                                       "plugin_list_configs_resp", "plugin_cloud_list_resp",
                                       "plugin_check_apm_resp", "plugin_install_apm_resp",
                                       "plugin_local_list_resp", "plugin_install_resp", "plugin_uninstall_resp",
                                       "plugin_check_updates_resp", "plugin_update_resp",
                                       "plugin_disable_resp", "plugin_enable_resp", "plugin_blacklist_resp",
                                       "minimap_resp", "player_positions_resp",
                                       "get_inventory_resp", "save_inventory_resp",
                                       "list_bans_resp", "unban_by_ticket_resp", "update_ban_expiration_resp",
                                       "change_password_resp", "get_groups_resp", "list_game_groups_resp",
                                       "create_game_group_resp", "update_game_group_resp", "delete_game_group_resp"):
                await broadcast_agent_to_authorized_webs(agent_key, raw)
    except WebSocketDisconnect:
        print(f"[Agent离线] key={agent_key}")
    except Exception as e:
        print(f"[WS] Agent连接异常: {type(e).__name__}: {e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if manager.active_agents.get(agent_key) is websocket:
            manager.active_agents.pop(agent_key, None)
            # 通知已连接的 Web 客户端：Agent 已下线
            offline_notif = json.dumps({"type": "agent_status", "msg_id": new_id(), "timestamp": now_ms(),
                                        "payload": {"agent_key": agent_key, "online": False}})
            try:
                await broadcast_agent_to_members(agent_key, offline_notif)
            except Exception:
                pass
