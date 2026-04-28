import time
from typing import Optional

from sqlalchemy.orm import Session

from app.models.db_models import ServerMember, ServerMemberRole


def add_member(
    db: Session,
    server_id: int,
    user_id: int,
    source: str,
    role: ServerMemberRole = ServerMemberRole.member,
    source_ref_type: Optional[str] = None,
    source_ref_id: Optional[int] = None,
    joined_by_user_id: Optional[int] = None,
) -> ServerMember:
    """统一成员写入入口，保证所有入会路径可追踪来源。"""
    existing = db.query(ServerMember).filter_by(server_id=server_id, user_id=user_id).first()
    if existing:
        if role == ServerMemberRole.owner and existing.role != ServerMemberRole.owner:
            existing.role = ServerMemberRole.owner
        return existing

    member = ServerMember(
        server_id=server_id,
        user_id=user_id,
        role=role,
        joined_at=int(time.time()),
        join_source=source,
        join_source_ref_type=source_ref_type,
        join_source_ref_id=source_ref_id,
        joined_by_user_id=joined_by_user_id,
    )
    db.add(member)
    db.flush()
    return member
