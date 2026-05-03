"""
API 依赖项
"""
import sqlite3
from fastapi import Header, HTTPException, Request
from typing import Optional

from app.core.config import AUTH_DB_PATH
from app.core.utils import get_user_permissions, verify_token


def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_current_user_id(authorization: str = Header(...)) -> int:
    """从 Token 获取当前用户 ID"""
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    email = verify_token(token)
    if not email:
        raise HTTPException(401, "未登录或登录已过期")
    
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE email=? COLLATE NOCASE",
            (email,),
        ).fetchone()
    
    if not row:
        raise HTTPException(401, "用户不存在")
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        banned = conn.execute(
            "SELECT 1 FROM AccountRestrictions WHERE user_id=? AND restriction_type='ban' AND is_active=1 LIMIT 1",
            (int(row[0]),),
        ).fetchone()
    if banned:
        raise HTTPException(403, "账号已被平台封禁")
    return int(row[0])


async def require_platform_admin(authorization: str = Header(...)) -> dict:
    """
    平台管理员验证依赖
    要求用户具有 platform.admin 权限或 is_platform_admin 为 True
    """
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    email = verify_token(token)
    if not email:
        raise HTTPException(401, "未登录或登录已过期")
    
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        # 获取用户 ID
        row = conn.execute(
            "SELECT id, email FROM users WHERE email=? COLLATE NOCASE",
            (email,),
        ).fetchone()
        
        if not row:
            raise HTTPException(401, "用户不存在")
        
        user_id, user_email = row[0], row[1]
        banned = conn.execute(
            "SELECT 1 FROM AccountRestrictions WHERE user_id=? AND restriction_type='ban' AND is_active=1 LIMIT 1",
            (user_id,),
        ).fetchone()
        if banned:
            raise HTTPException(403, "账号已被平台封禁")
        
        permissions = sorted(get_user_permissions(user_email))
        is_platform_admin = "*" in permissions
        if not is_platform_admin and not permissions:
            raise HTTPException(403, "需要平台管理员权限")

        return {
            "id": user_id,
            "email": user_email,
            "is_platform_admin": is_platform_admin,
            "permissions": permissions,
        }


def _has_platform_permission(current_user: dict, permission: str) -> bool:
    if current_user.get("is_platform_admin"):
        return True
    perms = current_user.get("permissions") or []
    for p in perms:
        if p == "*" or p == permission:
            return True
        if p.endswith(".*"):
            prefix = p[:-2]
            if permission == prefix or permission.startswith(prefix + "."):
                return True
    return False


def require_platform_permission(permission: str):
    async def _real_dependency(authorization: str = Header(...)) -> dict:
        current_user = await require_platform_admin(authorization)
        if not _has_platform_permission(current_user, permission):
            raise HTTPException(403, f"需要权限: {permission}")
        return current_user
    return _real_dependency


async def require_super_admin(authorization: str = Header(...)) -> dict:
    """
    超级管理员验证依赖
    要求用户具有 superadmin 角色
    """
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    email = verify_token(token)
    if not email:
        raise HTTPException(401, "未登录或登录已过期")
    
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        # 获取用户 ID
        row = conn.execute(
            "SELECT id, email FROM users WHERE email=? COLLATE NOCASE",
            (email,),
        ).fetchone()
        
        if not row:
            raise HTTPException(401, "用户不存在")
        
        user_id, user_email = row[0], row[1]
        
        # 检查是否 superadmin 权限组
        is_superadmin = conn.execute("""
            SELECT 1 FROM users u
            JOIN AccountAccessGroups g ON u.access_group_id = g.id
            WHERE u.email = ? COLLATE NOCASE AND g.name = 'superadmin'
        """, (email,)).fetchone()
        
        if not is_superadmin:
            raise HTTPException(403, "需要超级管理员权限")
        
        return {
            "id": user_id,
            "email": user_email
        }
