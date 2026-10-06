from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from app.schemas.news import EconomicEvent

class EconomicCalendarService:
    """
    Supplies macroeconomic calendar data, actual vs forecast tracking,
    event educational context, and historical reaction metrics for institutional reasoning.
    """

    def __init__(self):
        self._events: List[EconomicEvent] = []
        self._initialize_canonical_events()

    def _initialize_canonical_events(self):
        now = datetime.now(timezone.utc)
        self._events = [
            EconomicEvent(
                id="us_cpi_mom",
                title="US Consumer Price Index (CPI YoY)",
                country="US",
                currency="USD",
                impact="HIGH",
                event_time_utc=now - timedelta(hours=3),
                actual=2.9,
                forecast=2.8,
                previous=2.6,
                revised=None,
                unit="%",
                status="RELEASED",
                meaning=(
                    "The Consumer Price Index measures the average change over time in prices paid by consumers "
                    "for a basket of goods and services. As the primary inflation benchmark watched by the Federal Reserve, "
                    "a higher-than-expected print increases expectations of prolonged high interest rates ('higher-for-longer'), "
                    "which strengthens institutional demand for the US Dollar."
                ),
                historical_context=(
                    "Over the past 6 months, CPI prints deviating by >= 0.2% from forecast have triggered an immediate "
                    "40-70 pip displacement in DXY within the first 15 minutes of the NY session."
                ),
                historical_reactions=[
                    {
                        "date": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
                        "actual": 2.6,
                        "forecast": 2.7,
                        "dxy_reaction": "-0.45% Bearish Displacement",
                        "eurusd_reaction": "+55 pips rally into 4H FVG",
                        "xauusd_reaction": "+$28.50 Liquidity sweep of weekly high",
                    },
                    {
                        "date": (now - timedelta(days=60)).strftime("%Y-%m-%d"),
                        "actual": 3.1,
                        "forecast": 2.9,
                        "dxy_reaction": "+0.62% Bullish Expansion",
                        "eurusd_reaction": "-68 pips break of internal structure",
                        "xauusd_reaction": "-$34.00 displacement to discount",
                    },
                ],
            ),
            EconomicEvent(
                id="us_nfp",
                title="US Non-Farm Payrolls (NFP)",
                country="US",
                currency="USD",
                impact="HIGH",
                event_time_utc=now + timedelta(days=2),
                actual=None,
                forecast=165.0,
                previous=142.0,
                unit="K",
                status="SCHEDULED",
                meaning=(
                    "Non-Farm Payrolls measures the net change in the number of employed people in the US over the prior month, "
                    "excluding the farming industry. It is the most volatile monthly US economic release and heavily influences Fed policy. "
                    "Strong labor additions drive wage pressure and hawkish Fed rate expectations, driving DXY buying."
                ),
                historical_context=(
                    "NFP releases consistently produce dual-side liquidity sweeps in London/NY killzone overlapping pairs. "
                    "A surprise beat of >= 30K historically fuels multi-day DXY upward expansion."
                ),
                historical_reactions=[
                    {
                        "date": (now - timedelta(days=28)).strftime("%Y-%m-%d"),
                        "actual": 142.0,
                        "forecast": 160.0,
                        "dxy_reaction": "-0.38% Retracement",
                        "eurusd_reaction": "+42 pips into London High sweep",
                        "xauusd_reaction": "+$22.00 Bullish MSS",
                    }
                ],
            ),
            EconomicEvent(
                id="us_fomc_rate",
                title="Fed Interest Rate Decision (FOMC)",
                country="US",
                currency="USD",
                impact="HIGH",
                event_time_utc=now + timedelta(days=7),
                actual=None,
                forecast=5.00,
                previous=5.00,
                unit="%",
                status="SCHEDULED",
                meaning=(
                    "The Federal Open Market Committee sets the target federal funds rate. Changes directly adjust commercial banks' "
                    "borrowing costs, dictating global capital flows into or out of US dollar denominated debt instruments and Treasuries."
                ),
                historical_context=(
                    "FOMC rate announcements accompanied by Chair press conferences determine quarterly market regimes. "
                    "Hawkish holds or rate hikes compress risk assets while propelling DXY toward institutional premium arrays."
                ),
                historical_reactions=[
                    {
                        "date": (now - timedelta(days=45)).strftime("%Y-%m-%d"),
                        "actual": 5.00,
                        "forecast": 5.00,
                        "dxy_reaction": "+0.55% Post-conference rally",
                        "eurusd_reaction": "-75 pips sweep of Asian session range",
                        "xauusd_reaction": "-$40.00 Drop into Daily Order Block",
                    }
                ],
            ),
            EconomicEvent(
                id="us_core_pce",
                title="US Core PCE Price Index (MoM)",
                country="US",
                currency="USD",
                impact="HIGH",
                event_time_utc=now - timedelta(days=5),
                actual=0.3,
                forecast=0.2,
                previous=0.2,
                unit="%",
                status="RELEASED",
                meaning=(
                    "The Personal Consumption Expenditures price index excluding food and energy is the Federal Reserve's "
                    "officially preferred gauge of underlying consumer inflation. Deviations from expectations directly recalibrate "
                    "interest rate swap pricing."
                ),
                historical_context="PCE beats create persistent trend continuation rather than knee-jerk wicks.",
                historical_reactions=[
                    {
                        "date": (now - timedelta(days=35)).strftime("%Y-%m-%d"),
                        "actual": 0.2,
                        "forecast": 0.2,
                        "dxy_reaction": "+0.05% Range Bound",
                        "eurusd_reaction": "-10 pips consolidation",
                        "xauusd_reaction": "-$5.00 equilibrium retest",
                    }
                ],
            ),
            EconomicEvent(
                id="us_retail_sales",
                title="US Retail Sales (MoM)",
                country="US",
                currency="USD",
                impact="MEDIUM",
                event_time_utc=now + timedelta(days=4),
                actual=None,
                forecast=0.4,
                previous=0.1,
                unit="%",
                status="SCHEDULED",
                meaning=(
                    "Measures consumer expenditure at the retail level, representing roughly two-thirds of total US economic activity. "
                    "Resilient consumer demand signals robust economic growth, supporting the US dollar against foreign currencies."
                ),
                historical_context="Retail sales beats often fuel early New York session continuation moves in FX majors.",
                historical_reactions=[],
            ),
            EconomicEvent(
                id="us_jobless_claims",
                title="US Initial Jobless Claims",
                country="US",
                currency="USD",
                impact="MEDIUM",
                event_time_utc=now + timedelta(hours=14),
                actual=None,
                forecast=218.0,
                previous=222.0,
                unit="K",
                status="SCHEDULED",
                meaning=(
                    "Weekly metric tracking individuals filing for unemployment insurance for the first time. "
                    "Serves as the most up-to-date high-frequency pulse on US labor market tightness."
                ),
                historical_context="A spike above 230k signals labor cooling, pressuring DXY lower.",
                historical_reactions=[],
            ),
        ]

    def get_all_events(self) -> List[EconomicEvent]:
        return self._events

    def get_event_by_id(self, event_id: str) -> Optional[EconomicEvent]:
        for e in self._events:
            if e.id == event_id:
                return e
        return self._events[0] if self._events else None
