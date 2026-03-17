"""
app package: Digitraffic Marine AIS application backend.

Modules:
- config: settings (broker, intervals, DB path, bbox)
- state: runtime cache for latest AIS per MMSI
- db: SQLite operations (upsert, snapshot, history)
- ws_manager: WebSocket client + subscription manager
- mqtt_client: MQTT/WebSocket client to Digitraffic Marine
- snapshot: 15‑minute snapshot scheduler for tracked vessels
"""

from .config import settings as _settings, Settings
from .ws_manager import WebSocketManager as WSManager
from .mqtt_client import MqttService
from . import db
from . import snapshot
from . import state

__all__ = [
    "Settings",
    "get_settings",
    "WSManager",
    "MqttService",
    "db",
    "snapshot",
    "state",
]

__version__ = "0.1.0"


def get_settings() -> Settings:
    """Return global Settings instance."""
    return _settings