import sqlite3
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import AUTH_DB_PATH
from app.core.database import get_db
from app.core.utils import verify_token
from app.models.db_models import Server, ServerMemberRole
from app.models.schemas import (
    JoinRequestOut,
    NotificationOut,
    ServerInviteOut,
    ServerInviteRespondReq,
)
from app.services.membership_service import add_member
from app.services.notification_service import (
    create_notification,
    list_notifications,
    mark_all_read,
    mark_read,
    unread_count,
)

router = APIRouter(prefix="/api/messages", tags=["Messages"])


def _get_user_id(authorization: str = Header(...)) -> int:
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
    return int(row[0])


def _blacklist_join_block_reason(server_id: int, user_id: int, threshold: int) -> str:
    threshold = max(0, int(threshold or 0))
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        local = conn.execute(
            """
            SELECT COUNT(*)
            FROM agent_server_blacklist_cache
            WHERE server_id=? AND target_user_id=? AND status='active'
            """,
            (server_id, user_id),
        ).fetchone()
        if int(local[0] if local else 0) > 0:
            return "该账号已在本服务器黑名单中"
        if threshold > 0:
            cloud = conn.execute(
                """
                SELECT COUNT(*)
                FROM cloud_blacklist_entries
                WHERE target_user_id=? AND status='approved'
                """,
                (user_id,),
            ).fetchone()
            if int(cloud[0] if cloud else 0) >= threshold:
                return f"平台云黑记录达到 {threshold} 条"
    return ""


@router.get("", response_model=List[NotificationOut], summary="消息中心列表")
def get_messages(
    unread_only: bool = Query(False),
    q: str = Query(""),
    category: str = Query("all"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(_get_user_id),
):
    if category not in {"all", "join", "invite", "announcement", "system"}:
        raise HTTPException(400, "分类无效")
    rows = list_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
        q=q,
        category=category,
    )
    return [NotificationOut(**dict(r)) for r in rows]


@router.get("/unread-count", summary="获取未读数量")
def get_unread_count(user_id: int = Depends(_get_user_id)):
    return {"unread": unread_count(user_id)}


@router.post("/{message_id}/read", summary="标记单条消息已读")
def read_one_message(message_id: int, user_id: int = Depends(_get_user_id)):
    ok = mark_read(user_id=user_id, message_id=message_id)
    if not ok:
        raise HTTPException(404, "消息不存在")
    return {"ok": True}


@router.post("/read-all", summary="标记全部已读")
def read_all_messages(user_id: int = Depends(_get_user_id)):
    changed = mark_all_read(user_id=user_id)
    return {"ok": True, "changed": changed}


@router.get("/join-requests", response_model=List[JoinRequestOut], summary="列出我的入服申请")
def list_my_join_requests(
    status: Optional[str] = Query(None),
    user_id: int = Depends(_get_user_id),
):
    valid_status = {"pending", "approved", "rejected", "withdrawn"}
    if status and status not in valid_status:
        raise HTTPException(400, "状态无效")

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT
                r.id, r.server_id, r.applicant_user_id, au.email AS applicant_email,
                COALESCE(s.name, '') AS server_name,
                r.message, r.status, r.reviewed_by_user_id,
                ru.email AS reviewed_by_email,
                r.review_note, r.created_at, r.updated_at, r.withdrawn_at
            FROM (
                SELECT *, from_user_id AS applicant_user_id
                FROM server_member_requests
                WHERE request_type='join'
            ) r
            LEFT JOIN servers s ON s.id = r.server_id
            JOIN users au ON au.id = r.applicant_user_id
            LEFT JOIN users ru ON ru.id = r.reviewed_by_user_id
            WHERE r.applicant_user_id=?
        """
        params = [user_id]
        if status:
            sql += " AND r.status=?"
            params.append(status)
        sql += " ORDER BY r.created_at DESC, r.id DESC"
        rows = conn.execute(sql, tuple(params)).fetchall()

        server_ids = sorted({int(r["server_id"]) for r in rows if r["server_id"] is not None})
        server_code_map = {}
        if server_ids:
            placeholders = ",".join(["?"] * len(server_ids))
            code_rows = conn.execute(
                f"SELECT id, server_code FROM servers WHERE id IN ({placeholders})",
                tuple(server_ids),
            ).fetchall()
            server_code_map = {int(cid): (ccode or "") for (cid, ccode) in code_rows}

    result = []
    for r in rows:
        item = dict(r)
        item["server_code"] = server_code_map.get(int(item["server_id"]), "")
        result.append(JoinRequestOut(**item))
    return result


@router.post("/join-requests/{request_id}/withdraw", summary="撤回我的入服申请")
def withdraw_my_join_request(
    request_id: int,
    user_id: int = Depends(_get_user_id),
):
    now_ts = int(time.time())
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        req = conn.execute(
            """
            SELECT id, server_id, status
            FROM server_member_requests
            WHERE id=? AND request_type='join' AND from_user_id=?
            """,
            (request_id, user_id),
        ).fetchone()
        if not req:
            raise HTTPException(404, "申请不存在")
        if req["status"] != "pending":
            raise HTTPException(409, f"当前申请状态为 {req['status']}，不可撤回")

        conn.execute(
            """
            UPDATE server_member_requests
            SET status='withdrawn', withdrawn_at=?, updated_at=?
            WHERE id=?
            """,
            (now_ts, now_ts, request_id),
        )
        conn.commit()

    return {"ok": True, "status": "withdrawn"}


@router.get("/invites", response_model=List[ServerInviteOut], summary="列出我的邀请")
def list_my_invites(
    status: Optional[str] = Query(None),
    user_id: int = Depends(_get_user_id),
):
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
                FROM server_member_requests
                WHERE request_type='invite'
            ) i
            LEFT JOIN servers s ON s.id = i.server_id
            JOIN users inviter ON inviter.id = i.inviter_user_id
            JOIN users invitee ON invitee.id = i.invitee_user_id
            WHERE i.invitee_user_id=?
        """
        params = [user_id]
        if status:
            sql += " AND i.status=?"
            params.append(status)
        sql += " ORDER BY i.created_at DESC, i.id DESC"
        rows = conn.execute(sql, tuple(params)).fetchall()

    return [ServerInviteOut(**dict(r)) for r in rows]


@router.post("/invites/{invite_id}/respond", summary="处理邀请：接受或拒绝")
def respond_invite(
    invite_id: int,
    req: ServerInviteRespondReq,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_user_id),
):
    action = (req.action or "").strip().lower()
    if action not in {"accept", "reject"}:
        raise HTTPException(400, "action 仅支持 accept/reject")

    now_ts = int(time.time())
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        inv = conn.execute(
            """
            SELECT id, server_id, inviter_user_id, invitee_user_id, status, expires_at
            FROM (
                SELECT *, from_user_id AS inviter_user_id, to_user_id AS invitee_user_id
                FROM server_member_requests
                WHERE request_type='invite'
            )
            WHERE id=? AND invitee_user_id=?
            """,
            (invite_id, user_id),
        ).fetchone()
        if not inv:
            raise HTTPException(404, "邀请不存在")
        if inv["status"] != "pending":
            raise HTTPException(409, f"当前邀请状态为 {inv['status']}，不可重复处理")
        if inv["expires_at"] is not None and inv["expires_at"] < now_ts:
            conn.execute(
                "UPDATE server_member_requests SET status='expired', updated_at=? WHERE id=? AND request_type='invite'",
                (now_ts, invite_id),
            )
            conn.commit()
            raise HTTPException(409, "邀请已过期")

        if action == "accept":
            try:
                server = db.query(Server).filter_by(id=int(inv["server_id"])).first()
                if not server:
                    raise HTTPException(404, "服务器不存在")
                if server.owner_id is None:
                    raise HTTPException(400, "该服务器尚未被认领")
                block_reason = _blacklist_join_block_reason(
                    int(inv["server_id"]),
                    user_id,
                    int(getattr(server, "blacklist_auto_reject_count", 0) or 0),
                )
                if block_reason:
                    raise HTTPException(403, f"无法加入服务器：{block_reason}")
                add_member(
                    db=db,
                    server_id=int(inv["server_id"]),
                    user_id=user_id,
                    source="invite_accepted",
                    role=ServerMemberRole.member,
                    source_ref_type="invite",
                    source_ref_id=invite_id,
                    joined_by_user_id=int(inv["inviter_user_id"]),
                )
                db.commit()
            except HTTPException:
                db.rollback()
                raise
            except SQLAlchemyError as e:
                db.rollback()
                raise HTTPException(500, f"数据库错误: {e}")

        new_status = "accepted" if action == "accept" else "rejected"
        conn.execute(
            """
            UPDATE server_member_requests
            SET status=?, acted_at=?, updated_at=?
            WHERE id=? AND request_type='invite'
            """,
            (new_status, now_ts, now_ts, invite_id),
        )
        # 同时将对应邀请消息标记已读，避免消息中心残留未读。
        conn.execute(
            """
            UPDATE messages
            SET read_at=COALESCE(read_at, ?)
            WHERE receiver_user_id=? AND ref_type='invite' AND ref_id=?
            """,
            (now_ts, user_id, invite_id),
        )
        conn.commit()

    create_notification(
        receiver_user_id=int(inv["inviter_user_id"]),
        sender_user_id=user_id,
        server_id=int(inv["server_id"]),
        msg_type="invite_result",
        ref_type="invite",
        ref_id=invite_id,
        title="邀请处理结果",
        content="对方已接受邀请" if new_status == "accepted" else "对方已拒绝邀请",
        payload={"invite_id": invite_id, "status": new_status},
    )

    return {"ok": True, "status": new_status}
