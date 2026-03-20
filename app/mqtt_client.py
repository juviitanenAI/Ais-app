# app/mqtt_client.py
import asyncio
import json
import threading
import time
from typing import Optional
import paho.mqtt.client as mqtt

from .config import settings
from . import state, db
from .ws_manager import WebSocketManager

def in_bbox(lat: float, lon: float) -> bool:
    bbox = settings.BBOX
    if not bbox:
        return True
    min_lon, min_lat, max_lon, max_lat = bbox
    return (min_lat <= lat <= max_lat) and (min_lon <= lon <= max_lon)

class MqttService:
    """
    Ylläpitää yhteyttä Digitraffic Marine MQTT/WebSocket ‑päätteeseen.
    Note: We use a single shared background connection to ingest data into our local DB/state.
    This architecture adheres to Digitrafic's 5 requests per minute limit by shielding
    the source from direct user-driven requests.
    """
    def __init__(self, ws_mgr: WebSocketManager, loop: asyncio.AbstractEventLoop):
        self.ws_mgr = ws_mgr
        self.loop = loop
        self.client: Optional[mqtt.Client] = None

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("[MQTT] Connected")
            # Aiheiden mallit dokumentaatiossa: vessels-v2/<mmsi>/location & /metadata
            client.subscribe("vessels-v2/+/location")
            client.subscribe("vessels-v2/+/metadata")
        else:
            print("[MQTT] Connect failed:", rc)

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            if not topic.startswith("vessels-v2/"):
                return
            parts = topic.split("/")
            mmsi, kind = parts[1], parts[2]
            payload = json.loads(msg.payload.decode("utf-8"))

            with state.latest_lock:
                v = state.latest.setdefault(mmsi, {"loc": None, "meta": {}, "last_seen": None})

                if kind == "metadata":
                    v["meta"].update(payload)
                    db.upsert_latest(mmsi, loc=None, meta=payload)

                elif kind == "location":
                    lat = payload.get("lat"); lon = payload.get("lon")
                    if lat is None or lon is None:
                        return
                    if not in_bbox(lat, lon):
                        return
                    v["loc"] = payload
                    v["last_seen"] = payload.get("time", int(time.time()))
                    db.upsert_latest(mmsi, loc=payload, meta=None)

                    # Lähetä WS:lle vain kiinnostuneille
                    vtype_code = str(v["meta"].get("type", ""))
                    style = state.vessel_type_cache.get(vtype_code, {})
                    vtype_info = {
                        "color": style.get("color", "#8899aa"),
                        "label": style.get("desc_en") or style.get("desc_fi") or "Other",
                        "category": style.get("category", "other")
                    }
                    message = {
                        "type": "location", 
                        "mmsi": mmsi, 
                        "loc": payload, 
                        "meta": v.get("meta", {}),
                        "vtype_info": vtype_info
                    }
                    asyncio.run_coroutine_threadsafe(self.ws_mgr.broadcast_location(mmsi, message), self.loop)

        except Exception as e:
            print("[MQTT] on_message error:", e)

    def start(self):
        def _run():
            client = mqtt.Client(transport="websockets")
            if settings.USE_SSL:
                client.tls_set()
            client.ws_set_options(
                path=settings.BROKER_PATH,
                headers={"Digitraffic-User": settings.DIGITRAFFIC_USER}
            )
            client.on_connect = self._on_connect
            client.on_message = self._on_message
            client.connect(settings.BROKER_HOST, settings.BROKER_PORT, keepalive=60)
            self.client = client
            client.loop_forever()
        threading.Thread(target=_run, daemon=True).start()