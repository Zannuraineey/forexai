# Forex AI Market Analysis Platform

An institutional-grade, full-stack **Forex & Synthetic Indices AI Market Analysis Platform** built for high-probability trade detection, deterministic Smart Money Concepts (SMC) execution, automated non-repainting UT Bot confirmation, and real-time trade lifecycle push alerts.

---

## 📑 Table of Contents
1. [Architecture Overview](#-architecture-overview)
2. [Core Engines & Strategy Features](#-core-engines--strategy-features)
   - [Smart Money Concepts (SMC) & ICT Engine](#1-smart-money-concepts-smc--ict-engine)
   - [Non-Repainting UT Bot Engine](#2-non-repainting-ut-bot-engine)
   - [Structured Actionable Trade Tickets & 3-Tier Scaling](#3-structured-actionable-trade-tickets--3-tier-scaling)
   - [Trade Lifecycle Tracker & Milestones](#4-trade-lifecycle-tracker--milestones)
   - [Macro News Intelligence & DXY Engine](#5-macro-news-intelligence--dxy-engine)
   - [High-Priority Push Alerts (FCM)](#6-high-priority-push-alerts-fcm)
3. [Repository Structure](#-repository-structure)
4. [Prerequisites & Toolchain](#-prerequisites--toolchain)
5. [Step-by-Step Setup Guide](#-step-by-step-setup-guide)
   - [Step 1: Clone Repository](#step-1-clone-repository)
   - [Step 2: Firebase Project & Service Account Setup](#step-2-firebase-project--service-account-setup)
   - [Step 3: Deriv Market Data API Setup](#step-3-deriv-market-data-api-setup)
   - [Step 4: Backend Configuration & Local Run](#step-4-backend-configuration--local-run)
   - [Step 5: Database Setup & Migrations](#step-5-database-setup--migrations)
   - [Step 6: Frontend (Flutter) Configuration & Run](#step-6-frontend-flutter-configuration--run)
6. [Cloud Deployment (Railway & Render)](#-cloud-deployment-railway--render)
   - [Deploying to Railway](#deploying-to-railway)
   - [Deploying to Render](#deploying-to-render)
7. [API Reference & Testing Checklist](#-api-reference--testing-checklist)
8. [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 🏛️ Architecture Overview

```
                      ┌──────────────────────────────────────┐
                      │    Deriv WebSocket Ingestion API     │
                      │ (Forex Majors + Synthetic Vol 75/..) │
                      └──────────────────┬───────────────────┘
                                         │ Live Candles & Ticks
                                         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND ENGINE                           │
│                                                                            │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌────────────────┐  │
│  │    SMC / ICT Engine   │  │     UT Bot Engine     │  │ News Intel/DXY │  │
│  │ (Sweeps, MSS, OB, FVG)│  │ (ATR Trailing, 200 EMA│  │(Macro Events,  │  │
│  │  Session Killzones    │  │  14 RSI, Closed Bar)  │  │ Currency Bias) │  │
│  └───────────┬───────────┘  └───────────┬───────────┘  └───────┬────────┘  │
│              └─────────────────────┐    │    ┌─────────────────┘           │
│                                    ▼    ▼    ▼                             │
│                      ┌─────────────────────────────────┐                   │
│                      │   Deterministic AI Reasoning    │                   │
│                      │  - Structured Trade Tickets     │                   │
│                      │  - 3-Tier Scaling (1.5R/3R/5R)  │                   │
│                      │  - Invalidation Rules & Checks  │                   │
│                      └────────────────┬────────────────┘                   │
│                                       ▼                                    │
│                      ┌─────────────────────────────────┐                   │
│                      │   Trade Lifecycle & Alerts      │                   │
│                      │  - Milestone Event Dispatcher   │                   │
│                      │  - Anti-Spam (15m Cooldown)     │                   │
│                      │  - Background Scanner (45s)     │                   │
│                      └────────────────┬────────────────┘                   │
│                                       │                                    │
│   ┌───────────────────────────────────┴────────────────────────────────┐   │
│   │ Async PostgreSQL (asyncpg) / SQLite Local Storage + Firebase Admin │   │
│   └───────────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────────┼────────────────────────────────────┘
                                        │ High-Priority Push Alerts & REST APIs
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       FLUTTER MOBILE CLIENT (iOS / Android)                │
│                                                                            │
│  - Dark Financial Terminal UI (Emerald/Slate Palette)                      │
│  - Actionable Trade Ticket Card with 1-Click "COPY ALL" Clipboard         │
│  - Live Candle Charts with SMC Overlays & UT Bot Signals                   │
│  - Foreground Alert Banners & Direct Notification Deep-Linking             │
│  - In-App Lifecycle Milestone Triggers (Filled, TP1 BE, TP2, SL, Cancel)   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Engines & Strategy Features

### 1. Smart Money Concepts (SMC) & ICT Engine
- **Session Killzones**:
  - **Asian Session**: 00:00 - 08:00 UTC (Tokyo/Sydney range builder).
  - **London Open Killzone**: 07:00 - 10:00 UTC (European expansion / Judas swing).
  - **New York Open Killzone**: 12:00 - 15:00 UTC (US session expansion).
  - **NYSE Cash Open / Judas Window**: 13:30 - 14:30 UTC.
  - **London Close Killzone**: 15:00 - 17:00 UTC (Counter-trend rebalancing).
- **Liquidity Sweeps**: Identifies institutional stops run above Session Highs (`BSL - Buy-Side Liquidity`) and below Session Lows (`SSL - Sell-Side Liquidity`).
- **Market Structure Shift (MSS)**: Validates character change (CHoCH) on closed candles.
- **Fair Value Gaps (FVG) & Order Blocks (OB)**: High-probability entry zones matching directional flow.

### 2. Non-Repainting UT Bot Engine
- **Mathematical Non-Repainting Guarantee**: Evaluates strictly closed bars (`is_complete=True`). No tick-level signal flickering.
- **Dynamic ATR Trailing Stop**: Trailing key sensitivity value configured per asset class (Forex vs. Synthetic Volatility indices).
- **200 EMA Macro Filter**:
  - `BUY` signals require candle close strictly above 200 EMA.
  - `SELL` signals require candle close strictly below 200 EMA.
- **14 RSI Momentum Filter**: Guards against exhausted market conditions (`RSI < 70` for longs, `RSI > 30` for shorts).

### 3. Structured Actionable Trade Tickets & 3-Tier Scaling
Every validated setup outputs a mathematical, unambiguous execution plan:
- **Order Type**: Explicit `BUY LIMIT` or `SELL LIMIT`.
- **Execution Geometry**:
  - `Entry Price`: Limit order at optimal institutional mitigation zone.
  - `Stop Loss`: Protected beyond sweep high/low with dynamic ATR buffer.
  - `Risk`: Measured in pips/points.
- **3-Tier Scaling Blueprint**:
  - **TP1**: `1.5R` (Banks 50% position; moves Stop Loss to Breakeven).
  - **TP2**: `3.0R` (Banks 30% position; primary objective).
  - **TP3**: `5.0R` (Leaves 20% runner for macro trend expansion).
- **1-Click "COPY ALL"**: Copies clean broker-ready text to clipboard:
  ```text
  XAUUSD | BUY LIMIT
  Entry: 2650.50
  SL: 2642.10
  TP1: 2663.10 (+1.5R -> Move SL to BE)
  TP2: 2675.70 (+3.0R)
  TP3: 2692.50 (+5.0R)
  ```

### 4. Trade Lifecycle Tracker & Milestones
Tracks open setups from generation through completion:
1. `ENTRY_FILLED`: Order active at limit level.
2. `TP1_HIT_MOVE_TO_BE`: First target reached; push alert commands trader to secure 50% and move Stop Loss to Breakeven.
3. `TP2_HIT`: Primary objective secured.
4. `TP3_HIT`: Runner target reached.
5. `SL_HIT`: Invalidation reached; risk capped.
6. `SETUP_CANCELLED`: Front-run detector alerts if price hits TP1 before filling Entry.

### 5. Macro News Intelligence & DXY Engine
- Real-time economic calendar tracking (US, UK, EUR, JPY high-impact releases).
- **Dollar Index (DXY) Correlation Matrix**: Evaluates inverse decoupling between USD, Gold (XAUUSD), and major pairs.
- Automated 60-minute countdown warnings before major central bank rate decisions, CPI, and NFP releases.

### 6. High-Priority Push Alerts (FCM)
- Background scanner executes automated cycles across watchlist pairs every 45 seconds.
- 15-minute deduplication cooldown prevents spamming identical setups.
- Custom notification sound and emerald LED/branding icon on Android (`forex_ai_high_importance` channel).
- Tapping an alert deep-links directly to the asset's active trade ticket in the app.

---

## 📁 Repository Structure

```
forex-ai-platform/
├── Dockerfile                     # Root Dockerfile for Railway & cloud monorepo deployments
├── railway.json                   # Railway deployment configuration (Docker builder + health check)
├── render.yaml                    # Render Infrastructure as Code configuration
├── apps.md                        # UI/UX design specifications & color palette tokens
│
├── backend/                       # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint, lifespan startup/shutdown, routers
│   │   ├── api/                   # REST API routes
│   │   │   ├── analysis.py        # /analysis/run, /analysis/lifecycle-event, /analysis/latest
│   │   │   ├── candles.py         # /candles/query, /candles/ingest
│   │   │   ├── health.py          # /health (Liveness & readiness probe)
│   │   │   ├── instruments.py     # /instruments (Watchlist & catalog)
│   │   │   ├── market_context.py  # /market-context (Technical summary)
│   │   │   ├── news.py            # /news/events, /news/intelligence
│   │   │   ├── notifications.py   # /notifications/devices, /notifications/test
│   │   │   ├── sessions.py        # /sessions/current, /sessions/levels
│   │   │   └── strategy.py        # /strategy/evaluate, /strategy/ut-bot
│   │   ├── core/                  # Engine settings, DB engine, and migrations
│   │   │   ├── config.py          # Pydantic Settings & environment variables
│   │   │   └── database.py        # SQLAlchemy AsyncSession & auto-migrations
│   │   ├── models/                # SQLAlchemy database models
│   │   │   ├── analysis.py        # AnalysisResult (with JSON trade_setup)
│   │   │   ├── candle.py          # Candle
│   │   │   ├── instrument.py      # Instrument
│   │   │   └── notification.py    # RegisteredDevice, NotificationLog
│   │   ├── schemas/               # Pydantic schemas (Serialization & validation)
│   │   │   ├── ai_analysis.py     # TradeSetup, TradeTarget, InvalidationRule
│   │   │   ├── candle.py          # CandleDTO, CandleRead
│   │   │   └── notification.py    # DeviceRegistrationRequest, NotificationRead
│   │   └── services/              # Business logic & trading engines
│   │       ├── ai/                # DeterministicProvider, AIAnalysisEngine, UTBotEngine
│   │       ├── market_data/       # Deriv WebSocket Client & symbol catalog
│   │       ├── news/              # LiveNewsService, DXYService, NewsIntelligenceEngine
│   │       ├── notifications/     # NotificationService (Firebase Admin SDK), Scanner
│   │       └── session/           # SessionEngine (Asian, London, NY Killzones)
│   ├── tests/                     # Comprehensive pytest test suite
│   ├── Dockerfile                 # Backend-scoped Dockerfile (for Render)
│   ├── railway.json               # Backend-scoped Railway config
│   └── requirements.txt           # Python production dependencies
│
└── frontend/                      # Flutter Cross-Platform Client
    ├── android/                   # Native Android wrapper
    │   ├── app/
    │   │   ├── src/main/AndroidManifest.xml  # Permissions, FCM channels, metadata
    │   │   └── build.gradle       # Google Services plugin configuration
    │   └── build.gradle           # Root Gradle configuration
    ├── ios/                       # Native iOS wrapper
    ├── lib/                       # Flutter Dart Source Code
    │   ├── main.dart              # App entrypoint, FCM init, deep link router, alert banner
    │   ├── models/                # Typed Dart models (AiAnalysis, TradeSetup, Candle, News)
    │   ├── screens/               # Mobile UI Screens
    │   │   ├── markets_screen.dart    # Live market watchlist & session pill status
    │   │   ├── analysis_screen.dart   # Interactive Chart, Trade Ticket Card, SMC breakdown
    │   │   ├── news_screen.dart       # Macro economic calendar & DXY intelligence
    │   │   ├── alerts_screen.dart     # Push notification history & setup quick-view
    │   │   └── settings_screen.dart   # Strategy thresholds, test push button, server URL
    │   ├── services/              # API Client (Resilient retry, caching, FCM registration)
    │   └── widgets/               # Reusable trading widgets, bottom sheets, SVG icons
    └── pubspec.yaml               # Flutter package dependencies
```

---

## 🧰 Prerequisites & Toolchain

Ensure the following tools are installed on your workstation before starting:

| Tool | Recommended Version | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.11.x` or `3.12.x` | Backend runtime |
| **Flutter SDK** | `3.22.x` or higher | Frontend mobile framework |
| **Dart SDK** | `3.4.x` or higher | Included with Flutter SDK |
| **Android Studio / SDK** | API 34+ | Android emulation & APK compilation |
| **Git** | Latest | Version control |
| **Docker** *(Optional)* | Latest | Local containerized testing |
| **Deriv Account** | Free demo/live | Real-time market data WebSocket |
| **Firebase Account** | Free Spark plan | FCM push notification service |

---

## 🛠️ Step-by-Step Setup Guide

### Step 1: Clone Repository

```bash
git clone https://github.com/Zannuraineey/forexai.git
cd forexai
```

---

### Step 2: Firebase Project & Service Account Setup

Push notifications rely on Firebase Cloud Messaging (FCM).

#### A. Create Firebase Project
1. Navigate to the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** and name it `forex-ai-platform`.
3. Enable or disable Google Analytics as desired and create the project.

#### B. Setup Android Client in Firebase
1. In your Firebase project overview, click the **Android** icon.
2. Enter the Android package name:
   ```text
   com.forexai.platform
   ```
3. Set the App nickname to `Forex AI`.
4. Click **Register app**.
5. Download `google-services.json`.
6. Move the downloaded file into your frontend directory:
   ```bash
   # Place here:
   frontend/android/app/google-services.json
   ```

#### C. Generate Backend Service Account Key
1. In the Firebase Console, go to **Project settings** (gear icon) -> **Service accounts**.
2. Click **Generate new private key**, then click **Generate key**.
3. A JSON file will be downloaded (e.g., `forex-ai-platform-firebase-adminsdk-xxx.json`).
4. You can provide this to the backend in one of three ways:
   - **Method 1 (File Path - Local Dev)**: Save the file as `backend/firebase-service-account.json`.
   - **Method 2 (Raw JSON string - Cloud Env)**: Copy the entire file content into an environment variable `FIREBASE_SERVICE_ACCOUNT_JSON`.
   - **Method 3 (Base64 string - Railway/Docker)**:
     ```bash
     # Linux / macOS:
     base64 -w 0 firebase-service-account.json
     # Windows PowerShell:
     [Convert]::ToBase64String([IO.File]::ReadAllBytes("firebase-service-account.json"))
     ```
     Set the output string to the environment variable `FIREBASE_SERVICE_ACCOUNT_BASE64`.

---

### Step 3: Deriv Market Data API Setup

The platform ingests real-time candles for Forex pairs (`EURUSD`, `GBPUSD`, `XAUUSD`) and synthetic indices (`R_75`, `BOOM1000`, `CRASH1000`) via Deriv's low-latency WebSocket API.

1. Create a free account at [Deriv.com](https://deriv.com).
2. Go to **Account Settings** -> **API Token**.
3. Create a token with **Read** scope and name it `ForexAI_Read`.
4. Register a free App ID at [Deriv API Registration](https://api.deriv.com) (or use the default public testing App ID `1089`).
5. Keep your `DERIV_APP_ID` and `DERIV_API_TOKEN` ready for your `.env` file.

---

### Step 4: Backend Configuration & Local Run

#### A. Create Python Virtual Environment
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

#### B. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### C. Create `.env` Environment File
Create a `.env` file inside the `backend/` directory:

```env
# Application Settings
PROJECT_NAME="Forex AI Market Analysis Platform"
ENVIRONMENT="development"
DEBUG=True
LOG_LEVEL="INFO"

# Database Configuration
# Local SQLite fallback:
DATABASE_URL="sqlite+aiosqlite:///./forex_ai.db"
# Or Local PostgreSQL:
# DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/forex_ai"

# Market Data (Deriv WebSocket)
DERIV_APP_ID="1089"
DERIV_WS_URL="wss://api.derivws.com/trading/v1/options/ws/public"
DERIV_API_TOKEN="your_deriv_api_token_here"

# Firebase Credentials (choose path or raw JSON)
FIREBASE_SERVICE_ACCOUNT_PATH="firebase-service-account.json"
# Or:
# FIREBASE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
# FIREBASE_SERVICE_ACCOUNT_BASE64="eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIs..."

# AI Reasoning Configuration (Optional - uses Deterministic SMC Engine by default)
AI_MODEL_NAME="gemini-1.5-flash"
GEMINI_API_KEY=""
AI_API_KEY=""
```

#### D. Run the Backend Server
```bash
# From the backend/ folder:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify your backend is alive:
- Open your browser or run: `curl http://localhost:8000/health`
- Expected response: `{"status":"ok","database":"connected","deriv_ws":"connected",...}`
- Interactive API Docs: `http://localhost:8000/docs`

#### E. Execute Backend Test Suite
```bash
python -m pytest tests/test_setup_mathematics.py tests/test_notifications.py
# Run complete test suite:
python -m pytest tests/
```

---

### Step 5: Database Setup & Migrations

The database layer automatically initializes required tables and runs schema additions on startup (`init_db()` in `app/core/database.py`):
- `instruments`: Supported trading pairs and symbols.
- `candles`: OHLCV candlestick records with unique constraints `(instrument_id, timeframe, timestamp_utc)`.
- `analysis_results`: Generated trade setups, SMC structure, and JSON `trade_setup` tickets.
- `registered_devices`: FCM mobile push tokens and notification rules.
- `notification_logs`: Historical audit trail of dispatched push alerts.

> **Production Note**: In production (Railway/Render), connect a managed PostgreSQL database by passing `DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname`.

---

### Step 6: Frontend (Flutter) Configuration & Run

#### A. Install Flutter Dependencies
```bash
# Navigate to frontend directory
cd ../frontend

# Fetch Dart dependencies
flutter pub get
```

#### B. Configure Backend URL
Open `frontend/lib/services/api_service.dart` and verify or set `baseUrl`:
- **Android Physical Device via USB**: Set your PC's local Wi-Fi IP address (e.g., `http://192.168.1.100:8000`) or your live Railway URL.
- **Android Emulator**: Use `http://10.0.2.2:8000`.
- **Production Server**: Use your Railway or Render URL:
  ```dart
  static String baseUrl = 'https://forexai.up.railway.app';
  ```

#### C. Run the Flutter App
Ensure your Android device has **USB Debugging** enabled or launch an Android emulator:

```bash
# Check connected devices
flutter devices

# Run in debug mode
flutter run
```

---

## ☁️ Cloud Deployment (Railway & Render)

This repository is monorepo-ready with zero-config build detection for both Railway and Render.

### Deploying to Railway

Railway detects [`railway.json`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/railway.json) and the root [`Dockerfile`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/Dockerfile) automatically.

1. Fork or push this repository to your GitHub account.
2. In [Railway.app](https://railway.com), click **New Project** -> **Deploy from GitHub repo**.
3. Select `forexai`.
4. Add a **PostgreSQL** database service in the same project:
   - Click **+ New** -> **Database** -> **Add PostgreSQL**.
5. In your `forex-ai-backend` service settings, add the following Environment Variables:
   - `DATABASE_URL`: `${{Postgres.DATABASE_URL}}` (Reference the Railway Postgres service).
   - `DERIV_APP_ID`: `1089` (or your custom App ID).
   - `DERIV_API_TOKEN`: Your Deriv API token.
   - `FIREBASE_SERVICE_ACCOUNT_BASE64`: Paste your base64-encoded Firebase service account JSON.
   - `LOG_LEVEL`: `INFO`
6. Railway will automatically build and deploy. The service will be exposed via a public URL such as `https://forexai.up.railway.app`.

### Deploying to Render

Render reads [`render.yaml`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/render.yaml) from the repository root:

1. Create a new **Blueprint** project on [Render.com](https://render.com).
2. Connect your repository. Render will automatically spin up:
   - A PostgreSQL database (`forex-ai-postgres`).
   - A Docker web service (`forex-ai-backend`) pointing to `backend/Dockerfile` with context `backend`.
3. Add your secret environment variables (`DERIV_API_TOKEN`, `FIREBASE_SERVICE_ACCOUNT_JSON`) in the Render Dashboard.

---

## 📡 API Reference & Testing Checklist

### Key Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Healthcheck and connection status probe |
| `GET` | `/api/v1/instruments` | Get all active Forex and synthetic pairs |
| `GET` | `/api/v1/candles/query?symbol=XAUUSD&timeframe=15m` | Fetch stored OHLCV candles |
| `GET` | `/api/v1/sessions/current` | Get active Killzones (Asian, London, NY) |
| `POST` | `/api/v1/analysis/run` | Trigger on-demand SMC + UT Bot AI analysis |
| `GET` | `/api/v1/analysis/latest/{symbol}` | Retrieve latest actionable trade ticket |
| `POST` | `/api/v1/analysis/lifecycle-event` | Report trade lifecycle state change |
| `POST` | `/api/v1/notifications/devices` | Register mobile FCM token |
| `POST` | `/api/v1/notifications/test` | Trigger a test push notification |
| `GET` | `/api/v1/news/events` | Fetch macroeconomic calendar events |
| `POST` | `/api/v1/news/intelligence` | Generate macro DXY correlation analysis |

### Testing Lifecycle Workflow

You can test a complete trade lifecycle using `curl`:

```bash
# 1. Trigger an on-demand analysis
curl -X POST "http://localhost:8000/api/v1/analysis/run" \
     -H "Content-Type: application/json" \
     -d '{"symbol": "XAUUSD", "timeframe": "15m"}'

# 2. Report Entry Filled milestone
curl -X POST "http://localhost:8000/api/v1/analysis/lifecycle-event" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "XAUUSD",
       "event": "ENTRY_FILLED",
       "price": 2650.50,
       "timestamp_utc": "2026-10-08T12:00:00Z"
     }'

# 3. Report TP1 Reached (Commands Move to Breakeven)
curl -X POST "http://localhost:8000/api/v1/analysis/lifecycle-event" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "XAUUSD",
       "event": "TP1_HIT_MOVE_TO_BE",
       "price": 2663.10,
       "timestamp_utc": "2026-10-08T12:30:00Z"
     }'
```

---

## ❓ Troubleshooting & FAQs

### 1. `Lost connection to device` during `flutter run`
- **Cause**: Android OS power management put the USB connection to sleep, or the USB cable is loose.
- **Fix**:
  1. On your Android phone, enable **Developer options** -> toggle **Stay awake while charging**.
  2. Under Developer options -> **Default USB configuration**, select **File transfer / Android Auto** instead of "Charge only".
  3. Run `adb kill-server && adb start-server` and verify with `adb devices`.

### 2. `NameError: name 'Any' is not defined`
- **Cause**: In Python 3.11, type annotations are evaluated at runtime upon module import. If `Any` is used in a type hint (e.g., `Dict[str, Any]`), it must be imported from `typing`.
- **Fix**: Ensure `from typing import Any, Dict, List, Optional, Tuple` is present at the top of the file.

### 3. Railway `Deployment failed to build [10]`
- **Cause**: Railway defaulted to Nixpacks at the repository root because it didn't find `package.json` or `requirements.txt` at `/`.
- **Fix**: The repository includes a root `Dockerfile` and `railway.json` with `"builder": "DOCKERFILE"` so Railway builds the backend seamlessly without manual path adjustments.

### 4. Push notifications not received on device
- **Checklist**:
  1. Verify `google-services.json` is located in `frontend/android/app/`.
  2. Verify your backend log shows `Initialized Firebase Admin SDK from...`.
  3. Ensure Android 13+ notification permissions are granted (the app requests this automatically on first launch).
  4. Test sending a test notification via `POST /api/v1/notifications/test`.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
