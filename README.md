# AIS Ship Tracker ⚓

Real-time AIS ship tracking on nautical charts. Receives live vessel positions via MQTT from [Digitraffic Marine](https://www.digitraffic.fi/en/marine-traffic/) and displays them on an interactive OpenSeaMap map.

## Features

- **Live vessel positions** — all ships in the Baltic/Finland BBOX shown simultaneously
- **Nautical charts** — OpenSeaMap overlay on dark/light basemap
- **Ship type icons** — color-coded, rotated by heading (cargo, tanker, passenger, fishing)
- **Historical trails** — 24h position history at 15-sec resolution
- **Search & detail** — sidebar with vessel search, metadata, and speed/heading info
- **WebSocket push** — real-time updates, no polling

## Prerequisites

- **Python 3.10+**
- **pip**

## Setup

```bash
# Clone the repo
git clone https://github.com/juviitanenAI/Ais-app.git
cd Ais-app

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# Activate venv (if not already active)
source venv/bin/activate

# Start the app
python main.py
```

Open **http://localhost:8000** in your browser.

> The app connects to Digitraffic's public MQTT broker on startup. Vessels will start appearing on the map within ~10–30 seconds as AIS data streams in.

## Configuration

All settings can be overridden via environment variables:

| Variable                                                          | Default                     | Description                            |
| ----------------------------------------------------------------- | --------------------------- | -------------------------------------- |
| `BROKER_HOST`                                                     | `meri.digitraffic.fi`       | MQTT broker hostname                   |
| `BROKER_PORT`                                                     | `443`                       | MQTT broker port                       |
| `BROKER_PATH`                                                     | `/mqtt`                     | WebSocket path                         |
| `SNAPSHOT_INTERVAL_SEC`                                           | `900` (15 min)              | How often position snapshots are taken |
| `HISTORY_WINDOW_MINUTES`                                          | `180` (3h)                  | Default history window for the API     |
| `STALE_VESSEL_MINUTES`                                            | `30`                        | Vessels older than this are dimmed     |
| `BBOX_LON_MIN` / `BBOX_LAT_MIN` / `BBOX_LON_MAX` / `BBOX_LAT_MAX` | `16.0 / 58.0 / 32.0 / 66.0` | Bounding box filter (Finland/Baltics)  |
| `DB_PATH`                                                         | `vessels.sqlite`            | SQLite database file path              |

Example with custom settings:

```bash
BBOX_LAT_MIN=59.0 BBOX_LAT_MAX=61.0 python main.py
```

## API Endpoints

| Endpoint                                   | Description                       |
| ------------------------------------------ | --------------------------------- |
| `GET /`                                    | Map UI                            |
| `GET /simple`                              | Legacy simple UI                  |
| `GET /api/vessels?q=<search>`              | Vessel catalog (name/MMSI search) |
| `GET /api/vessels/live`                    | All vessels with current position |
| `GET /api/history?mmsi=<mmsi>&minutes=180` | Historical position samples       |
| `WS /ws`                                   | WebSocket for live updates        |

## Architecture

```
MQTT (Digitraffic) → mqtt_client.py → state.py (in-memory)
                                     → db.py (SQLite)
                                     → ws_manager.py → Browser (WebSocket)

Browser → /api/vessels/live (initial load)
        → /ws subscribe_all (live updates)
        → /api/history (historical trails)
```

## Project Structure

```
Ais-app/
├── main.py                 # Entrypoint: Uvicorn + MQTT + sampler
├── requirements.txt
├── vessels.sqlite           # Auto-created SQLite database
└── app/
    ├── __init__.py
    ├── api.py               # FastAPI routes
    ├── config.py             # Settings (env-configurable)
    ├── db.py                 # SQLite operations
    ├── mqtt_client.py        # MQTT client (Digitraffic)
    ├── snapshot.py           # 15-min position sampler
    ├── state.py              # In-memory vessel state
    ├── ws_manager.py         # WebSocket manager
    └── templates/
        ├── map_ui.html       # Main map UI (Leaflet + OpenSeaMap)
        └── simple_ui.html    # Legacy simple UI
```
