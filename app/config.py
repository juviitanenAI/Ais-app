# app/config.py
from dataclasses import dataclass
from typing import Optional, Tuple
import os

@dataclass(frozen=True)
class Settings:
    # Digitraffic Marine (MQTT over WebSocket)
    BROKER_HOST: str = os.getenv("BROKER_HOST", "meri.digitraffic.fi")
    BROKER_PORT: int = int(os.getenv("BROKER_PORT", "443"))
    BROKER_PATH: str = os.getenv("BROKER_PATH", "/mqtt")      # WebSocket path (docs)
    USE_SSL: bool = True

    # Snapshots: 15 sek välein, 3 h historia UI:lle defaulttina
    SNAPSHOT_INTERVAL_SEC: int = int(os.getenv("SNAPSHOT_INTERVAL_SEC", str(30)))
    HISTORY_WINDOW_MINUTES: int = int(os.getenv("HISTORY_WINDOW_MINUTES", str(3 * 60)))
    SNAPSHOT_RETENTION_MINUTES: int = int(os.getenv("SNAPSHOT_RETENTION_MINUTES", str(7 * 24 * 60)))

    # Tee välitön ”aloitusnäyte” kun alus otetaan seurantaan (deduplikoidaan UNIQUE-indeksillä)
    INITIAL_SNAPSHOT_ON_SUBSCRIBE: bool = os.getenv("INITIAL_SNAPSHOT_ON_SUBSCRIBE", "true").lower() == "true"

    # Karkea aluefiltteri (lonMin, latMin, lonMax, latMax) – pienennä kuormaa
    BBOX: Optional[Tuple[float, float, float, float]] = (
        float(os.getenv("BBOX_LON_MIN", "16.0")),
        float(os.getenv("BBOX_LAT_MIN", "58.0")),
        float(os.getenv("BBOX_LON_MAX", "32.0")),
        float(os.getenv("BBOX_LAT_MAX", "66.0")),
    )

    # Stale vessel threshold (minutes) – vessels older than this are dimmed/hidden
    STALE_VESSEL_MINUTES: int = int(os.getenv("STALE_VESSEL_MINUTES", "30"))

    # SQLite
    DB_PATH: str = os.getenv("DB_PATH", "vessels.sqlite")

    # Digitraffic Buoy Measurements (SSE but polling 30min is fine)
    BUOY_SSE_URL: str = os.getenv("BUOY_SSE_URL", "https://meri.digitraffic.fi/api/sse/v1/measurements")

    # Rate limiting compliance
    # Use this header to identify the application as per Digitrafic's recommendations
    DIGITRAFFIC_USER: str = os.getenv("DIGITRAFFIC_USER", "Ais-app-research-project")

settings = Settings()