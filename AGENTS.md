# Agents.md

## Overview

AIS-app is a real-time maritime surveillance and vessel tracking application. It utilizes a FastAPI backend to ingest AIS (Automatic Identification System) data via MQTT and buoy measurements, persisting them in SQLite and serving them to a reactive Svelte frontend via WebSockets and REST.

## Architecture

- **Backend (FastAPI)**:
  - **Lifespan Management**: Handles DB schema initialization, integrity checks, and service startup (MQTT, Buoy, Sampler, Flusher).
  - **State Management**: In-memory thread-safe storage (`state.py`) for the latest vessel positions and buoy data to minimize DB latency.
  - **Ingestion**: `MqttService` for live AIS; `BuoyService` for environmental data.
  - **Persistence**: `sampler_task` takes snapshots; `flusher_task` commits to SQLite.
  - **Caching**: Pre-computed heatmap and trend data stored in dedicated SQLite tables for sub-second API responses.
- **Frontend (Svelte)**:
  - **Reactivity**: Svelte stores manage live updates from WebSockets.
  - **Visualization**: Map-centric UI for real-time tracking, historical paths, and heatmaps.
- **Database (SQLite)**:
  - Optimized with WAL (Write-Ahead Logging) for concurrent read/write.
  - Custom functions/indices for spatial and temporal queries.

## Features

- **Live Tracking**: WebSocket-driven vessel updates and buoy telemetry.
- **Vessel Catalog**: Searchable index of vessels by MMSI/Name with background type synchronization (Digitraffic).
- **History & Playback**: 15-minute sampled historical tracks for specified vessels.
- **Analytics**: Dynamic route heatmaps and activity trends (12h to 1w windows).
- **Integrity Guard**: Automated startup verification of the multi-GB spatial database.

## Testing Strategy

- **Mandatory**: Every new feature/endpoint must include a corresponding test in `tests/`.
- **Backend**: `pytest` for unit/integration testing of API routes, DB queries, and service logic.
- **Frontend**: Component testing via Vitest/Svelte Testing Library (where applicable).
- **CI/CD**: Mock MQTT/Buoy services to validate ingestion pipelines without external dependencies.
- **Performance**: Stress-test WebSocket congestion and SQLite query latency on large datasets.

## Development Workflow

1. **Environment**: `make setup` (install python deps + npm install).
2. **Backend**: `make dev-backend` (uvicorn with --reload).
3. **Frontend**: `make dev-frontend` (vite dev server).
4. **Build**: `make build` (compile frontend to `frontend/dist` for FastAPI serving).
5. **Lint/Test**: `make check` (runs ruff/eslint and pytest).

## Debugging (Signal-Path)

All planning and debugging follow this strict path:

- **Signal**: [The triggering input, error message, or system event]
- **Path**: [The specific sequence of execution or data flow: Component A → Component B → Component C]
- **Debug/Plan**: [The isolated root cause or proposed implementation action]

---

**Architect's Note**: Challenge every design suggestion. Avoid bloat. If a feature can be done with a simpler SQL query or a more efficient Svelte store, do it. Do not add dependencies unless the cost of maintaining a custom solution outweighs the overhead.

Never run tests unless explicitly asked by the user.
