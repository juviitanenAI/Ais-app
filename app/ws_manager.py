# app/ws_manager.py
import json
from typing import Dict, Set
from fastapi import WebSocket
from .config import settings
from . import db

class WebSocketManager:
    """Hallinnoi WS-asiakkaita ja heidän tilaamiaan MMSI-listoja."""
    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = {}

    def tracked_union(self) -> Set[str]:
        tracked: Set[str] = set()
        for subs in self.subscriptions.values():
            tracked |= subs
        return tracked

    async def register(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)
        self.subscriptions[ws] = set()

    def unregister(self, ws: WebSocket):
        self.clients.discard(ws)
        self.subscriptions.pop(ws, None)

    async def handle_message(self, ws: WebSocket, data: str):
        """Odottaa viestejä muodossa: {"type":"subscribe","mmsi":["123","456"]}"""
        try:
            msg = json.loads(data)
            if msg.get("type") == "subscribe":
                incoming = {s for s in msg.get("mmsi", []) if s}
                prev = self.subscriptions.get(ws, set())
                newly_added = incoming - prev
                self.subscriptions[ws] = incoming

                # Halutessasi tee välitön aloite-näyte
                if settings.INITIAL_SNAPSHOT_ON_SUBSCRIBE and newly_added:
                    from .snapshot import snapshot_now_for_mmsis
                    await snapshot_now_for_mmsis(newly_added)
        except Exception:
            pass

    async def broadcast_location(self, mmsi: str, message: dict):
        """Lähetä live-sijainti vain niille klienteille, jotka seuraavat MMSI:tä."""
        text = json.dumps(message)
        stale = []
        for ws in list(self.clients):
            try:
                if mmsi in self.subscriptions.get(ws, set()):
                    await ws.send_text(text)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.unregister(ws)
            try:
                await ws.close()
            except Exception:
                pass