import json
import sqlite3
from fastapi import APIRouter, HTTPException, Depends, Header
from app.core.config import AUTH_DB_PATH
from app.core.utils import verify_token, has_permission, get_user_permissions
from app.models.schemas import GroupCreate, GroupUpdate, UserGroupUpdate
from typing import List, Optional

router = APIRouter(prefix="/api/rbac", tags=["RBAC"])

# 1. 权限校验 Dependency
async def check_admin_perm(authorization: str = Header(...)):
    """权限校验中间件，要求 superadmin 或 rbac.manage 权限"""
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    email = verify_token(token)
    if not email:
        raise HTTPException(401, "未登录或登录已过期")
    
    if not has_permission(email, "rbac.manage"):
        raise HTTPException(403, "没有权限管理 RBAC")
    return email

# 2. 组管理
@router.get("/groups")
async def list_groups(_ = Depends(check_admin_perm)):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        groups = conn.execute("SELECT id, name, parent_group_id, description, permissions FROM AccountAccessGroups").fetchall()
        result = []
        for g in groups:
            gid, name, pid, desc, perms_raw = g
            try:
                perms = json.loads(perms_raw or "[]")
                if not isinstance(perms, list):
                    perms = []
            except Exception:
                perms = []
            result.append({
                "id": gid,
                "name": name,
                "parent_id": pid,
                "description": desc,
                "permissions": [str(p) for p in perms if p]
            })
        return {"ok": True, "data": result}

@router.post("/groups")
async def create_group(req: GroupCreate, _ = Depends(check_admin_perm)):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO AccountAccessGroups(name, parent_group_id, description, permissions) VALUES(?,?,?,?)",
                (req.name, req.parent_id, req.description, json.dumps(req.permissions, ensure_ascii=False)),
            )
            gid = cursor.lastrowid
            conn.commit()
            return {"ok": True, "id": gid}
        except sqlite3.IntegrityError:
            raise HTTPException(400, "角色组名已存在")

@router.delete("/groups/{group_id}")
async def delete_group(group_id: int, _ = Depends(check_admin_perm)):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        # 不能删除核心角色 (模仿 TShock)
        group = conn.execute("SELECT name FROM AccountAccessGroups WHERE id=?", (group_id,)).fetchone()
        if not group:
             raise HTTPException(404, "组不存在")
        if group[0] in ['superadmin', 'admin', 'default']:
             raise HTTPException(403, f"不能删除系统内置角色: {group[0]}")
        
        conn.execute("UPDATE users SET access_group_id=NULL WHERE access_group_id=?", (group_id,))
        conn.execute("DELETE FROM AccountAccessGroups WHERE id=?", (group_id,))
        conn.commit()
    return {"ok": True}

# 3. 用户-组管理
@router.post("/users/{email}/groups")
async def update_account_access_group(email: str, req: UserGroupUpdate, _ = Depends(check_admin_perm)):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute("SELECT id FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if not row:
            raise HTTPException(404, "用户不存在")
        user_id = row[0]
        
        group_name = req.groups[0] if req.groups else "default"
        grow = conn.execute("SELECT id FROM AccountAccessGroups WHERE name=?", (group_name,)).fetchone()
        if not grow:
            raise HTTPException(404, "权限组不存在")
        conn.execute("UPDATE users SET access_group_id=? WHERE id=?", (grow[0], user_id))
        conn.commit()
    return {"ok": True}

@router.get("/users")
async def list_users_with_groups(_ = Depends(check_admin_perm)):
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        users = conn.execute("SELECT id, email, created_at FROM users").fetchall()
        result = []
        for u in users:
            uid, email, cat = u
            groups = conn.execute("""
                SELECT g.name FROM AccountAccessGroups g
                JOIN users u ON u.access_group_id = g.id
                WHERE u.id=?
            """, (uid,)).fetchall()
            result.append({
                "email": email,
                "created_at": cat,
                "groups": [g[0] for g in groups]
            })
        return {"ok": True, "data": result}
