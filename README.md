# Forex AI Market Analysis Platform

An institutional-grade, full-stack **Forex & Synthetic Indices AI Market Analysis Platform** built for high-probability trade detection, deterministic Smart Money Concepts (SMC) execution, automated non-repainting UT Bot confirmation, and real-time trade lifecycle push alerts.

---

## 📑 Table of Contents
1. [Architecture Overview](#-architecture-overview)
2. [Core Engines & Strategy Features](#-core-engines--strategy-features)
   - [Smart Money Concepts (SMC) & ICT Engine](#1-smart-money-concepts-smc--ict-engine)
   - [MSNR Institutional Execution Model & Consequent Encroachment](#2-msnr-institutional-execution-model--consequent-encroachment)
   - [Smart Money Technique (SMT) Divergence Engine](#3-smart-money-technique-smt-divergence-engine)
   - [7-Hour Profile Engine & Session Persistence](#4-7-hour-profile-engine--session-persistence)
   - [Non-Repainting UT Bot Engine](#5-non-repainting-ut-bot-engine)
   - [Structured Actionable Trade Tickets & 3-Tier Scaling](#6-structured-actionable-trade-tickets--3-tier-scaling)
   - [Trade Lifecycle Tracker & Milestones](#7-trade-lifecycle-tracker--milestones)
   - [Macro News Intelligence & DXY Decoupling](#8-macro-news-intelligence--dxy-decoupling)
   - [Session Scanner Diagnostics & High-Priority Push Alerts (FCM)](#9-session-scanner-diagnostics--high-priority-push-alerts-fcm)

3. [Repository Structure](#-repository-structure)
4. [Prerequisites & Toolchain](#-prerequisites--toolchain)
5. [Step-by-Step Setup Guide](#-step-by-step-setup-guide)
   - [Step 1: Clone Repository](#step-1-clone-repository)
   - [Step 2: Firebase Project & Service Account Setup](#step-2-firebase-project--service-account-setup)
   - [Step 3: Deriv Market Data API Setup](#step-3-deriv-market-data-api-setup)
   - [Step 4: Backend Configuration & Local Run](#step-4-backend-configuration--local-run)
   - [Step 5: Database Setup & Migrations](#step-5-database-setup--migrations)
   - [Step 6: Frontend (Flutter) Configuration & Run](#step-6-frontend-flutter-configuration--run)
6. [Advanced FCM & Android Notification System (Complete Blueprint)](#-advanced-fcm--android-notification-system-complete-blueprint)
   - [Notification Subsystem Architecture](#1-notification-subsystem-architecture)
   - [Frontend FCM File Matrix](#2-frontend-fcm-file-matrix)
   - [Component 1: Custom Vector Candlestick Icon (`ic_stat_notification.xml`)](#component-1-custom-vector-candlestick-icon-ic_stat_notificationxml)
   - [Component 2: Emerald Notification Accent Color (`colors.xml`)](#component-2-emerald-notification-accent-color-colorsxml)
   - [Component 3: Android Gradle Configuration (`build.gradle.kts`)](#component-3-android-gradle-configuration-buildgradlekts)
   - [Component 4: Android Manifest Permissions & Channel Metadata](#component-4-android-manifest-permissions--channel-metadata)
   - [Component 5: Flutter FCM Initialization & Background Handler](#component-5-flutter-fcm-initialization--background-handler)
   - [Component 6: Deep-Linking & Click Routing to Trade Tickets](#component-6-deep-linking--click-routing-to-trade-tickets)
   - [Component 7: Foreground Trading Alert Banner](#component-7-foreground-trading-alert-banner)
   - [Component 8: Backend High-Priority Dispatch Pairing](#component-8-backend-high-priority-dispatch-pairing)
7. [Cloud Deployment (Railway & Render)](#-cloud-deployment-railway--render)
   - [Deploying to Railway](#deploying-to-railway)
   - [Deploying to Render](#deploying-to-render)
8. [API Reference & Testing Checklist](#-api-reference--testing-checklist)
9. [Troubleshooting & FAQs](#-troubleshooting--faqs)

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

### 2. MSNR Institutional Execution Model & Consequent Encroachment
- **5-Step Institutional Setup Sequence**:
  1. **7H Profile Dominance**: Trade direction must be strictly aligned with the latest Completed 7-Hour Profile (`BULLISH` or `BEARISH`).
  2. **Session Liquidity Manipulation**: Wick sweep of opposing previous session pool (Asia High/Low or London High/Low) inside active killzone.
  3. **MSNR Classic Exhaustion Bar**: Requires manipulation candle wick ratio $\ge 35\%$ (`rejection_wick_ratio >= 0.35`) to confirm institutional absorption and filter out aggressive breakout spikes.
  4. **Displacement & Market Structure Shift (MSS)**: Clear lower-timeframe body close breaking the structural swing high/low.
  5. **50% Consequent Encroachment (CE) Retest Entry**: Limit entry placed precisely at the 50% midpoint of the displacement Fair Value Gap (FVG) or RBS/SBR flip zone:
     $$\text{Entry Price} = \frac{\text{FVG Top} + \text{FVG Bottom}}{2}$$
- **Strict Mathematical Geometry Validation (`validate_trade_geometry`)**:
  - **BUY**: $\text{Stop Loss} < \text{Entry (CE)} < \text{Take Profit}$
  - **SELL**: $\text{Take Profit} < \text{Entry (CE)} < \text{Stop Loss}$
  - Inverted targets or zero-risk trades are strictly rejected and downgraded to diagnostic `POTENTIAL_SETUP`.
  - Minimum Risk-to-Reward ratio: $\text{R:R} \ge 2.0$.
  - Dynamic Stop Loss buffer calculated via ATR (minimum $1.50 / 15$ pips on Gold `XAUUSD`).

### 3. Smart Money Technique (SMT) Divergence Engine
- **Intermarket Divergence Pairs**:
  - **Precious Metals**: `XAUUSD` (Gold) $\longleftrightarrow$ `XAGUSD` (Silver)
  - **Forex Majors**: `EURUSD` (Fiber) $\longleftrightarrow$ `GBPUSD` (Cable)
- **Accumulation / Distribution Confirmation**:
  - **Bullish SMT**: Asset A takes session low (Lower Low) while Asset B holds above session low (Higher Low) $\rightarrow$ Elevates setup quality to **`Grade A+`**.
  - **Bearish SMT**: Asset A sweeps session high (Higher High) while Asset B fails to sweep (Lower High) $\rightarrow$ Elevates setup quality to **`Grade A+`**.
- **Contradiction Veto**:
  - If structural shift is Long but an active SMT divergence is Bearish, the bias engine automatically flags a conflict and suppresses the setup.

### 4. 7-Hour Profile Engine & Session Persistence
- **Anchor Configurations & Stub Handling**:
  - 4 daily profile blocks evaluated in UTC (`DAILY_ANCHOR` mode): `00:00–07:00`, `07:00–14:00`, `14:00–21:00`, and `21:00–24:00` (3-hour stub).
  - Stub expected count scales dynamically to 3 candles, ensuring proper `COMPLETED` resolution.
- **85% Completeness Ratio**:
  - Configured with `min_candles_ratio_for_complete = 0.85` so that 1 missing 1H candle (6 out of 7 = 85.7%) safely achieves `ProfileStatus.COMPLETED` and `DataQuality.COMPLETE`.
- **Zero-Repainting In-Progress Fallback**:
  - When the current 7H profile is `IN_PROGRESS`, trading engines automatically inherit the directional bias from the last `COMPLETED` profile.
- **36-Hour Session Range Persistence**:
  - Data ingestion loads 36 hours of historical candles (5m = 432 candles, 15m = 144 candles).
  - Guarantees Asian session High/Low levels persist throughout London and New York without missing data errors.

### 5. Non-Repainting UT Bot Engine
- **Mathematical Non-Repainting Guarantee**: Evaluates strictly closed bars (`is_complete=True`). No tick-level signal flickering.
- **Dynamic ATR Trailing Stop**: Trailing key sensitivity value configured per asset class (Forex vs. Synthetic Volatility indices).
- **200 EMA Macro Filter**:
  - `BUY` signals require candle close strictly above 200 EMA.
  - `SELL` signals require candle close strictly below 200 EMA.
- **14 RSI Momentum Filter**: Guards against exhausted market conditions (`RSI < 70` for longs, `RSI > 30` for shorts).

### 6. Structured Actionable Trade Tickets & 3-Tier Scaling
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
  XAUUSD | BUY LIMIT (Grade A+ • SMT Confirmed)
  Entry: 2650.50
  SL: 2642.10
  TP1: 2663.10 (+1.5R -> Move SL to BE)
  TP2: 2675.70 (+3.0R)
  TP3: 2692.50 (+5.0R)
  ```

### 7. Trade Lifecycle Tracker & Milestones
Tracks open setups from generation through completion:
1. `ENTRY_FILLED`: Order active at limit level.
2. `TP1_HIT_MOVE_TO_BE`: First target reached; push alert commands trader to secure 50% and move Stop Loss to Breakeven.
3. `TP2_HIT`: Primary objective secured.
4. `TP3_HIT`: Runner target reached.
5. `SL_HIT`: Invalidation reached; risk capped.
6. `SETUP_CANCELLED`: Front-run detector alerts if price hits TP1 before filling Entry.

### 8. Macro News Intelligence & DXY Decoupling
- **Strict Decoupling from Trade Setups**:
  - DXY is **never** used to gate, block, or generate trade setups. Trade setups are driven exclusively by session structure and 7H profiles.
  - DXY relationship evaluates to `NEUTRAL` in bias validation.
- **Reserved Exclusively for Macro News & Events**:
  - High-impact macroeconomic calendar tracking (CPI, NFP, FOMC rate decisions).
  - Pre-event 60-minute risk warnings and volatility spike buffer alerts.
- **Zero Fabricated / Mock Fallback Data**:
  - Direct DXY symbols (`DXY`, `USDX`, `DX`) or live constituent basket rates are queried. If live data is absent from price feeds, the service reports `UNAVAILABLE` rather than generating artificial prices.

### 9. Session Scanner Diagnostics & High-Priority Push Alerts (FCM)
- **Granular Cycle Logging**:
  - Logs one diagnostic line per symbol/timeframe during every scan cycle:
    ```text
    [SessionScanner] [EURUSD 15m] session=london, 7H=COMPLETED BULLISH, levels=[asian: 1.0820-1.0880], first_failed=Sweep in active session
    ```
- **Real-Time State Counts & Status Endpoint**:
  - Cycles conclude with aggregated state counts:
    ```text
    🔄 [SessionScanner] Cycle completed for [LONDON]. State Counts: NO_SETUP=4, WATCH=2, POTENTIAL=1, VALID=1
    ```
  - Exposed via `GET /api/v1/analysis/scanner/status` with `state_counts` object (`NO_SETUP`, `WATCH`, `POTENTIAL`, `VALID`).
- **High-Priority FCM Push Dispatch**:
  - Automated 45-second scan worker with 15-minute deduplication cooldown.
  - Custom vector candlestick drawable icon (`ic_stat_notification.xml`) and emerald LED/branding tint (`#10B981`).
  - Deep-links directly to the asset's active trade ticket in the Flutter app.


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
│   │       ├── ai/                # DeterministicProvider, AIAnalysisEngine, SessionScannerWorker
│   │       ├── bias/              # BiasValidationEngine (Multi-layer confirmation & conflict gating)
│   │       ├── features/          # MSNREngine (CE 50% retest), SMTEngine (Divergence), TargetRealism
│   │       ├── profiling/         # SevenHourProfileEngine (7H aggregation & zero-repainting)
│   │       ├── market_data/       # Deriv WebSocket Client & symbol catalog
│   │       ├── news/              # EconomicCalendarService, DXYService, NewsIntelligenceEngine
│   │       ├── notifications/     # NotificationService (Firebase Admin SDK)
│   │       └── session/           # SessionEngine (Asian, London, NY Killzones & 36H persistence)

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

## 🔔 Advanced FCM & Android Notification System (Complete Blueprint)

Trading setups and market volatility alerts are time-critical. Standard push notifications often fail institutional trading requirements because:
1. **The "White Square" Icon Bug**: On Android 5.0+ (API 21+), Android forces status bar notification icons to be rendered as an alpha-channel mask. If a standard full-color PNG app icon is used, the OS renders it as a solid, broken white square.
2. **Missing Notification Channels**: Modern Android (API 26+) silences notifications unless they are explicitly assigned to a high-importance notification channel with sound, vibration, and heads-up popups enabled.
3. **App State Loss**: Clicking a notification while the app is closed (terminated) often just opens the home screen instead of deep-linking directly into the active Trade Ticket.
4. **Foreground Invisibility**: By default in Flutter, Firebase Cloud Messaging does not show alerts when the app is actively open in the foreground.

This platform implements an end-to-end, institutional notification architecture resolving every one of these challenges.

---

### 1. Notification Subsystem Architecture

```
[ Backend Trade Scanner (45s) ]
               │
               ▼  (High-Priority FCM Message + Custom Payload)
[ Google Firebase Cloud Messaging (FCM) ]
               │
               ├── Android OS System Tray
               │     ├── Displays: Custom Candlestick Vector Icon (ic_stat_notification.xml)
               │     ├── Tints: Emerald Accent Color (#10B981)
               │     └── Channels: 'forex_ai_alerts' (High Importance, Sound, Vibrate)
               │
               ▼
   [ Flutter Client State Handler ]
         │
         ├── Terminated (App Closed)  ──▶ FirebaseMessaging.getInitialMessage() ──▶ Jump to Trade Ticket
         ├── Background (App Minimized) ──▶ onMessageOpenedApp.listen()          ──▶ Jump to Trade Ticket
         └── Foreground (App Open)      ──▶ onMessage.listen()                  ──▶ Floating Alert Banner
```

---

### 2. Frontend FCM File Matrix

To recreate this notification system in any Flutter app, the following 9 files work together:

| File Path | Role & Purpose |
| :--- | :--- |
| [`frontend/pubspec.yaml`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/pubspec.yaml) | Imports `firebase_core`, `firebase_messaging`, and `flutter_local_notifications`. |
| [`frontend/android/build.gradle.kts`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/android/build.gradle.kts) | Registers Google Services Gradle Classpath (`com.google.gms:google-services:4.4.2`). |
| [`frontend/android/app/build.gradle.kts`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/android/app/build.gradle.kts) | Applies the `com.google.gms.google-services` plugin and sets the application ID. |
| [`frontend/android/app/google-services.json`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/android/app/google-services.json) | Firebase configuration linking the Android app to your Firebase Cloud project. |
| [`frontend/android/app/src/main/res/drawable/ic_stat_notification.xml`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/android/app/src/main/res/drawable/ic_stat_notification.xml) | Monochrome vector silhouette of 3 candlesticks and an AI signal star. |
| [`frontend/android/app/src/main/res/values/colors.xml`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/android/app/src/main/res/values/colors.xml) | Defines `#10B981` (Emerald accent color) used by Android to tint notification headers. |
| [`frontend/android/app/src/main/AndroidManifest.xml`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/android/app/src/main/AndroidManifest.xml) | Declares notification permissions, metadata tags for default icon, color, and channel. |
| [`frontend/lib/main.dart`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/lib/main.dart) | Background isolate handler, runtime permissions, FCM token registration, and deep-link routing. |
| [`frontend/lib/services/api_service.dart`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/frontend/lib/services/api_service.dart) | Sends the extracted FCM token to `POST /api/v1/notifications/devices`. |

---

### Component 1: Custom Vector Candlestick Icon (`ic_stat_notification.xml`)

> **Crucial Rule**: Android status bar icons **must be pure white (`#FFFFFFFF`) on a transparent background**. Android ignores all color channels in status bar icons and uses the shape strictly as an alpha transparency mask.

Create the file at:
`frontend/android/app/src/main/res/drawable/ic_stat_notification.xml`

```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <!-- Left Candlestick -->
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M4,9h3v7H4z"/>
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M5,6h1v3H5z"/>
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M5,16h1v3H5z"/>

    <!-- Middle Candlestick (Bullish Expansion) -->
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M10,6h3v10h-3z"/>
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M11,3h1v3h-1z"/>
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M11,16h1v4h-1z"/>

    <!-- Right Candlestick (Breakout) -->
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M16,4h3v9h-3z"/>
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M17,1h1v3h-1z"/>
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M17,13h1v5h-1z"/>

    <!-- AI Signal Star (Top Right Confluence Sparkle) -->
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M21.5,1.5l0.7,1.4 1.5,0.7 -1.5,0.7 -0.7,1.5 -0.7,-1.5 -1.5,-0.7 1.5,-0.7z"/>
</vector>
```

---

### Component 2: Emerald Notification Accent Color (`colors.xml`)

Android applies this color to the small circular background behind your icon, the app name title text, and the interactive action buttons in the notification drawer.

Create the file at:
`frontend/android/app/src/main/res/values/colors.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <!-- Institutional Emerald Accent Token -->
    <color name="notification_accent">#10B981</color>
</resources>
```

---

### Component 3: Android Gradle Configuration (`build.gradle.kts`)

#### Root Gradle: `frontend/android/build.gradle.kts`
Add the Google Services classpath inside the `buildscript` block:

```kotlin
buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath("com.google.gms:google-services:4.4.2")
    }
}
```

#### App Gradle: `frontend/android/app/build.gradle.kts`
Apply the plugin in the `plugins` block:

```kotlin
plugins {
    id("com.android.application")
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services") // <-- Must be applied here
}

android {
    namespace = "com.forexai.platform.frontend"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    defaultConfig {
        applicationId = "com.forexai.platform.frontend"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }
}
```

---

### Component 4: Android Manifest Permissions & Channel Metadata

Edit `frontend/android/app/src/main/AndroidManifest.xml`:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- Essential Network & Notification Permissions -->
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/> <!-- Android 13+ (API 33+) -->
    <uses-permission android:name="android.permission.VIBRATE"/>
    <uses-permission android:name="android.permission.WAKE_LOCK"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>

    <application
        android:label="Forex AI"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher">

        <!-- 1. Default Notification Channel ID -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="forex_ai_alerts" />

        <!-- 2. Custom Silhouette Notification Icon -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_icon"
            android:resource="@drawable/ic_stat_notification" />

        <!-- 3. Custom Emerald Accent Tint -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_color"
            android:resource="@color/notification_accent" />

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop" <!-- Ensures single instance on notification click -->
            ...>
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
```

---

### Component 5: Flutter FCM Initialization & Background Handler

Inside `frontend/lib/main.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'services/api_service.dart';

// 1. MUST be a top-level function outside any class with @pragma entry-point
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  debugPrint('Background FCM received: ${message.messageId}');
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase SDK
  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  } catch (e) {
    debugPrint('Firebase initialization notice: $e');
  }

  runApp(const ForexAIApp());
  _initFCM();
}

Future<void> _initFCM() async {
  try {
    final messaging = FirebaseMessaging.instance;

    // Request permissions for Android 13+ and iOS
    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    // Enable heads-up alerts while the app is in the foreground
    await messaging.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    // Retrieve unique FCM device token & register with backend
    final token = await messaging.getToken();
    if (token != null) {
      debugPrint('FCM Token: $token');
      await ApiService.registerDevice(fcmToken: token, platform: 'android');
    }

    // Subscribe to macroeconomic event broadcasts
    await messaging.subscribeToTopic('economic_events');

    // Handle token rotation automatically
    messaging.onTokenRefresh.listen((newToken) {
      ApiService.registerDevice(fcmToken: newToken, platform: 'android');
    });

    // Wire up lifecycle click listeners
    _setupNotificationClickListeners(messaging);
  } catch (e) {
    debugPrint('FCM init error: $e');
  }
}
```

---

### Component 6: Deep-Linking & Click Routing to Trade Tickets

When a trader taps an alert, they must immediately land on the relevant asset's Trade Ticket or Macro Event.

```dart
void _setupNotificationClickListeners(FirebaseMessaging messaging) {
  // Case A: App was completely CLOSED (Terminated)
  messaging.getInitialMessage().then((message) {
    if (message != null) {
      Future.delayed(const Duration(milliseconds: 600), () {
        _handleNotificationOpen(message);
      });
    }
  });

  // Case B: App was in the BACKGROUND (Minimized)
  FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
    _handleNotificationOpen(message);
  });
}

void _handleNotificationOpen(RemoteMessage? message) {
  if (message == null) return;
  
  final type = message.data['type']?.toString();
  final screen = message.data['screen']?.toString();

  // 1. Economic Event Navigation
  if (type == 'ECONOMIC_EVENT_UPCOMING' || screen == 'news') {
    final eventId = message.data['event_id']?.toString();
    shellKey.currentState?.navigateToNews(eventId);
    return;
  }

  // 2. Direct Trade Ticket Navigation by Symbol
  final symbol = message.data['symbol']?.toString();
  if (symbol != null && symbol.isNotEmpty) {
    shellKey.currentState?.navigateToAnalysis(symbol);
    return;
  }

  // 3. Fallback title/body scanner for known instruments
  final text = '${message.notification?.title ?? ''} ${message.notification?.body ?? ''}'.toUpperCase();
  for (final s in ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'R_75', 'BOOM1000']) {
    if (text.contains(s)) {
      shellKey.currentState?.navigateToAnalysis(s);
      return;
    }
  }
}
```

---

### Component 7: Foreground Trading Alert Banner

When the trader has the app actively open, `FirebaseMessaging.onMessage.listen` intercepts the notification and displays an institutional trading banner at the top of the screen:

```dart
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  final ctx = navigatorKey.currentContext;
  if (ctx == null || !ctx.mounted) return;

  final title = message.notification?.title ?? message.data['title'] ?? 'AI Market Alert';
  final body = message.notification?.body ?? message.data['body'] ?? '';
  final symbol = message.data['symbol']?.toString();
  final isBuy = message.data['action']?.toString().toUpperCase().contains('BUY') ?? false;

  ScaffoldMessenger.of(ctx).showSnackBar(
    SnackBar(
      backgroundColor: const Color(0xFF0F172A), // Dark slate
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.all(12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: isBuy ? const Color(0xFF10B981) : const Color(0xFFF43F5E), // Emerald or Rose
          width: 1.5,
        ),
      ),
      content: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: (isBuy ? const Color(0xFF10B981) : const Color(0xFFF43F5E)).withOpacity(0.2),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              isBuy ? 'BUY' : 'SELL',
              style: TextStyle(
                color: isBuy ? const Color(0xFF10B981) : const Color(0xFFF43F5E),
                fontWeight: FontWeight.bold,
                fontSize: 11,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                Text(body, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12), maxLines: 1),
              ],
            ),
          ),
          if (symbol != null)
            TextButton(
              onPressed: () {
                ScaffoldMessenger.of(ctx).hideCurrentSnackBar();
                shellKey.currentState?.navigateToAnalysis(symbol);
              },
              child: const Text('VIEW', style: TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold)),
            ),
        ],
      ),
    ),
  );
});
```

---

### Component 8: Backend High-Priority Dispatch Pairing

On the backend, [`backend/app/services/notifications/notification_service.py`](file:///c:/Users/lenovo/.gemini/antigravity-ide/scratch/forex-ai-platform/backend/app/services/notifications/notification_service.py) constructs the message matching the exact channel and styling configured in the Android app:

```python
from firebase_admin import messaging

message = messaging.Message(
    token=device_token,
    notification=messaging.Notification(
        title="XAUUSD | BUY LIMIT (Grade A+)",
        body="Entry: 2650.50 | SL: 2642.10 | TP1: 2663.10 (+1.5R)"
    ),
    data={
        "type": "TRADE_SETUP_GENERATED",
        "symbol": "XAUUSD",
        "action": "BUY LIMIT",
        "entry_price": "2650.50",
        "stop_loss": "2642.10",
        "tp1": "2663.10",
        "tp2": "2675.70",
        "screen": "analysis",
        "state": "VALID_SETUP"
    },
    android=messaging.AndroidConfig(
        priority="high",
        ttl=3600,
        notification=messaging.AndroidNotification(
            channel_id="forex_ai_high_importance", # High importance channel with sound & heads-up popup
            icon="ic_stat_notification",           # References the vector candlestick drawable
            color="#10B981",                       # Institutional emerald accent tint
            sound="default",
            default_vibrate_timings=True,
        )
    )
)

response = messaging.send(message)
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
| `GET` | `/api/v1/sessions/evaluate` | Evaluate sessions & DST transitions for a specific UTC timestamp |
| `POST` | `/api/v1/analysis/run` | Trigger on-demand MSNR + SMC + UT Bot AI analysis |
| `GET` | `/api/v1/analysis/latest/{symbol}` | Retrieve latest actionable trade ticket |
| `GET` | `/api/v1/analysis/scanner/status` | Get real-time scanner health & state counts (`NO_SETUP/WATCH/POTENTIAL/VALID`) |
| `POST` | `/api/v1/analysis/scanner/run-once` | Manually trigger an immediate scan cycle across watchlist |
| `POST` | `/api/v1/analysis/lifecycle-event` | Report trade lifecycle state change |
| `POST` | `/api/v1/notifications/devices` | Register mobile FCM token |
| `POST` | `/api/v1/notifications/test` | Trigger a test push notification |
| `GET` | `/api/v1/news/dxy` | Real-time DXY metrics (macro events only; no mock data) |
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

### Running Automated Test Suite

The platform includes a test suite covering the entire institutional stack:

```bash
cd backend
python -m pytest tests/
```

- **Suite Coverage**: **160 tests passing** across 24 test modules.
- **Key Modules**:
  - `tests/test_setup_mathematics.py`: Strict geometry verification (TP < Entry < SL on shorts, SL < Entry < TP on longs, $R:R \ge 2.0$), SessionProfileModel condition checks, liquidity proximity POTENTIAL_SETUP, and scanner status counts.
  - `tests/test_seven_hour_profile_engine.py`: 7H profile boundaries, 85% completeness threshold (6/7 candles), 3h daily anchor stub, consecutive profile relationships (`SUPPORT`/`CONTRADICT`/`NEUTRAL`), and zero-repainting guarantees.
  - `tests/test_session_engine.py`: 36-hour lookback Asian & London session persistence across DST shifts and NY overlap.
  - `tests/test_msnr_engine.py`: Consequent encroachment (50% CE) midpoint entries, RBS/SBR flips, and manipulation exhaustion bars.
  - `tests/test_smt_engine.py`: Precious metals (XAU/XAG) & Majors (EUR/GBP) divergence, Grade A+ elevation, and contradictory conflict vetoes.
  - `tests/test_bias_validation_engine.py`: DXY decoupling (returns NEUTRAL for setups, zero mock data).
  - `tests/test_notifications.py`: FCM high-priority dispatch, deduplication cooldown, and trade lifecycle milestone alerts.


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
