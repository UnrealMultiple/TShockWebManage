import asyncio
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.services.ws_manager import manager


async def request_agent_store(agent_key: str, msg_type: str, payload: Dict[str, Any], timeout: float = 8.0) -> Dict[str, Any]:
    try:
        packet = await manager.request_agent(agent_key, msg_type, payload, timeout=timeout)
    except TimeoutError:
        raise HTTPException(503, "Agent 当前离线或响应超时")
    except asyncio.TimeoutError:
        raise HTTPException(503, "Agent 响应超时")

    resp = packet.get("payload") if isinstance(packet, dict) else None
    if not isinstance(resp, dict):
        raise HTTPException(502, "Agent 返回数据无效")
    if not resp.get("success"):
        raise HTTPException(400, resp.get("msg") or "Agent 本地数据库操作失败")
    return resp


async def bind_character_on_agent(
    agent_key: str,
    user_id: int,
    email: str,
    character_name: str,
    source: str,
) -> Dict[str, Any]:
    return await request_agent_store(agent_key, "agent_character_bind", {
        "panel_user_id": user_id,
        "panel_email": email,
        "character_name": character_name,
        "source": source,
    })


async def delete_character_on_agent(
    agent_key: str,
    character_name: str,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"character_name": character_name}
    if user_id is not None:
        payload["panel_user_id"] = user_id
    return await request_agent_store(agent_key, "agent_character_delete", payload)


async def assign_character_on_agent(
    agent_key: str,
    character_name: str,
    target_user_id: Optional[int],
    target_email: str = "",
) -> Dict[str, Any]:
    return await request_agent_store(agent_key, "agent_character_assign", {
        "character_name": character_name,
        "target_user_id": target_user_id,
        "target_email": target_email,
    })


async def add_blacklist_on_agent(
    agent_key: str,
    target_user_id: int,
    target_email: str,
    reason: str,
    created_by_user_id: int,
    created_by_email: str,
) -> Dict[str, Any]:
    return await request_agent_store(agent_key, "agent_blacklist_add", {
        "target_user_id": target_user_id,
        "target_email": target_email,
        "reason": reason,
        "created_by_user_id": created_by_user_id,
        "created_by_email": created_by_email,
    })


async def remove_blacklist_on_agent(
    agent_key: str,
    target_user_id: int,
    removed_by_user_id: int,
    removed_by_email: str,
) -> Dict[str, Any]:
    return await request_agent_store(agent_key, "agent_blacklist_remove", {
        "target_user_id": target_user_id,
        "removed_by_user_id": removed_by_user_id,
        "removed_by_email": removed_by_email,
    })
