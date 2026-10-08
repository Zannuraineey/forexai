from datetime import datetime, time, date, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict
from app.schemas.candle import CandleRead

class SessionWindowInfo(BaseModel):
    name: str # 'asian', 'london', 'new_york'
    timezone_name: str # e.g. 'Asia/Tokyo', 'Europe/London', 'America/New_York'
    is_active: bool
    local_start_time: str
    local_end_time: str
    current_local_time: str
    start_utc: datetime
    end_utc: datetime
    status: str # 'UPCOMING', 'ACTIVE', 'COMPLETED'

    model_config = ConfigDict(from_attributes=True)

class SessionLevels(BaseModel):
    session_name: str # 'asian', 'london', 'new_york'
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    range_pips: Optional[float] = None
    status: str = "UPCOMING" # 'UPCOMING', 'ACTIVE', 'COMPLETED'
    swept_high: bool = False
    swept_low: bool = False
    candle_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class CurrentSessionState(BaseModel):
    timestamp_utc: datetime
    active_sessions: List[str]
    is_overlap: bool
    overlap_name: Optional[str] = None # e.g. 'london_new_york_overlap'
    primary_session: Optional[str] = None
    session_windows: Dict[str, SessionWindowInfo]
    session_levels: Dict[str, SessionLevels] = {}

    model_config = ConfigDict(from_attributes=True)

class SessionEngine:
    """
    Institutional DST-aware trading session engine.
    Uses canonical geographic IANA timezones (Asia/Tokyo, Europe/London, America/New_York)
    to dynamically adapt across Daylight Saving Time shifts (GMT/BST, EST/EDT)
    without hardcoded UTC offsets.
    """

    SESSION_CONFIGS = {
        "asian": {
            "timezone": "Asia/Tokyo",
            "start": time(9, 0),    # 09:00 JST -> 00:00 UTC (No DST in Japan)
            "end": time(18, 0),      # 18:00 JST -> 09:00 UTC
        },
        "london": {
            "timezone": "Europe/London",
            "start": time(8, 0),    # 08:00 Local -> 08:00 UTC (Winter GMT) / 07:00 UTC (Summer BST)
            "end": time(16, 30),    # 16:30 Local -> 16:30 UTC (Winter GMT) / 15:30 UTC (Summer BST)
        },
        "new_york": {
            "timezone": "America/New_York",
            "start": time(8, 0),    # 08:00 Local -> 13:00 UTC (Winter EST) / 12:00 UTC (Summer EDT)
            "end": time(17, 0),     # 17:00 Local -> 22:00 UTC (Winter EST) / 21:00 UTC (Summer EDT)
        },
    }

    @classmethod
    def get_killzone_info(cls, dt_utc: datetime) -> Dict[str, Any]:
        """
        Institutional Killzone Identifier (DST & UTC normalized):
        - London Open Killzone: 07:00 - 10:00 UTC (A+)
        - New York Open Killzone: 12:00 - 14:00 UTC (A+)
        - NYSE Cash Open / Judas Window: 14:30 - 16:00 UTC (A+)
        - London Close Killzone: 16:30 - 18:30 UTC (A+)
        - Off-Killzone Consolidation: Grade B
        """
        t = dt_utc.time()
        if time(7, 0) <= t < time(10, 0):
            return {"is_killzone": True, "name": "London Open Killzone", "grade": "Grade A+"}
        elif time(12, 0) <= t < time(14, 0):
            return {"is_killzone": True, "name": "NY Open Killzone", "grade": "Grade A+"}
        elif time(14, 30) <= t < time(16, 0):
            return {"is_killzone": True, "name": "NYSE Cash Open (Judas Window)", "grade": "Grade A+"}
        elif time(16, 30) <= t < time(18, 30):
            return {"is_killzone": True, "name": "London Close Killzone", "grade": "Grade A+"}
        return {"is_killzone": False, "name": "Off-Killzone Session", "grade": "Grade B"}

    @classmethod
    def get_session_window(
        cls, session_name: str, target_date: date, dt_utc: datetime
    ) -> SessionWindowInfo:
        config = cls.SESSION_CONFIGS[session_name]
        tz = ZoneInfo(config["timezone"])
        
        # Local start and end datetimes on the target date
        local_start = datetime.combine(target_date, config["start"], tzinfo=tz)
        local_end = datetime.combine(target_date, config["end"], tzinfo=tz)
        
        # Handle overnight edge cases if start > end (not currently used, but robust)
        if config["end"] < config["start"]:
            local_end += timedelta(days=1)
            
        start_utc = local_start.astimezone(timezone.utc)
        end_utc = local_end.astimezone(timezone.utc)
        
        dt_local = dt_utc.astimezone(tz)
        
        if dt_utc < start_utc:
            status = "UPCOMING"
            is_active = False
        elif dt_utc >= end_utc:
            status = "COMPLETED"
            is_active = False
        else:
            status = "ACTIVE"
            is_active = True

        return SessionWindowInfo(
            name=session_name,
            timezone_name=config["timezone"],
            is_active=is_active,
            local_start_time=config["start"].strftime("%H:%M"),
            local_end_time=config["end"].strftime("%H:%M"),
            current_local_time=dt_local.strftime("%H:%M:%S"),
            start_utc=start_utc,
            end_utc=end_utc,
            status=status,
        )

    @classmethod
    def evaluate_sessions(
        cls,
        dt_utc: datetime,
        candles_today: Optional[List[CandleRead]] = None,
        pip_size: float = 0.0001,
        current_candle: Optional[CandleRead] = None,
    ) -> CurrentSessionState:
        """
        Determines active sessions and computes session levels for the current day.
        """
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt_utc.astimezone(timezone.utc)

        current_date = dt_utc.date()
        windows: Dict[str, SessionWindowInfo] = {}
        active_list: List[str] = []

        for name in ["asian", "london", "new_york"]:
            window = cls.get_session_window(name, current_date, dt_utc)
            # If the session ended before now, check if there's a more relevant recent window
            # (e.g. Asian session started yesterday local time or early today)
            windows[name] = window
            if window.is_active:
                active_list.append(name)

        is_overlap = len(active_list) > 1
        overlap_name = None
        if "london" in active_list and "new_york" in active_list:
            overlap_name = "london_new_york_overlap"
        elif is_overlap:
            overlap_name = "_".join(active_list) + "_overlap"

        # Determine primary session
        primary_session: Optional[str] = None
        if "new_york" in active_list:
            primary_session = "new_york"
        elif "london" in active_list:
            primary_session = "london"
        elif "asian" in active_list:
            primary_session = "asian"
        elif active_list:
            primary_session = active_list[0]

        # Calculate session levels (High, Low, Open, Close, Sweeps) if candles provided
        session_levels: Dict[str, SessionLevels] = {}
        curr = current_candle or (candles_today[-1] if candles_today else None)

        for name, window in windows.items():
            lvl = SessionLevels(session_name=name, status=window.status)
            if candles_today:
                # Filter candles that fell within [start_utc, end_utc]
                # If window is ACTIVE, candles up to current dt_utc
                session_candles = [
                    c for c in candles_today
                    if window.start_utc <= (c.timestamp_utc.astimezone(timezone.utc) if c.timestamp_utc.tzinfo else c.timestamp_utc.replace(tzinfo=timezone.utc)) < window.end_utc
                ]
                if session_candles:
                    lvl.candle_count = len(session_candles)
                    lvl.open = session_candles[0].open
                    lvl.close = session_candles[-1].close
                    lvl.high = max(c.high for c in session_candles)
                    lvl.low = min(c.low for c in session_candles)
                    lvl.range_pips = round((lvl.high - lvl.low) / pip_size, 1)

                    # Check for sweeps by current candle if current candle is outside or after session
                    if curr is not None and lvl.high is not None and lvl.low is not None:
                        # High swept: curr.high exceeds session high, but curr.close is below or candle is wick
                        if curr.high > lvl.high:
                            lvl.swept_high = True
                        if curr.low < lvl.low:
                            lvl.swept_low = True

            session_levels[name] = lvl

        return CurrentSessionState(
            timestamp_utc=dt_utc,
            active_sessions=active_list,
            is_overlap=is_overlap,
            overlap_name=overlap_name,
            primary_session=primary_session,
            session_windows=windows,
            session_levels=session_levels,
        )
