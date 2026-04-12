import sqlite3
import re
import secrets
import time
from fastapi import APIRouter, HTTPException, Request
from app.core.config import AUTH_DB_PATH
from app.core.utils import hash_pw, make_token
from app.models.schemas import SendCodeReq, RegisterReq, LoginReq, ResetSendCodeReq, ResetConfirmReq
from app.services.mail_service import send_email_code

router = APIRouter(prefix="/api/auth")

_pending = {}
# 验证码发送限流状态：key -> {timestamps: [ts...], lock_until: ts}
_code_send_guard = {}
QQ_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@qq\.com$", re.IGNORECASE)

# 单次发送冷却：同一邮箱至少间隔 60 秒
CODE_SEND_CD_SECONDS = 60
# 窗口限次：10 分钟内最多 5 次
CODE_SEND_WINDOW_SECONDS = 10 * 60
CODE_SEND_MAX_IN_WINDOW = 5
# 连续高频保护：2 分钟内达到 3 次触发风控锁定
CODE_SEND_BURST_WINDOW_SECONDS = 2 * 60
CODE_SEND_BURST_MAX = 3
CODE_SEND_RISK_LOCK_SECONDS = 10 * 60


def _guard_key(email: str, scene: str, client_ip: str) -> str:
    # 同邮箱 + 场景 + IP 独立限流，避免互相影响
    return f"{scene}:{email.lower()}:{client_ip}"


def _check_send_guard(email: str, scene: str, client_ip: str):
    now = time.time()
    key = _guard_key(email, scene, client_ip)
    state = _code_send_guard.get(key) or {"timestamps": [], "lock_until": 0}

    if now < state.get("lock_until", 0):
        remain = int(state["lock_until"] - now)
        raise HTTPException(429, f"发送过于频繁，已触发风控，请 {remain} 秒后重试")

    # 清理窗口外记录
    recent = [ts for ts in state.get("timestamps", []) if now - ts <= CODE_SEND_WINDOW_SECONDS]
    state["timestamps"] = recent

    if recent:
        since_last = now - recent[-1]
        if since_last < CODE_SEND_CD_SECONDS:
            remain = int(CODE_SEND_CD_SECONDS - since_last)
            raise HTTPException(429, f"请求过快，请 {remain} 秒后再发送验证码")

    burst = [ts for ts in recent if now - ts <= CODE_SEND_BURST_WINDOW_SECONDS]
    if len(burst) >= CODE_SEND_BURST_MAX:
        state["lock_until"] = now + CODE_SEND_RISK_LOCK_SECONDS
        _code_send_guard[key] = state
        raise HTTPException(429, f"单位时间内连续发送次数过多，请 {CODE_SEND_RISK_LOCK_SECONDS} 秒后重试")

    if len(recent) >= CODE_SEND_MAX_IN_WINDOW:
        remain = int(CODE_SEND_WINDOW_SECONDS - (now - recent[0]))
        raise HTTPException(429, f"发送次数已达上限，请 {remain} 秒后重试")

    _code_send_guard[key] = state


def _record_send_guard(email: str, scene: str, client_ip: str):
    now = time.time()
    key = _guard_key(email, scene, client_ip)
    state = _code_send_guard.get(key) or {"timestamps": [], "lock_until": 0}
    recent = [ts for ts in state.get("timestamps", []) if now - ts <= CODE_SEND_WINDOW_SECONDS]
    recent.append(now)
    state["timestamps"] = recent
    _code_send_guard[key] = state

def init_db():
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        # 用户表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT    UNIQUE NOT NULL,
                pw_hash    TEXT    NOT NULL,
                salt       TEXT    NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        # 角色组表 (Group)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    UNIQUE NOT NULL,
                parent_id   INTEGER,
                description TEXT,
                FOREIGN KEY (parent_id) REFERENCES groups(id)
            )
        """)
        # 权限表 (Permission)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS group_permissions (
                group_id   INTEGER NOT NULL,
                permission TEXT    NOT NULL,
                PRIMARY KEY (group_id, permission),
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)
        # 用户-组关联表 (User-Group Relation)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_groups (
                user_id    INTEGER NOT NULL,
                group_id   INTEGER NOT NULL,
                PRIMARY KEY (user_id, group_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)
        # 游戏角色绑定表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_characters (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                agent_key      TEXT    NOT NULL,
                character_name TEXT    NOT NULL,
                registered_at  INTEGER NOT NULL,
                UNIQUE(agent_key, character_name),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # 初始化默认角色 (模仿 TShock)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM groups WHERE name='superadmin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO groups(name, description) VALUES('superadmin', '超级管理员，拥有所有权限')")
            cursor.execute("INSERT INTO groups(name, description) VALUES('admin', '管理员')")
            cursor.execute("INSERT INTO groups(name, description) VALUES('default', '普通用户')")
            
            # 为 superadmin 添加通配符权限
            cursor.execute("SELECT id FROM groups WHERE name='superadmin'")
            sid = cursor.fetchone()[0]
            cursor.execute("INSERT INTO group_permissions(group_id, permission) VALUES(?, '*')", (sid,))
            
        conn.commit()

init_db()

@router.post("/send-code")
async def api_send_code(req: SendCodeReq, request: Request):
    if not QQ_RE.match(req.email):
        raise HTTPException(400, "仅支持 QQ 邮箱注册")

    client_ip = request.client.host if request.client else "unknown"
    _check_send_guard(req.email, "register", client_ip)
    
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=? COLLATE NOCASE", (req.email,)).fetchone():
            raise HTTPException(409, "该邮箱已注册")
    
    salt = secrets.token_hex(16)
    pw_hash = hash_pw(req.password, salt)
    code = str(secrets.randbelow(900000) + 100000)
    
    _pending[req.email.lower()] = {
        "code": code,
        "expires_at": time.time() + 300,
        "pw_hash": pw_hash,
        "salt": salt,
    }
    
    try:
        await send_email_code(req.email, code)
    except Exception as e:
        raise HTTPException(500, f"邮件发送失败：{e}")

    _record_send_guard(req.email, "register", client_ip)
    return {"ok": True}

@router.post("/register")
async def api_register(req: RegisterReq):
    if not QQ_RE.match(req.email):
        raise HTTPException(400, "仅支持 QQ 邮箱注册")

    key = req.email.lower()
    p = _pending.get(key)
    if not p or time.time() > p["expires_at"]:
        raise HTTPException(400, "验证码无效或已过期")
    if p["code"] != req.code.strip():
        raise HTTPException(400, "验证码错误")
    
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users(email, pw_hash, salt, created_at) VALUES(?,?,?,?)",
                         (key, p["pw_hash"], p["salt"], int(time.time())))
            uid = cursor.lastrowid
            
            # 默认赋予 'default' 角色
            grow = cursor.execute("SELECT id FROM groups WHERE name='default'").fetchone()
            if grow:
                cursor.execute("INSERT INTO user_groups(user_id, group_id) VALUES(?,?)", (uid, grow[0]))
            
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "邮箱占用")
    
    _pending.pop(key, None)
    return {"ok": True, "token": make_token(key), "email": key}

@router.post("/login")
async def api_login(req: LoginReq):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute("SELECT pw_hash, salt FROM users WHERE email=? COLLATE NOCASE", (req.email,)).fetchone()
    if not row or hash_pw(req.password, row[1]) != row[0]:
        raise HTTPException(401, "账号或密码错误")
    return {"ok": True, "token": make_token(req.email.lower()), "email": req.email.lower()}

# ── 忘记密码：发送重置验证码 ────────────────────────────────────
@router.post("/reset-send-code")
async def api_reset_send_code(req: ResetSendCodeReq, request: Request):
    key = req.email.lower()
    client_ip = request.client.host if request.client else "unknown"
    _check_send_guard(key, "reset", client_ip)
    
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        if not conn.execute("SELECT 1 FROM users WHERE email=? COLLATE NOCASE", (key,)).fetchone():
            # 不暴露账号是否存在，统一返回成功，防止账号枚举
            _record_send_guard(key, "reset", client_ip)
            return {"ok": True}
    
    code = str(secrets.randbelow(900000) + 100000)
    _pending[f"reset:{key}"] = {
        "code": code,
        "expires_at": time.time() + 300,
    }

    try:
        await send_email_code(req.email, code)
    except Exception as e:
        raise HTTPException(500, f"邮件发送失败：{e}")

    _record_send_guard(key, "reset", client_ip)
    return {"ok": True}

# ── 忘记密码：验证码校验 + 重置密码 ────────────────────────────
@router.post("/reset-confirm")
async def api_reset_confirm(req: ResetConfirmReq):
    key = req.email.lower()
    pending_key = f"reset:{key}"
    p = _pending.get(pending_key)
    
    if not p or time.time() > p["expires_at"]:
        raise HTTPException(400, "验证码无效或已过期")
    if p["code"] != req.code.strip():
        raise HTTPException(400, "验证码错误")
    
    salt = secrets.token_hex(16)
    pw_hash = hash_pw(req.new_password, salt)
    
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        updated = conn.execute(
            "UPDATE users SET pw_hash=?, salt=? WHERE email=? COLLATE NOCASE",
            (pw_hash, salt, key)
        ).rowcount
    
    if not updated:
        raise HTTPException(404, "用户不存在")
    
    _pending.pop(pending_key, None)
    return {"ok": True}
