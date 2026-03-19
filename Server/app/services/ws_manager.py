import json
from typing import Dict, Optional
from fastapi import WebSocket
from app.core.utils import now_ms, new_id

class ConnectionManager:
    def __init__(self):
        self.active_agents: Dict[str, WebSocket] = {}
        self.active_webs: Dict[str, WebSocket] = {}

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

manager = ConnectionManager()
