import json
import sqlite3
import time
from typing import Any, Dict, List, Optional

from app.core.config import AUTH_DB_PATH


def create_notification(
    receiver_user_id: int,
    msg_type: str,
    title: str,
    content: str,
    sender_user_id: Optional[int] = None,
    server_id: Optional[int] = None,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> int:
    now_ts = int(time.time())
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO messages(
                receiver_user_id, sender_user_id, server_id,
                type, ref_type, ref_id,
                title, content, payload_json,
                created_at, read_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,NULL)
            """,
            (
                receiver_user_id,
                sender_user_id,
                server_id,
                msg_type,
                ref_type,
                ref_id,
                title,
                content,
                payload_json,
                now_ts,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_notifications(
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    q: str = "",
    category: str = "all",
) -> List[sqlite3.Row]:
    limit = max(1, min(200, int(limit)))
    offset = max(0, int(offset))
    where_sql = """
        n.receiver_user_id=?
        AND (
            n.ref_type IS NULL
            OR n.ref_type != 'announcement'
            OR EXISTS (
                SELECT 1
                FROM announcements a
                WHERE a.id = n.ref_id
                  AND a.status = 'active'
            )
        )
    """
    params: List[Any] = [user_id]
    if unread_only:
        where_sql += " AND n.read_at IS NULL"
    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword}%"
        where_sql += """
            AND (
                n.title LIKE ?
                OR n.content LIKE ?
                OR su.email LIKE ?
                OR s.name LIKE ?
                OR CAST(n.ref_id AS TEXT) LIKE ?
            )
        """
        params.extend([like, like, like, like, like])
    if category == "join":
        where_sql += " AND n.type IN ('join_request_pending','join_request_result','join_request_rejected','join_request_approved','join_request_withdrawn')"
    elif category == "invite":
        where_sql += " AND n.type IN ('invite','invite_sent','invite_accepted','invite_rejected','invite_expired','invite_result')"
    elif category == "announcement":
        where_sql += " AND n.type = 'announcement'"
    elif category == "system":
        where_sql += " AND n.type NOT IN ('join_request_pending','join_request_result','join_request_rejected','join_request_approved','join_request_withdrawn','invite','invite_sent','invite_accepted','invite_rejected','invite_expired','invite_result','announcement')"

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT
                n.id, n.receiver_user_id, n.sender_user_id, su.email AS sender_email,
                n.server_id, s.name AS server_name, n.type, n.ref_type, n.ref_id,
                n.title, n.content, n.payload_json,
                n.created_at, n.read_at
            FROM messages n
            LEFT JOIN users su ON su.id = n.sender_user_id
            LEFT JOIN servers s ON s.id = n.server_id
            WHERE {where_sql}
            ORDER BY n.created_at DESC, n.id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        ).fetchall()
    return rows


def mark_read(user_id: int, message_id: int) -> bool:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, read_at FROM messages WHERE id=? AND receiver_user_id=?",
            (message_id, user_id),
        ).fetchone()
        if not row:
            return False
        if row[1] is None:
            conn.execute(
                "UPDATE messages SET read_at=? WHERE id=?",
                (int(time.time()), message_id),
            )
            conn.commit()
    return True


def mark_all_read(user_id: int) -> int:
    now_ts = int(time.time())
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        cur = conn.execute(
            "UPDATE messages SET read_at=? WHERE receiver_user_id=? AND read_at IS NULL",
            (now_ts, user_id),
        )
        conn.commit()
        return int(cur.rowcount or 0)


def unread_count(user_id: int) -> int:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM messages n
            WHERE n.receiver_user_id=?
              AND n.read_at IS NULL
              AND (
                  n.ref_type IS NULL
                  OR n.ref_type != 'announcement'
                  OR EXISTS (
                      SELECT 1
                      FROM announcements a
                      WHERE a.id = n.ref_id
                        AND a.status = 'active'
                  )
              )
            """,
            (user_id,),
        ).fetchone()
    return int(row[0] if row else 0)
