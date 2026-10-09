from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.candle import CandleRead
from app.schemas.msnr import (
    MSNRZone,
    MSNRZoneType,
    MSNRZoneQuality,
    MSNRSetupType,
    MSNRSetupSignal,
    MSNRAnalysisResult,
)
from app.schemas.smt import SMTDivergenceDetail, SMTDivergenceType
from app.services.features.structure import MarketStructureAnalyzer, SwingPoint

logger = logging.getLogger("forex_ai.msnr_engine")


class MSNREngine:
    """
    Malaysian Support and Resistance (MSNR) & Alchemist Playbook Engine.
    
    Synthesizes:
    1. Classic SNR (Classic A peak resistance, Classic V trough support).
    2. Role-reversal flip zones (RBS: Resistance Becomes Support, SBR: Support Becomes Resistance).
    3. Consequent Encroachment (CE 50% equilibrium of reaction candles / order blocks).
    4. Session Cycle Quarterly Theory (Asia Accumulation, London Manipulation, NY Distribution/Reversal).
    5. Daily Profile #2 (NY Reversal) with correlated SMT Divergence (XAUUSD Gold vs XAGUSD Silver).
    """

    @staticmethod
    def get_session_phase(timestamp_utc: datetime) -> str:
        """
        Maps a UTC timestamp to its Quarterly Theory (QT) session phase:
        - 00:00 - 08:00 UTC: Accumulation (Asia Range)
        - 08:00 - 12:00 UTC: Manipulation (London Sweep / Judas)
        - 12:00 - 16:00 UTC: Distribution (New York AM / Profile #2 Reversal)
        - 16:00 - 24:00 UTC: Continuation / Reset
        """
        hour = timestamp_utc.hour
        if 0 <= hour < 8:
            return "ACCUMULATION_ASIA"
        elif 8 <= hour < 12:
            return "MANIPULATION_LONDON"
        elif 12 <= hour < 16:
            return "DISTRIBUTION_NY_AM"
        else:
            return "CONTINUATION_NY_PM"

    @staticmethod
    def calculate_consequent_encroachment(
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        direction: str = "BULLISH",
        use_wick: bool = False,
    ) -> float:
        """
        Calculates the 50% Consequent Encroachment (CE) level based on Alchemist MSNR rules.
        - Bullish: 50% between Open and Low (or High and Low if use_wick=True)
        - Bearish: 50% between Open and High (or High and Low if use_wick=True)
        """
        if use_wick:
            return round((high_price + low_price) / 2.0, 4)

        if direction.upper() == "BULLISH":
            return round((open_price + low_price) / 2.0, 4)
        else:
            return round((open_price + high_price) / 2.0, 4)

    @classmethod
    def identify_msnr_zones(
        cls,
        candles: List[CandleRead],
        pip_size: float = 0.01,  # Default for Gold/Silver ($0.01)
        left_bars: int = 2,
        right_bars: int = 2,
    ) -> List[MSNRZone]:
        """
        Extracts Classic A (Resistance), Classic V (Support), RBS, and SBR flip zones.
        Evaluates touches and determines zone freshness.
        """
        if len(candles) < (left_bars + right_bars + 1):
            return []

        swings = MarketStructureAnalyzer.identify_swings(
            candles, left_bars=left_bars, right_bars=right_bars
        )
        if not swings:
            return []

        zones: List[MSNRZone] = []

        # Analyze each swing point as potential Classic A / Classic V or RBS / SBR
        for sp in swings:
            c = candles[sp.index]
            formed_time = sp.timestamp_utc

            if sp.point_type == "HIGH":
                # Classic A (Peak Resistance)
                # Zone spans from candle open/close body edge to high wick
                body_edge = max(float(c.open), float(c.close))
                top_p = float(c.high)
                bot_p = body_edge
                lvl_p = top_p
                ce_50 = cls.calculate_consequent_encroachment(
                    float(c.open), float(c.high), float(c.low), float(c.close),
                    direction="BEARISH"
                )

                # Check if price later cleanly broke ABOVE this resistance (RBS creation)
                broken = False
                broken_time: Optional[datetime] = None
                touches = 0

                for subsequent_c in candles[sp.index + 1:]:
                    # If candle closes above the top of the zone, it's broken
                    if float(subsequent_c.close) > top_p:
                        broken = True
                        broken_time = subsequent_c.timestamp_utc
                        break

                if broken:
                    # Once broken to the upside, resistance becomes support (RBS)
                    # Count subsequent retests touching the zone from above
                    rbs_touches = 0
                    rbs_broken_again = False
                    for post_c in candles:
                        if broken_time and post_c.timestamp_utc > broken_time:
                            # Retest touches the zone
                            if float(post_c.low) <= top_p and float(post_c.close) >= bot_p:
                                rbs_touches += 1
                            elif float(post_c.close) < bot_p:
                                # Invalidation of RBS
                                rbs_broken_again = True

                    quality = MSNRZoneQuality.FRESH if rbs_touches <= 1 else (
                        MSNRZoneQuality.TESTED if rbs_touches == 2 else MSNRZoneQuality.EXHAUSTED
                    )
                    zones.append(
                        MSNRZone(
                            zone_type=MSNRZoneType.RBS,
                            top_price=top_p,
                            bottom_price=bot_p,
                            level_price=top_p,
                            consequent_encroachment_50=ce_50,
                            touches_count=rbs_touches,
                            quality=quality,
                            formed_at_utc=formed_time,
                            broken_at_utc=broken_time,
                            is_active=not rbs_broken_again,
                        )
                    )
                else:
                    # Intact Classic A Resistance
                    for subsequent_c in candles[sp.index + 1:]:
                        if float(subsequent_c.high) >= bot_p and float(subsequent_c.close) <= top_p:
                            touches += 1

                    quality = MSNRZoneQuality.FRESH if touches <= 1 else (
                        MSNRZoneQuality.TESTED if touches == 2 else MSNRZoneQuality.EXHAUSTED
                    )
                    zones.append(
                        MSNRZone(
                            zone_type=MSNRZoneType.CLASSIC_A,
                            top_price=top_p,
                            bottom_price=bot_p,
                            level_price=top_p,
                            consequent_encroachment_50=ce_50,
                            touches_count=touches,
                            quality=quality,
                            formed_at_utc=formed_time,
                            broken_at_utc=None,
                            is_active=True,
                        )
                    )

            elif sp.point_type == "LOW":
                # Classic V (Trough Support)
                body_edge = min(float(c.open), float(c.close))
                top_p = body_edge
                bot_p = float(c.low)
                lvl_p = bot_p
                ce_50 = cls.calculate_consequent_encroachment(
                    float(c.open), float(c.high), float(c.low), float(c.close),
                    direction="BULLISH"
                )

                broken = False
                broken_time: Optional[datetime] = None
                touches = 0

                for subsequent_c in candles[sp.index + 1:]:
                    if float(subsequent_c.close) < bot_p:
                        broken = True
                        broken_time = subsequent_c.timestamp_utc
                        break

                if broken:
                    # Once broken to downside, support becomes resistance (SBR)
                    sbr_touches = 0
                    sbr_broken_again = False
                    for post_c in candles:
                        if broken_time and post_c.timestamp_utc > broken_time:
                            if float(post_c.high) >= bot_p and float(post_c.close) <= top_p:
                                sbr_touches += 1
                            elif float(post_c.close) > top_p:
                                sbr_broken_again = True

                    quality = MSNRZoneQuality.FRESH if sbr_touches <= 1 else (
                        MSNRZoneQuality.TESTED if sbr_touches == 2 else MSNRZoneQuality.EXHAUSTED
                    )
                    zones.append(
                        MSNRZone(
                            zone_type=MSNRZoneType.SBR,
                            top_price=top_p,
                            bottom_price=bot_p,
                            level_price=bot_p,
                            consequent_encroachment_50=ce_50,
                            touches_count=sbr_touches,
                            quality=quality,
                            formed_at_utc=formed_time,
                            broken_at_utc=broken_time,
                            is_active=not sbr_broken_again,
                        )
                    )
                else:
                    # Intact Classic V Support
                    for subsequent_c in candles[sp.index + 1:]:
                        if float(subsequent_c.low) <= top_p and float(subsequent_c.close) >= bot_p:
                            touches += 1

                    quality = MSNRZoneQuality.FRESH if touches <= 1 else (
                        MSNRZoneQuality.TESTED if touches == 2 else MSNRZoneQuality.EXHAUSTED
                    )
                    zones.append(
                        MSNRZone(
                            zone_type=MSNRZoneType.CLASSIC_V,
                            top_price=top_p,
                            bottom_price=bot_p,
                            level_price=bot_p,
                            consequent_encroachment_50=ce_50,
                            touches_count=touches,
                            quality=quality,
                            formed_at_utc=formed_time,
                            broken_at_utc=None,
                            is_active=True,
                        )
                    )

        return zones

    @classmethod
    def evaluate_setups(
        cls,
        symbol: str,
        candles: List[CandleRead],
        zones: List[MSNRZone],
        smt_divergence: Optional[SMTDivergenceDetail] = None,
        pip_size: float = 0.01,
    ) -> List[MSNRSetupSignal]:
        """
        Evaluates potential high-probability MSNR Alchemist trading setups:
        1. Bullish RBS Retest at 50% CE
        2. Bearish SBR Retest at 50% CE
        3. Daily Profile #2 (New York Reversal) + SMT Divergence (Gold/Silver specific)
        """
        if not candles or not zones:
            return []

        curr = candles[-1]
        curr_price = float(curr.close)
        curr_time = curr.timestamp_utc
        session_phase = cls.get_session_phase(curr_time)
        signals: List[MSNRSetupSignal] = []

        active_zones = [z for z in zones if z.is_active and z.quality != MSNRZoneQuality.EXHAUSTED]

        for z in active_zones:
            # Buffer tolerance around the 50% CE level
            ce = z.consequent_encroachment_50
            tolerance = max(40 * pip_size, curr_price * 0.004)

            # 1. Bullish RBS Retest
            if z.zone_type == MSNRZoneType.RBS and (z.bottom_price - tolerance) <= curr_price <= (z.top_price + tolerance):
                sl = round(z.bottom_price - (20 * pip_size), 4)
                risk = max(round(ce - sl, 4), 10 * pip_size)
                t1 = round(ce + (risk * 2.0), 4)
                t2 = round(ce + (risk * 3.5), 4)
                rr = round((t1 - ce) / risk, 2)

                # Base confidence score on freshness
                conf = 0.82 if z.quality == MSNRZoneQuality.FRESH else 0.70

                summary = (
                    f"MSNR Bullish RBS Retest on {symbol}: Price retesting broken resistance at {z.level_price:.2f}. "
                    f"Entry at 50% CE ({ce:.2f}) with SL {sl:.2f}."
                )

                signals.append(
                    MSNRSetupSignal(
                        symbol=symbol,
                        setup_type=MSNRSetupType.BULLISH_RBS_RETEST,
                        direction="BULLISH",
                        zone=z,
                        entry_price=ce,
                        stop_loss=sl,
                        target_1=t1,
                        target_2=t2,
                        risk_reward=rr,
                        session_phase=session_phase,
                        smt_confluence=None,
                        confidence_score=conf,
                        summary=summary,
                    )
                )

            # 2. Bearish SBR Retest
            elif z.zone_type == MSNRZoneType.SBR and (z.bottom_price - tolerance) <= curr_price <= (z.top_price + tolerance):
                sl = round(z.top_price + (20 * pip_size), 4)
                risk = max(round(sl - ce, 4), 10 * pip_size)
                t1 = round(ce - (risk * 2.0), 4)
                t2 = round(ce - (risk * 3.5), 4)
                rr = round((ce - t1) / risk, 2)

                conf = 0.82 if z.quality == MSNRZoneQuality.FRESH else 0.70

                summary = (
                    f"MSNR Bearish SBR Retest on {symbol}: Price retesting broken support at {z.level_price:.2f}. "
                    f"Entry at 50% CE ({ce:.2f}) with SL {sl:.2f}."
                )

                signals.append(
                    MSNRSetupSignal(
                        symbol=symbol,
                        setup_type=MSNRSetupType.BEARISH_SBR_RETEST,
                        direction="BEARISH",
                        zone=z,
                        entry_price=ce,
                        stop_loss=sl,
                        target_1=t1,
                        target_2=t2,
                        risk_reward=rr,
                        session_phase=session_phase,
                        smt_confluence=None,
                        confidence_score=conf,
                        summary=summary,
                    )
                )

        # 3. Daily Profile #2: New York Reversal + SMT Divergence (Gold / Silver Master Playbook)
        if smt_divergence is not None:
            # Check if we are in NY AM or London Manipulation into NY AM
            is_ny_or_london = session_phase in ("DISTRIBUTION_NY_AM", "MANIPULATION_LONDON")
            
            if is_ny_or_london:
                zone_proximity = max(100 * pip_size, curr_price * 0.02)
                if smt_divergence.divergence_type == SMTDivergenceType.BULLISH_SMT:
                    # Find closest Support / RBS zone below or near current price
                    support_zones = [
                        z for z in active_zones 
                        if z.zone_type in (MSNRZoneType.CLASSIC_V, MSNRZoneType.RBS) 
                        and abs(curr_price - z.consequent_encroachment_50) <= zone_proximity
                    ]
                    if support_zones:
                        best_zone = min(support_zones, key=lambda x: abs(curr_price - x.consequent_encroachment_50))
                        ce = best_zone.consequent_encroachment_50
                        sl = round(best_zone.bottom_price - (25 * pip_size), 4)
                        risk = max(round(curr_price - sl, 4), 10 * pip_size)
                        t1 = round(curr_price + (risk * 2.2), 4)
                        t2 = round(curr_price + (risk * 4.0), 4)
                        rr = round((t1 - curr_price) / risk, 2)

                        summary = (
                            f"Daily Profile #2 NY Bullish Reversal on {symbol}: Validated by Bullish SMT Divergence "
                            f"with {smt_divergence.correlated_symbol}. Institutional accumulation tapping MSNR zone "
                            f"at {ce:.2f}. SL at {sl:.2f}, Targeting ERL {t2:.2f}."
                        )

                        signals.append(
                            MSNRSetupSignal(
                                symbol=symbol,
                                setup_type=MSNRSetupType.DAILY_PROFILE_2_NY_REVERSAL,
                                direction="BULLISH",
                                zone=best_zone,
                                entry_price=ce,
                                stop_loss=sl,
                                target_1=t1,
                                target_2=t2,
                                risk_reward=rr,
                                session_phase=session_phase,
                                smt_confluence=smt_divergence,
                                confidence_score=0.92,
                                summary=summary,
                            )
                        )

                elif smt_divergence.divergence_type == SMTDivergenceType.BEARISH_SMT:
                    # Find closest Resistance / SBR zone above or near current price
                    res_zones = [
                        z for z in active_zones 
                        if z.zone_type in (MSNRZoneType.CLASSIC_A, MSNRZoneType.SBR) 
                        and abs(curr_price - z.consequent_encroachment_50) <= zone_proximity
                    ]
                    if res_zones:
                        best_zone = min(res_zones, key=lambda x: abs(curr_price - x.consequent_encroachment_50))
                        ce = best_zone.consequent_encroachment_50
                        sl = round(best_zone.top_price + (25 * pip_size), 4)
                        risk = max(round(sl - curr_price, 4), 10 * pip_size)
                        t1 = round(curr_price - (risk * 2.2), 4)
                        t2 = round(curr_price - (risk * 4.0), 4)
                        rr = round((curr_price - t1) / risk, 2)

                        summary = (
                            f"Daily Profile #2 NY Bearish Reversal on {symbol}: Validated by Bearish SMT Divergence "
                            f"with {smt_divergence.correlated_symbol}. Institutional distribution tapping MSNR zone "
                            f"at {ce:.2f}. SL at {sl:.2f}, Targeting ERL {t2:.2f}."
                        )

                        signals.append(
                            MSNRSetupSignal(
                                symbol=symbol,
                                setup_type=MSNRSetupType.DAILY_PROFILE_2_NY_REVERSAL,
                                direction="BEARISH",
                                zone=best_zone,
                                entry_price=ce,
                                stop_loss=sl,
                                target_1=t1,
                                target_2=t2,
                                risk_reward=rr,
                                session_phase=session_phase,
                                smt_confluence=smt_divergence,
                                confidence_score=0.92,
                                summary=summary,
                            )
                        )

        return signals

    @classmethod
    def analyze(
        cls,
        symbol: str,
        candles: List[CandleRead],
        smt_divergence: Optional[SMTDivergenceDetail] = None,
        pip_size: float = 0.01,
        left_bars: int = 2,
        right_bars: int = 2,
    ) -> MSNRAnalysisResult:
        """
        Executes end-to-end MSNR analysis for a given asset and its price history.
        """
        if not candles:
            return MSNRAnalysisResult(
                symbol=symbol,
                timestamp_utc=datetime.now(timezone.utc),
                active_zones=[],
                signals=[],
                has_active_setup=False,
                highest_quality_signal=None,
            )

        ts = candles[-1].timestamp_utc
        zones = cls.identify_msnr_zones(
            candles, pip_size=pip_size, left_bars=left_bars, right_bars=right_bars
        )
        signals = cls.evaluate_setups(
            symbol=symbol,
            candles=candles,
            zones=zones,
            smt_divergence=smt_divergence,
            pip_size=pip_size,
        )

        best_signal = max(signals, key=lambda s: s.confidence_score) if signals else None

        return MSNRAnalysisResult(
            symbol=symbol,
            timestamp_utc=ts,
            active_zones=[z for z in zones if z.is_active],
            signals=signals,
            has_active_setup=len(signals) > 0,
            highest_quality_signal=best_signal,
        )
