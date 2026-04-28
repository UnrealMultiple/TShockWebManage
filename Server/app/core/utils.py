import hashlib
import sqlite3
import time
import uuid
import jwt
import datetime
from typing import Optional, List, Set
from app.core.config import JWT_SECRET, JWT_HOURS, AUTH_DB_PATH

def now_ms() -> int:
    """获取当前时间的毫秒级时间戳"""
    return int(time.time() * 1000)

def new_id() -> str:
    """生成唯一的 UUID 标识符"""
    return str(uuid.uuid4())

def hash_pw(password: str, salt: str) -> str:
    """对密码进行 SHA-256 加密"""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def make_token(email: str) -> str:
    """生成 JWT 认证令牌"""
    payload = {
        "sub": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> Optional[str]:
    """验证 JWT 令牌并返回用户邮箱"""
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return data.get("sub")
    except Exception:
        return None

def get_user_permissions(email: str) -> Set[str]:
    """获取用户的所有权限节点，支持继承体系"""
    permissions = set()
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        # 获取用户所属的组
        row = conn.execute("SELECT id FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if not row:
            return permissions
        user_id = row[0]
        
        # 递归检查组权限 (支持 RBAC 继承)
        groups_to_check = []
        rows = conn.execute("SELECT group_id FROM account_role_members WHERE user_id=?", (user_id,)).fetchall()
        for r in rows:
            groups_to_check.append(r[0])
            
        checked_groups = set()
        while groups_to_check:
            gid = groups_to_check.pop(0)
            if gid in checked_groups:
                continue
            checked_groups.add(gid)
            
            # 获取当前组权限
            perms = conn.execute("SELECT permission FROM account_role_permissions WHERE group_id=?", (gid,)).fetchall()
            for p in perms:
                permissions.add(p[0])
            
            # 获取父组并加入待检查列表
            parent = conn.execute("SELECT parent_id FROM account_roles WHERE id=?", (gid,)).fetchone()
            if parent and parent[0]:
                groups_to_check.append(parent[0])
    
    return permissions

def has_permission(email: str, permission: str) -> bool:
    """检查用户是否具有指定权限"""
    # 如果用户没有任何权限，直接返回 False
    user_perms = get_user_permissions(email)
    if "*" in user_perms: 
        return True # 超管
        
    if permission in user_perms:
        return True
    
    # 支持通配符父节点检查 (e.g. user.edit 匹配 user.*)
    parts = permission.split(".")
    for i in range(len(parts)):
        check = ".".join(parts[:i]) + ".*"
        if check in user_perms:
            return True
            
    return False
