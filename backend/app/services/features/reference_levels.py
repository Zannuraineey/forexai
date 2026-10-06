from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.candle import CandleRead

class KeyReferenceLevels(BaseModel):
    # Previous Day Levels
    previous_day_high: Optional[float] = None
    previous_day_low: Optional[float] = None
    previous_day_close: Optional[float] = None
    day_open: Optional[float] = None

    # Previous Week Levels
    previous_week_high: Optional[float] = None
    previous_week_low: Optional[float] = None
    week_open: Optional[float] = None

    # Daily Range
    adr_5_pips: Optional[float] = None
    adr_20_pips: Optional[float] = None
    current_day_range_pips: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class ReferenceLevelsCalculator:
    """
    Computes institutional reference levels:
    - PDH (Previous Day High) / PDL (Previous Day Low) / PDC (Previous Day Close)
    - PWH (Previous Week High) / PWL (Previous Week Low)
    - ADR (Average Daily Range)
    Uses strict UTC calendar boundaries.
    """

    @staticmethod
    def calculate_levels(
        daily_candles: List[CandleRead],
        current_candle: CandleRead,
        pip_size: float = 0.0001
    ) -> KeyReferenceLevels:
        """
        daily_candles should be sorted ascending by timestamp_utc.
        """
        levels = KeyReferenceLevels()
        if not daily_candles:
            return levels

        # Group or filter completed prior days
        current_date = current_candle.timestamp_utc.date()
        past_days = [c for c in daily_candles if c.timestamp_utc.date() < current_date]

        if past_days:
            # Most recent completed day
            prev_day = past_days[-1]
            levels.previous_day_high = prev_day.high
            levels.previous_day_low = prev_day.low
            levels.previous_day_close = prev_day.close

            # ADR over past 5 and 20 days
            ranges_pips = [(d.high - d.low) / pip_size for d in past_days]
            if len(ranges_pips) >= 5:
                levels.adr_5_pips = round(sum(ranges_pips[-5:]) / 5.0, 1)
            if len(ranges_pips) >= 20:
                levels.adr_20_pips = round(sum(ranges_pips[-20:]) / 20.0, 1)

        # Current Day Open and Range
        today_candles = [c for c in daily_candles if c.timestamp_utc.date() == current_date]
        if today_candles:
            levels.day_open = today_candles[0].open
            day_high = max(today_candles[0].high, current_candle.high)
            day_low = min(today_candles[0].low, current_candle.low)
            levels.current_day_range_pips = round((day_high - day_low) / pip_size, 1)
        else:
            levels.day_open = current_candle.open
            levels.current_day_range_pips = round((current_candle.high - current_candle.low) / pip_size, 1)

        # Weekly calculations: determine current week start (Monday)
        current_cal = current_candle.timestamp_utc.isocalendar()
        curr_year, curr_week = current_cal[0], current_cal[1]

        # Prior week candles
        prior_week_candles = [
            c for c in daily_candles
            if c.timestamp_utc.isocalendar()[0] < curr_year or
            (c.timestamp_utc.isocalendar()[0] == curr_year and c.timestamp_utc.isocalendar()[1] < curr_week)
        ]
        if prior_week_candles:
            # Filter strictly to the immediately preceding week
            last_pw_cal = prior_week_candles[-1].timestamp_utc.isocalendar()
            target_pw_year, target_pw_week = last_pw_cal[0], last_pw_cal[1]
            pw_bars = [
                c for c in prior_week_candles
                if c.timestamp_utc.isocalendar()[0] == target_pw_year
                and c.timestamp_utc.isocalendar()[1] == target_pw_week
            ]
            if pw_bars:
                levels.previous_week_high = max(c.high for c in pw_bars)
                levels.previous_week_low = min(c.low for c in pw_bars)

        # Current Week Open
        curr_week_candles = [
            c for c in daily_candles
            if c.timestamp_utc.isocalendar()[0] == curr_year
            and c.timestamp_utc.isocalendar()[1] == curr_week
        ]
        if curr_week_candles:
            levels.week_open = curr_week_candles[0].open

        return levels
