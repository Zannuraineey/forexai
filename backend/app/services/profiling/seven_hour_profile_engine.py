import math
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.candle import CandleRead, CandleDTO
from app.schemas.seven_hour_profile import (
    SevenHourProfileConfig,
    SevenHourProfileResult,
    SevenHourQuantitativeFeatures,
    ProfileRelationship,
    ProfileStatus,
    ProfileDirection,
    ProfileClassification,
    DataQuality,
    PreviousProfileSummary,
)
from app.models.seven_hour_profile import SevenHourProfile


class SevenHourProfileEngine:
    """
    Independent 7-Hour Higher-Timeframe Profiling Engine.
    
    Synthesizes custom/synthetic 7-hour profile candles from lower-timeframe
    OHLC data (e.g., 1h, 15m, 5m), computes quantitative microstructure metrics,
    evaluates relationships between consecutive completed profiles, and performs
    deterministic profile classification without any AI/LLM intervention.
    
    Key Architectural Guarantees:
    - Completely decoupled from external session engine (zero session logic or dependency).
    - Fully configurable anchor boundary (timezone, start time, alignment mode).
    - Zero-repainting: completed historical profiles are immutable and never look ahead.
    - Status-aware: IN_PROGRESS profiles are segregated from confirmed historical bars.
    """

    @classmethod
    def get_expected_candle_count(cls, duration_hours: int, source_timeframe: str) -> int:
        """Calculates expected count of source candles for the profile duration."""
        tf = source_timeframe.lower().strip()
        total_minutes = duration_hours * 60
        if tf in ("1m", "m1"):
            return total_minutes
        elif tf in ("5m", "m5"):
            return total_minutes // 5
        elif tf in ("15m", "m15"):
            return total_minutes // 15
        elif tf in ("30m", "m30"):
            return total_minutes // 30
        elif tf in ("1h", "h1"):
            return total_minutes // 60
        elif tf in ("4h", "h4"):
            return max(1, total_minutes // 240)
        return max(1, total_minutes // 60)

    @classmethod
    def get_window_for_timestamp(
        cls, dt_utc: datetime, config: SevenHourProfileConfig
    ) -> Tuple[datetime, datetime]:
        """
        Determines the [start_utc, end_utc) window containing dt_utc.
        Explicitly respects configured anchor timezone, start time, and duration.
        """
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt_utc.astimezone(timezone.utc)

        tz = ZoneInfo(config.anchor_timezone)
        dt_local = dt_utc.astimezone(tz)
        duration_seconds = config.duration_hours * 3600

        if config.alignment_mode == "DAILY_ANCHOR":
            # Day anchor resets at anchor_start on each local date
            anchor_dt = datetime.combine(dt_local.date(), config.anchor_start, tzinfo=tz)
            if dt_local < anchor_dt:
                anchor_dt -= timedelta(days=1)
            delta_sec = (dt_local - anchor_dt).total_seconds()
            block_idx = math.floor(delta_sec / duration_seconds)
            start_local = anchor_dt + timedelta(seconds=block_idx * duration_seconds)
            end_local = start_local + timedelta(seconds=duration_seconds)
        else:
            # CONTINUOUS mode: fixed baseline reference aligned with Monday 2024-01-01 at anchor_start
            epoch_ref = datetime(2024, 1, 1, config.anchor_start.hour, config.anchor_start.minute, tzinfo=tz)
            delta_sec = (dt_local - epoch_ref).total_seconds()
            block_idx = math.floor(delta_sec / duration_seconds)
            start_local = epoch_ref + timedelta(seconds=block_idx * duration_seconds)
            end_local = start_local + timedelta(seconds=duration_seconds)

        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        return start_utc, end_utc

    @classmethod
    def generate_windows_range(
        cls, start_utc: datetime, end_utc: datetime, config: SevenHourProfileConfig
    ) -> List[Tuple[datetime, datetime]]:
        """Generates all non-overlapping 7H profile windows covering [start_utc, end_utc]."""
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=timezone.utc)
        if end_utc.tzinfo is None:
            end_utc = end_utc.replace(tzinfo=timezone.utc)

        windows: List[Tuple[datetime, datetime]] = []
        curr_w_start, curr_w_end = cls.get_window_for_timestamp(start_utc, config)

        while curr_w_start <= end_utc:
            windows.append((curr_w_start, curr_w_end))
            next_sample = curr_w_end + timedelta(seconds=1)
            curr_w_start, curr_w_end = cls.get_window_for_timestamp(next_sample, config)
            if windows and curr_w_start <= windows[-1][0]:
                curr_w_start = windows[-1][1]
                curr_w_end = curr_w_start + timedelta(hours=config.duration_hours)

        return windows

    @classmethod
    def build_synthetic_profile(
        cls,
        symbol: str,
        window_start_utc: datetime,
        window_end_utc: datetime,
        candles_in_window: List[Union[CandleRead, CandleDTO]],
        config: SevenHourProfileConfig,
        current_time_utc: Optional[datetime] = None,
        previous_profile: Optional[SevenHourProfileResult] = None,
        atr_value: Optional[float] = None,
        historical_ranges: Optional[List[float]] = None,
    ) -> SevenHourProfileResult:
        """
        Synthesizes a 7H profile candle from lower-timeframe bars within [window_start_utc, window_end_utc).
        Strictly zero-repaint: never accesses or incorporates bars past window_end_utc.
        """
        if current_time_utc is None:
            eval_time = candles_in_window[-1].timestamp_utc if candles_in_window else window_end_utc
        else:
            eval_time = current_time_utc

        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)
        else:
            eval_time = eval_time.astimezone(timezone.utc)

        expected_count = cls.get_expected_candle_count(config.duration_hours, config.source_timeframe)
        actual_count = len(candles_in_window)

        # Determine Profile Status
        if eval_time < window_end_utc:
            status = ProfileStatus.IN_PROGRESS
        else:
            status = ProfileStatus.COMPLETED

        # Determine Data Quality
        if actual_count == 0:
            data_quality = DataQuality.INSUFFICIENT
        elif actual_count >= int(expected_count * config.min_candles_ratio_for_complete):
            data_quality = DataQuality.COMPLETE
        else:
            data_quality = DataQuality.PARTIAL

        # Handle zero candle edge case safely
        if actual_count == 0:
            features = SevenHourQuantitativeFeatures(
                range=0.0,
                normalized_range=0.0,
                body=0.0,
                upper_wick=0.0,
                lower_wick=0.0,
                body_ratio=0.0,
                close_location=0.5,
            )
            return SevenHourProfileResult(
                symbol=symbol,
                profile_start=window_start_utc,
                profile_end=window_end_utc,
                status=status,
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                direction=ProfileDirection.NEUTRAL,
                range=0.0,
                body=0.0,
                body_ratio=0.0,
                close_location=0.5,
                features=features,
                previous_profile=None,
                relationship=None,
                classification=ProfileClassification.INSUFFICIENT_DATA,
                source_timeframe=config.source_timeframe,
                source_candle_count=0,
                expected_candle_count=expected_count,
                data_quality=data_quality,
                config_id=config.config_id,
            )

        # Sort candles strictly ascending by timestamp (timezone-normalized)
        sorted_candles = sorted(
            candles_in_window,
            key=lambda c: c.timestamp_utc if c.timestamp_utc.tzinfo else c.timestamp_utc.replace(tzinfo=timezone.utc)
        )

        p_open = float(sorted_candles[0].open)
        p_high = float(max(c.high for c in sorted_candles))
        p_low = float(min(c.low for c in sorted_candles))
        p_close = float(sorted_candles[-1].close)

        p_range = round(p_high - p_low, 6)
        p_body = round(abs(p_close - p_open), 6)
        p_upper_wick = round(p_high - max(p_open, p_close), 6)
        p_lower_wick = round(min(p_open, p_close) - p_low, 6)

        # Safe zero-range handling
        if p_range > 0:
            body_ratio = round(p_body / p_range, 4)
            close_location = round((p_close - p_low) / p_range, 4)
        else:
            body_ratio = 0.0
            close_location = 0.5

        if p_close > p_open:
            direction = ProfileDirection.BULLISH
        elif p_close < p_open:
            direction = ProfileDirection.BEARISH
        else:
            direction = ProfileDirection.NEUTRAL

        normalized_range = round(p_range / config.pip_size, 2) if config.pip_size > 0 else p_range
        range_vs_atr = round(p_range / atr_value, 4) if atr_value and atr_value > 0 else None

        range_pctile = None
        if historical_ranges and len(historical_ranges) > 0:
            below_count = sum(1 for r in historical_ranges if r < p_range)
            range_pctile = round((below_count / len(historical_ranges)) * 100.0, 1)

        # Evaluate Relationship with Previous Profile
        relationship: Optional[ProfileRelationship] = None
        prev_summary: Optional[PreviousProfileSummary] = None

        if previous_profile is not None:
            prev = previous_profile
            prev_summary = PreviousProfileSummary(
                profile_start=prev.profile_start,
                profile_end=prev.profile_end,
                open=prev.open,
                high=prev.high,
                low=prev.low,
                close=prev.close,
                range=prev.range,
                body=prev.body,
                direction=prev.direction,
                classification=prev.classification,
            )

            took_high = p_high > prev.high
            took_low = p_low < prev.low
            closed_above_high = p_close > prev.high
            closed_below_low = p_close < prev.low
            closed_inside_prev = (prev.low <= p_close <= prev.high)
            open_inside_prev = (prev.low <= p_open <= prev.high)

            expansion_ratio = round(p_range / prev.range, 4) if prev.range > 0 else 1.0
            expanded = p_range > prev.range
            contracted = p_range < prev.range

            # Continuation flag
            continuation = (
                (direction == ProfileDirection.BULLISH and prev.direction == ProfileDirection.BULLISH and p_close > prev.close) or
                (direction == ProfileDirection.BEARISH and prev.direction == ProfileDirection.BEARISH and p_close < prev.close)
            )

            # Reversal flag: sweep of previous extreme with counter-close
            reversal = (
                (prev.direction == ProfileDirection.BEARISH and took_low and direction == ProfileDirection.BULLISH and p_close >= prev.close) or
                (prev.direction == ProfileDirection.BULLISH and took_high and direction == ProfileDirection.BEARISH and p_close <= prev.close)
            )

            # Failed expansion: broke previous extreme but failed to sustain/close beyond it
            failed_expansion = (
                (took_high and not closed_above_high) or
                (took_low and not closed_below_low)
            )

            close_loc_vs_prev = (
                round((p_close - prev.low) / prev.range, 4) if prev.range > 0 else 0.5
            )

            relationship = ProfileRelationship(
                took_previous_high=took_high,
                took_previous_low=took_low,
                closed_above_previous_high=closed_above_high,
                closed_below_previous_low=closed_below_low,
                closed_inside_previous_range=closed_inside_prev,
                open_inside_previous_range=open_inside_prev,
                current_range=p_range,
                previous_range=prev.range,
                expansion_ratio=expansion_ratio,
                expanded_vs_previous=expanded,
                contracted_vs_previous=contracted,
                continuation=continuation,
                reversal=reversal,
                failed_expansion=failed_expansion,
                close_location_relative_to_previous_range=close_loc_vs_prev,
                previous_high=prev.high,
                previous_low=prev.low,
                previous_close=prev.close,
            )

        features = SevenHourQuantitativeFeatures(
            range=p_range,
            normalized_range=normalized_range,
            body=p_body,
            upper_wick=p_upper_wick,
            lower_wick=p_lower_wick,
            body_ratio=body_ratio,
            close_location=close_location,
            range_vs_atr=range_vs_atr,
            expansion_ratio=relationship.expansion_ratio if relationship else None,
            previous_range=relationship.previous_range if relationship else None,
            range_percentile=range_pctile,
            high_taken=relationship.took_previous_high if relationship else False,
            low_taken=relationship.took_previous_low if relationship else False,
            close_above_previous_high=relationship.closed_above_previous_high if relationship else False,
            close_below_previous_low=relationship.closed_below_previous_low if relationship else False,
        )

        # Deterministic Profile Classification
        classification = cls.classify_profile(
            status=status,
            direction=direction,
            p_range=p_range,
            close_location=close_location,
            previous_profile=previous_profile,
            relationship=relationship,
            data_quality=data_quality,
        )

        return SevenHourProfileResult(
            symbol=symbol,
            profile_start=window_start_utc,
            profile_end=window_end_utc,
            status=status,
            open=p_open,
            high=p_high,
            low=p_low,
            close=p_close,
            direction=direction,
            range=p_range,
            body=p_body,
            body_ratio=body_ratio,
            close_location=close_location,
            features=features,
            previous_profile=prev_summary,
            relationship=relationship,
            classification=classification,
            source_timeframe=config.source_timeframe,
            source_candle_count=actual_count,
            expected_candle_count=expected_count,
            data_quality=data_quality,
            config_id=config.config_id,
        )

    @classmethod
    def classify_profile(
        cls,
        status: ProfileStatus,
        direction: ProfileDirection,
        p_range: float,
        close_location: float,
        previous_profile: Optional[SevenHourProfileResult],
        relationship: Optional[ProfileRelationship],
        data_quality: DataQuality,
    ) -> ProfileClassification:
        """
        Deterministic, rule-based classification taxonomy.
        Zero LLM / probabilistic models used.
        """
        if previous_profile is None or relationship is None or data_quality == DataQuality.INSUFFICIENT:
            return ProfileClassification.INSUFFICIENT_DATA

        prev = previous_profile

        # 1. Bullish Reversal: Previous was bearish, low swept/taken, closed strongly bullish
        if (prev.direction == ProfileDirection.BEARISH and
            relationship.took_previous_low and
            direction == ProfileDirection.BULLISH and
            relationship.previous_close is not None and
            relationship.close_location_relative_to_previous_range is not None and
            relationship.close_location_relative_to_previous_range >= 0.50):
            return ProfileClassification.BULLISH_REVERSAL

        # 2. Bearish Reversal: Previous was bullish, high swept/taken, closed strongly bearish
        if (prev.direction == ProfileDirection.BULLISH and
            relationship.took_previous_high and
            direction == ProfileDirection.BEARISH and
            relationship.previous_close is not None and
            relationship.close_location_relative_to_previous_range is not None and
            relationship.close_location_relative_to_previous_range <= 0.50):
            return ProfileClassification.BEARISH_REVERSAL

        # 3. Bullish Expansion: Closed above previous high with range expansion
        if (direction == ProfileDirection.BULLISH and
            relationship.expanded_vs_previous and
            relationship.closed_above_previous_high):
            return ProfileClassification.BULLISH_EXPANSION

        # 4. Bearish Expansion: Closed below previous low with range expansion
        if (direction == ProfileDirection.BEARISH and
            relationship.expanded_vs_previous and
            relationship.closed_below_previous_low):
            return ProfileClassification.BEARISH_EXPANSION

        # 5. Failed Bullish Expansion: Took previous high, but failed to close above it
        if relationship.took_previous_high and not relationship.closed_above_previous_high:
            return ProfileClassification.FAILED_BULLISH_EXPANSION

        # 6. Failed Bearish Expansion: Took previous low, but failed to close below it
        if relationship.took_previous_low and not relationship.closed_below_previous_low:
            return ProfileClassification.FAILED_BEARISH_EXPANSION

        # 7. Range / Consolidation: Inside bar or contracted range closed within previous range
        inside_bar = not relationship.took_previous_high and not relationship.took_previous_low
        contracted_inside = relationship.contracted_vs_previous and relationship.closed_inside_previous_range
        if inside_bar or contracted_inside:
            return ProfileClassification.RANGE_CONSOLIDATION

        # 8. Bullish Continuation: Bullish close following bullish profile
        if (direction == ProfileDirection.BULLISH and
            prev.direction == ProfileDirection.BULLISH and
            relationship.previous_close is not None and
            relationship.close_location_relative_to_previous_range is not None and
            relationship.close_location_relative_to_previous_range > 0.50):
            return ProfileClassification.BULLISH_CONTINUATION

        # 9. Bearish Continuation: Bearish close following bearish profile
        if (direction == ProfileDirection.BEARISH and
            prev.direction == ProfileDirection.BEARISH and
            relationship.previous_close is not None and
            relationship.close_location_relative_to_previous_range is not None and
            relationship.close_location_relative_to_previous_range < 0.50):
            return ProfileClassification.BEARISH_CONTINUATION

        return ProfileClassification.UNCLASSIFIED

    @classmethod
    def evaluate_candles(
        cls,
        symbol: str,
        candles: List[Union[CandleRead, CandleDTO]],
        config: Optional[SevenHourProfileConfig] = None,
        current_time_utc: Optional[datetime] = None,
    ) -> List[SevenHourProfileResult]:
        """
        Processes a series of lower-timeframe candles into sequential 7H profiles.
        Enforces zero lookahead: profile N is calculated strictly before profile N+1,
        and profile N relationships only inspect profile N-1.
        """
        if not candles:
            return []

        cfg = config or SevenHourProfileConfig()

        # Normalize timestamps and sort
        sorted_candles = sorted(
            candles,
            key=lambda c: c.timestamp_utc if c.timestamp_utc.tzinfo else c.timestamp_utc.replace(tzinfo=timezone.utc)
        )

        min_ts = sorted_candles[0].timestamp_utc
        max_ts = sorted_candles[-1].timestamp_utc
        if min_ts.tzinfo is None:
            min_ts = min_ts.replace(tzinfo=timezone.utc)
        if max_ts.tzinfo is None:
            max_ts = max_ts.replace(tzinfo=timezone.utc)

        windows = cls.generate_windows_range(min_ts, max_ts, cfg)
        profiles: List[SevenHourProfileResult] = []
        historical_ranges: List[float] = []
        prev_profile: Optional[SevenHourProfileResult] = None

        candle_idx = 0
        n_candles = len(sorted_candles)

        for w_start, w_end in windows:
            # Collect candles strictly in [w_start, w_end)
            w_candles: List[Union[CandleRead, CandleDTO]] = []
            while candle_idx < n_candles:
                c = sorted_candles[candle_idx]
                c_ts = c.timestamp_utc if c.timestamp_utc.tzinfo else c.timestamp_utc.replace(tzinfo=timezone.utc)
                if c_ts < w_start:
                    candle_idx += 1
                    continue
                elif c_ts < w_end:
                    w_candles.append(c)
                    candle_idx += 1
                else:
                    break

            if not w_candles and candle_idx >= n_candles:
                break

            profile = cls.build_synthetic_profile(
                symbol=symbol,
                window_start_utc=w_start,
                window_end_utc=w_end,
                candles_in_window=w_candles,
                config=cfg,
                current_time_utc=current_time_utc,
                previous_profile=prev_profile,
                historical_ranges=list(historical_ranges),
            )

            profiles.append(profile)

            # Only completed profiles become historical references for the next window
            if profile.status == ProfileStatus.COMPLETED and profile.data_quality != DataQuality.INSUFFICIENT:
                prev_profile = profile
                historical_ranges.append(profile.range)

        return profiles

    @classmethod
    async def persist_profile(
        cls,
        db_session: AsyncSession,
        profile: SevenHourProfileResult,
        instrument_id: int,
    ) -> SevenHourProfile:
        """
        Persists a 7H profile record with idempotency and uniqueness guarantee.
        Prevents duplicate records for (instrument_id, profile_start_utc, config_id).
        """
        stmt = select(SevenHourProfile).where(
            SevenHourProfile.instrument_id == instrument_id,
            SevenHourProfile.profile_start_utc == profile.profile_start,
            SevenHourProfile.config_id == profile.config_id,
        )
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()

        rel_dict = profile.relationship.model_dump() if profile.relationship else {}
        feat_dict = profile.features.model_dump()

        if existing:
            existing.profile_end_utc = profile.profile_end
            existing.source_timeframe = profile.source_timeframe
            existing.status = profile.status.value
            existing.open = profile.open
            existing.high = profile.high
            existing.low = profile.low
            existing.close = profile.close
            existing.range = profile.range
            existing.body = profile.body
            existing.direction = profile.direction.value
            existing.classification = profile.classification.value
            existing.relationship_data = rel_dict
            existing.quantitative_features = feat_dict
            existing.data_quality = profile.data_quality.value
            existing.source_candle_count = profile.source_candle_count
            await db_session.commit()
            await db_session.refresh(existing)
            return existing

        new_row = SevenHourProfile(
            instrument_id=instrument_id,
            config_id=profile.config_id,
            profile_start_utc=profile.profile_start,
            profile_end_utc=profile.profile_end,
            source_timeframe=profile.source_timeframe,
            status=profile.status.value,
            open=profile.open,
            high=profile.high,
            low=profile.low,
            close=profile.close,
            range=profile.range,
            body=profile.body,
            direction=profile.direction.value,
            classification=profile.classification.value,
            relationship_data=rel_dict,
            quantitative_features=feat_dict,
            data_quality=profile.data_quality.value,
            source_candle_count=profile.source_candle_count,
        )
        db_session.add(new_row)
        await db_session.commit()
        await db_session.refresh(new_row)
        return new_row
