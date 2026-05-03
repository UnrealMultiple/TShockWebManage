import sqlite3
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.config import AUTH_DB_PATH, BOOTSTRAP_TOKEN
from app.core.schema import init_auth_db
from app.core.qq_email import normalize_qq_email
from app.core.utils import hash_pw, make_token
from app.models.schemas import SendCodeReq, RegisterReq, LoginReq, ResetSendCodeReq, ResetConfirmReq, BootstrapPlatformAdminReq
from app.api import deps
from app.services.mail_service import send_email_code

router = APIRouter(prefix="/api/auth")

_pending = {}
# 验证码发送限流状态：key -> {timestamps: [ts...], lock_until: ts}
_code_send_guard = {}

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


def _has_platform_admin(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM users u JOIN AccountAccessGroups g ON g.id = u.access_group_id WHERE g.name='superadmin' LIMIT 1"
    ).fetchone() is not None


def _ensure_bootstrap_open(conn: sqlite3.Connection):
    if _has_platform_admin(conn):
        raise HTTPException(409, "平台已存在超级管理员，无需首次初始化")


def _check_bootstrap_token(token: str):
    if not BOOTSTRAP_TOKEN:
        raise HTTPException(503, "服务端未配置平台初始化令牌")
    if not token or token.strip() != BOOTSTRAP_TOKEN:
        raise HTTPException(403, "初始化令牌无效")


def init_db():
    init_auth_db()


init_db()

@router.post("/send-code")
async def api_send_code(req: SendCodeReq, request: Request):
    email = normalize_qq_email(req.email)

    client_ip = request.client.host if request.client else "unknown"
    _check_send_guard(email, "register", client_ip)
    
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone():
            raise HTTPException(409, "该邮箱已注册")
    
    salt = secrets.token_hex(16)
    pw_hash = hash_pw(req.password, salt)
    code = str(secrets.randbelow(900000) + 100000)
    
    _pending[email] = {
        "code": code,
        "expires_at": time.time() + 300,
        "pw_hash": pw_hash,
        "salt": salt,
    }
    
    try:
        await send_email_code(email, code)
    except Exception as e:
        raise HTTPException(500, f"邮件发送失败：{e}")

    _record_send_guard(email, "register", client_ip)
    return {"ok": True}

@router.post("/register")
async def api_register(req: RegisterReq):
    key = normalize_qq_email(req.email)
    p = _pending.get(key)
    if not p or time.time() > p["expires_at"]:
        raise HTTPException(400, "验证码无效或已过期")
    if p["code"] != req.code.strip():
        raise HTTPException(400, "验证码错误")
    
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            grow = cursor.execute("SELECT id FROM AccountAccessGroups WHERE name='default'").fetchone()
            access_group_id = grow[0] if grow else None
            cursor.execute("INSERT INTO users(email, pw_hash, salt, access_group_id, created_at) VALUES(?,?,?,?,?)",
                         (key, p["pw_hash"], p["salt"], access_group_id, int(time.time())))
            
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "邮箱占用")
    
    _pending.pop(key, None)
    return {"ok": True, "token": make_token(key), "email": key}

@router.post("/login")
async def api_login(req: LoginReq):
    email = normalize_qq_email(req.email)
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute("SELECT id, pw_hash, salt FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
    if not row or hash_pw(req.password, row[2]) != row[1]:
        raise HTTPException(401, "账号或密码错误")
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        banned = conn.execute(
            "SELECT 1 FROM AccountRestrictions WHERE user_id=? AND restriction_type='ban' AND is_active=1 LIMIT 1",
            (row[0],),
        ).fetchone()
    if banned:
        raise HTTPException(403, "账号已被平台封禁")
    return {"ok": True, "token": make_token(email), "email": email}


@router.get("/me")
async def api_me(current_user_id: int = Depends(deps.get_current_user_id)):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, email FROM users WHERE id = ?",
            (current_user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(401, "用户不存在")
    return {"id": row[0], "email": row[1]}


@router.get("/bootstrap-status")
async def api_bootstrap_status():
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        has_platform_admin = _has_platform_admin(conn)
    return {
        "bootstrap_required": not has_platform_admin,
        "has_platform_admin": has_platform_admin,
        "bootstrap_token_configured": bool(BOOTSTRAP_TOKEN),
    }


@router.post("/bootstrap-send-code")
async def api_bootstrap_send_code(req: SendCodeReq, request: Request, bootstrap_token: str):
    email = normalize_qq_email(req.email)

    _check_bootstrap_token(bootstrap_token)
    client_ip = request.client.host if request.client else "unknown"
    _check_send_guard(email, "bootstrap", client_ip)

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        _ensure_bootstrap_open(conn)
        if conn.execute("SELECT 1 FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone():
            raise HTTPException(409, "该邮箱已注册，不能用于首次平台初始化")

    salt = secrets.token_hex(16)
    pw_hash = hash_pw(req.password, salt)
    code = str(secrets.randbelow(900000) + 100000)
    key = f"bootstrap:{email}"
    _pending[key] = {
        "code": code,
        "expires_at": time.time() + 300,
        "pw_hash": pw_hash,
        "salt": salt,
    }

    try:
        await send_email_code(email, code)
    except Exception as e:
        raise HTTPException(500, f"邮件发送失败：{e}")

    _record_send_guard(email, "bootstrap", client_ip)
    return {"ok": True}


@router.post("/bootstrap-register")
async def api_bootstrap_register(req: RegisterReq, bootstrap_token: str):
    _check_bootstrap_token(bootstrap_token)
    email = normalize_qq_email(req.email)
    key = f"bootstrap:{email}"
    p = _pending.get(key)
    if not p or time.time() > p["expires_at"]:
        raise HTTPException(400, "验证码无效或已过期")
    if p["code"] != req.code.strip():
        raise HTTPException(400, "验证码错误")

    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            _ensure_bootstrap_open(conn)
            cursor = conn.cursor()
            grow = cursor.execute("SELECT id FROM AccountAccessGroups WHERE name='superadmin'").fetchone()
            access_group_id = grow[0] if grow else None
            cursor.execute(
                "INSERT INTO users(email, pw_hash, salt, access_group_id, created_at) VALUES(?,?,?,?,?)",
                (email, p["pw_hash"], p["salt"], access_group_id, int(time.time()))
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "邮箱占用")

    _pending.pop(key, None)
    return {"ok": True, "token": make_token(email), "email": email}


@router.post("/bootstrap-platform-admin")
async def api_bootstrap_platform_admin(
    req: BootstrapPlatformAdminReq,
    current_user_id: int = Depends(deps.get_current_user_id),
):
    if not BOOTSTRAP_TOKEN:
        raise HTTPException(503, "服务端未配置平台初始化令牌")
    if not req.bootstrap_token or req.bootstrap_token.strip() != BOOTSTRAP_TOKEN:
        raise HTTPException(403, "初始化令牌无效")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        if _has_platform_admin(conn):
            raise HTTPException(409, "平台已存在管理员，无需再执行初始化")

        user = conn.execute(
            "SELECT id, email FROM users WHERE id = ?",
            (current_user_id,),
        ).fetchone()
        if not user:
            raise HTTPException(404, "当前用户不存在")

        group = conn.execute("SELECT id FROM AccountAccessGroups WHERE name='superadmin'").fetchone()
        if not group:
            raise HTTPException(500, "超级管理员权限组不存在")
        conn.execute(
            "UPDATE users SET access_group_id=? WHERE id=?",
            (group[0], current_user_id),
        )

        conn.commit()
        return {
            "ok": True,
            "email": user[1],
            "message": "平台超级管理员初始化完成",
        }

# ── 忘记密码：发送重置验证码 ────────────────────────────────────
@router.post("/reset-send-code")
async def api_reset_send_code(req: ResetSendCodeReq, request: Request):
    key = normalize_qq_email(req.email)
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
        await send_email_code(key, code)
    except Exception as e:
        raise HTTPException(500, f"邮件发送失败：{e}")

    _record_send_guard(key, "reset", client_ip)
    return {"ok": True}

# ── 忘记密码：验证码校验 + 重置密码 ────────────────────────────
@router.post("/reset-confirm")
async def api_reset_confirm(req: ResetConfirmReq):
    key = normalize_qq_email(req.email)
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
