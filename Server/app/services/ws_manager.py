import asyncio
import json
from typing import Dict, Optional
from fastapi import WebSocket
from app.core.utils import now_ms, new_id

class ConnectionManager:
    def __init__(self):
        self.active_agents: Dict[str, WebSocket] = {}
        self.active_webs: Dict[str, WebSocket] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.pending_agent_responses: Dict[str, asyncio.Future] = {}

    def make_envelope(self, msg_type: str, payload: dict, msg_id: Optional[str] = None) -> str:
        return json.dumps({
            "type":      msg_type,
            "msg_id":    msg_id or new_id(),
            "timestamp": now_ms(),
            "payload":   payload,
        })

    async def broadcast_webs(self, message: str):
        dead = []
        for cid, ws in self.active_webs.items():
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.active_webs.pop(cid, None)

    async def send_agent(self, agent_id: Optional[str], message: str):
        targets = (
            {agent_id: self.active_agents[agent_id]}
            if agent_id and agent_id in self.active_agents
            else dict(self.active_agents)
        )
        dead = []
        for cid, ws in targets.items():
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.active_agents.pop(cid, None)

    async def request_agent(
        self,
        agent_id: str,
        msg_type: str,
        payload: dict,
        timeout: float = 8.0,
    ) -> dict:
        if not agent_id or agent_id not in self.active_agents:
            raise TimeoutError("Agent 当前离线")

        loop = asyncio.get_running_loop()
        msg_id = new_id()
        fut = loop.create_future()
        self.pending_agent_responses[msg_id] = fut
        try:
            await self.send_agent(agent_id, self.make_envelope(msg_type, payload, msg_id=msg_id))
            packet = await asyncio.wait_for(fut, timeout=timeout)
            return packet
        finally:
            self.pending_agent_responses.pop(msg_id, None)

    def resolve_agent_response(self, packet: dict) -> bool:
        payload = packet.get("payload") if isinstance(packet, dict) else None
        ref_id = payload.get("ref_id") if isinstance(payload, dict) else None
        if not ref_id:
            return False
        fut = self.pending_agent_responses.get(str(ref_id))
        if not fut or fut.done():
            return False
        fut.set_result(packet)
        return True

manager = ConnectionManager()
