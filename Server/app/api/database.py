import os
import re
import sqlite3
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.core.config import AUTH_DB_PATH
from app.core.utils import has_permission, verify_token

router = APIRouter(prefix="/api/db", tags=["database"])

ALLOWED_DBS: Dict[str, str] = {
    "auth":    AUTH_DB_PATH,
}

_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


# ── 内部工具 ─────────────────────────────────────────────────────

def _auth(authorization: str) -> str:
    """验证 JWT，返回 email；失败则 401。"""
    token = authorization.removeprefix("Bearer ").strip()
    email = verify_token(token)
    if not email:
        raise HTTPException(401, "未登录或登录已过期")
    return email


def _resolve(db_name: str) -> str:
    """返回数据库文件路径；不在白名单或文件不存在则报错。"""
    if db_name not in ALLOWED_DBS:
        raise HTTPException(400, "未知数据库")
    path = ALLOWED_DBS[db_name]
    if not os.path.exists(path):
        raise HTTPException(404, "数据库文件不存在")
    return path


def _chk(name: str):
    """验证标识符（表名/列名）合法性，防注入。"""
    if not _IDENT_RE.match(name):
        raise HTTPException(400, f"非法标识符: {name!r}")


def _require_write_perm(db_name: str, email: str):
    """auth 数据库写操作需要 superadmin（* 权限）。"""
    if db_name == "auth" and not has_permission(email, "*"):
        raise HTTPException(403, "需要超级管理员权限才能修改认证数据库")


# ── Request Models ───────────────────────────────────────────────

class RowUpdateReq(BaseModel):
    pk_col: str
    pk_val: Any
    data:   Dict[str, Any]


class RowDeleteReq(BaseModel):
    pk_col: str
    pk_val: Any


class RowInsertReq(BaseModel):
    data: Dict[str, Any]


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/list")
def list_databases(authorization: str = Header(...)):
    """列出所有允许访问的数据库及其存在状态。"""
    _auth(authorization)
    return {
        "ok":   True,
        "data": [
            {"name": name, "exists": os.path.exists(path)}
            for name, path in ALLOWED_DBS.items()
        ],
    }


@router.get("/{db_name}/tables")
def list_tables(db_name: str, authorization: str = Header(...)):
    """列出数据库中所有表。"""
    _auth(authorization)
    path = _resolve(db_name)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    return {"ok": True, "data": [r[0] for r in rows]}


@router.get("/{db_name}/table/{table_name}")
def query_table(
    db_name:    str,
    table_name: str,
    page:       int = Query(1,  ge=1),
    page_size:  int = Query(50, ge=1, le=500),
    authorization: str = Header(...),
):
    """分页查询表数据，同时返回列元数据和总行数。"""
    _auth(authorization)
    path = _resolve(db_name)
    _chk(table_name)

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row

        cols_info = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        if not cols_info:
            raise HTTPException(404, "表不存在")

        columns = [
            {
                "name":    c["name"],
                "type":    c["type"],
                "pk":      bool(c["pk"]),
                "notnull": bool(c["notnull"]),
            }
            for c in cols_info
        ]

        total  = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        offset = (page - 1) * page_size
        rows   = conn.execute(
            f'SELECT * FROM "{table_name}" LIMIT ? OFFSET ?', (page_size, offset)
        ).fetchall()

    return {
        "ok": True,
        "data": {
            "columns":   columns,
            "rows":      [dict(r) for r in rows],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        },
    }


@router.put("/{db_name}/table/{table_name}/row")
def update_row(
    db_name:    str,
    table_name: str,
    req:        RowUpdateReq,
    authorization: str = Header(...),
):
    """按主键更新一行。"""
    email = _auth(authorization)
    _require_write_perm(db_name, email)

    path = _resolve(db_name)
    _chk(table_name)
    _chk(req.pk_col)
    for col in req.data:
        _chk(col)

    if not req.data:
        raise HTTPException(400, "无修改数据")

    set_clause = ", ".join(f'"{c}" = ?' for c in req.data)
    values     = [*req.data.values(), req.pk_val]

    with sqlite3.connect(path) as conn:
        r = conn.execute(
            f'UPDATE "{table_name}" SET {set_clause} WHERE "{req.pk_col}" = ?',
            values,
        )
        conn.commit()
        if r.rowcount == 0:
            raise HTTPException(404, "未找到对应行")

    return {"ok": True}


@router.post("/{db_name}/table/{table_name}/row")
def insert_row(
    db_name:    str,
    table_name: str,
    req:        RowInsertReq,
    authorization: str = Header(...),
):
    """向表中插入新行。"""
    email = _auth(authorization)
    _require_write_perm(db_name, email)

    path = _resolve(db_name)
    _chk(table_name)
    for col in req.data:
        _chk(col)

    if not req.data:
        raise HTTPException(400, "无插入数据")

    cols         = ", ".join(f'"{c}"'  for c in req.data)
    placeholders = ", ".join("?"       for _ in req.data)

    with sqlite3.connect(path) as conn:
        cur = conn.cursor()
        cur.execute(
            f'INSERT INTO "{table_name}" ({cols}) VALUES ({placeholders})',
            list(req.data.values()),
        )
        new_id = cur.lastrowid
        conn.commit()

    return {"ok": True, "id": new_id}


@router.delete("/{db_name}/table/{table_name}/row")
def delete_row(
    db_name:    str,
    table_name: str,
    req:        RowDeleteReq,
    authorization: str = Header(...),
):
    """按主键删除一行。"""
    email = _auth(authorization)
    _require_write_perm(db_name, email)

    path = _resolve(db_name)
    _chk(table_name)
    _chk(req.pk_col)

    with sqlite3.connect(path) as conn:
        r = conn.execute(
            f'DELETE FROM "{table_name}" WHERE "{req.pk_col}" = ?',
            [req.pk_val],
        )
        conn.commit()
        if r.rowcount == 0:
            raise HTTPException(404, "未找到对应行")

    return {"ok": True}
