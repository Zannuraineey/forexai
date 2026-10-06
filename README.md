# forexai

An institutional-grade **Forex & Synthetic Indices AI Market Analysis Platform** combining:
- **Smart Money Concepts (SMC) & ICT Strategy Engine**: Liquidity sweeps, Order Blocks, FVGs, Market Structure Shifts (MSS), and dynamic multi-session Killzones (Asian, London, New York).
- **Non-Repainting UT Bot Engine**: Dynamic ATR trailing stop with 200 EMA trend filtering, 14 RSI momentum gating, and confirmed closed-bar multi-timeframe radar.
- **Deriv Synthetic Indices Integration**: Volatility 75 (`R_75`), Crash & Boom, Step Index, and major FX pairs.
- **Decoupled Notification Layer**: Real-time Firebase Cloud Messaging (FCM) push alerts to mobile devices with custom high-priority notification channels.
- **Full-Stack Architecture**:
  - **Backend**: Python 3.12+, FastAPI, SQLAlchemy (Async PostgreSQL / SQLite fallback), Firebase Admin SDK.
  - **Mobile Client**: Flutter 3.x cross-platform app (Android & iOS), interactive charts, live alerts, and strategy controls.

---

## 🚀 Key Features

1. **Deterministic AI Market Reasoning**:
   - Zero lookahead bias.
   - Evaluates closed candle structure without repainting.
   - Computes explicit Stop Loss and Take Profit levels based on validated invalidation points.

2. **UT Bot Strategy Overlay**:
   - Designed for synthetic volatility pairs (`Volatility 75`) and Forex majors.
   - Multi-timeframe closed-bar confirmation matrix (5M, 15M, 1H).
   - Toggleable directly in the mobile analysis screen.

3. **Background Session Scanner & Push Alerts**:
   - Automated 45-second scan cycles across active watchlist pairs.
   - Intelligent 15-minute deduplication and anti-spam cooldown.
   - Modern Android notification branding with custom candlestick vector icon and emerald accent.

---

## 📁 Repository Structure

```
forex-ai-platform/
├── backend/                  # FastAPI REST API & Analysis Engine
│   ├── app/
│   │   ├── api/              # Endpoints (Sessions, Strategies, Analysis, Devices)
│   │   ├── core/             # Database connection, locks & configuration
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   └── services/         # AI providers, UT Bot, Scanner, Notifications
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # Flutter mobile application
│   ├── lib/
│   │   ├── models/           # Dart data models
│   │   ├── screens/          # Markets, Analysis, Alerts, Settings
│   │   ├── services/         # Resilient API & FCM messaging services
│   │   └── widgets/          # Charts, bottom sheets & interactive components
│   └── pubspec.yaml
└── README.md
```

---

## 🛠️ Setup & Running

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Flutter)
```bash
cd frontend
flutter pub get
flutter run
```

---

## 📄 License
MIT License
