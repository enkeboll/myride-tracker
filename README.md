# MyRide K12 Bus Location Tracker, Schedule Manager & Web Dashboard

A Python backend service and web dashboard that authenticates with **MyRide K12 (AWS Cognito)**, negotiates an **ASP.NET Core SignalR WebSocket** stream, receives real-time bus location updates, and logs them into a local **SQLite WAL** database (portable to Synology NAS via Docker).

---

## Features

- **CARTO Vector Basemaps**: Uses MapLibre GL JS and CARTO's official GL style vector tiles (`https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json`) for crisp, high-DPI vector rendering, WebGL performance, and sharp font labels.
- **Active Bus Window Scheduler**: Monitored automatically during active bus hours (**Monday–Friday, 7:45 AM – 8:50 AM ET**). Outside this window, the service remains in low-power standby while serving historical data.
- **Embedded Web Dashboard**: Modern responsive UI (`http://localhost:8080`) featuring:
  - **Live Status Indicator**: Active (Streaming) vs Standby (Off-Hours) with timezone notice.
  - **Interactive Vector Map**: Built with MapLibre GL JS & CARTO Vector Dark Matter basemap, plotting live bus markers & GeoJSON breadcrumb route trails.
  - **Bus Status Cards**: Real-time speed, heading, assigned bus number (e.g. Bus #53), student details, and last reported timestamp.
  - **Location History Table**: Filterable history table displaying recorded points.
- **Automated Authentication**: Authenticates directly using your MyRide username and password via AWS Cognito `USER_PASSWORD_AUTH` (or long-lived `refresh_token`), automatically renewing access tokens.
- **REST API Discovery**: Automatically fetches user metadata, district tenant ID GUID, and assigned student bus numbers.
- **SignalR WebSocket Streaming**: Connects to `wss://myridek12.tylerapi.com/livevehiclehub`, parses SignalR JSON protocol record delimiters (`\x1e`), handles 15-second keep-alive pings (`type: 6`), and dispatches live `NewLocation` updates.
- **SQLite WAL Storage**: Asynchronously logs bus coordinates (`asset_unique_id`, `latitude`, `longitude`, `speed`, `heading`, `log_time`, and `raw_payload`) into `myride.db` using SQLite Write-Ahead Logging mode (`PRAGMA journal_mode=WAL;`).
- **Docker & NAS Ready**: Containerized with a multi-stage `Dockerfile` and `docker-compose.yml` for Synology NAS deployment with persistent database volumes.

---

## Quickstart Guide (Local Development)

### 1. Environment Setup

Create a Python virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your MyRide K12 credentials:

```env
MYRIDE_USERNAME=your_email@domain.com
MYRIDE_PASSWORD=your_password
DB_URL=sqlite+aiosqlite:///myride.db
LOG_LEVEL=INFO
WEB_HOST=0.0.0.0
WEB_PORT=8080
```

---

## Running the Service

All commands are run using `main.py`:

### Start Daemon & Web Dashboard
Starts the background daemon (checking the Mon-Fri 7:45 AM - 8:50 AM ET schedule) and launches the Web Dashboard at **`http://localhost:8080`**:

```bash
python main.py run
```

> **Tip**: To test WebSocket streaming outside of active school bus hours, pass `--ignore-schedule`:
> ```bash
> python main.py run --ignore-schedule
> ```

### Start Web Server Standalone
Runs only the web dashboard HTTP server:

```bash
python main.py web --port 8080
```

---

## Automated Test Suite

Run the full pytest suite (15 unit and integration tests):

```bash
pytest -v tests/
```

---

## Synology NAS / Docker Deployment

When deploying to Synology NAS via Docker Container Manager:

```bash
docker-compose up -d --build
```
