from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.candle import CandleRead
from app.schemas import (
    SMTDivergenceDetail,
    SMTDivergenceType,
    SMTPairGroup,
    SMTContext,
)

logger = logging.getLogger("forex_ai.smt_engine")

class SMTEngine:
    """
    Institutional Smart Money Tool (SMT) Divergence Engine.
    Detects non-conforming swing highs/lows between positively correlated instruments:
    - Precious Metals: XAUUSD (Gold) vs XAGUSD (Silver)
    - Forex Majors: EURUSD (Fiber) vs GBPUSD (Cable)
    
    Identifies institutional accumulation (Bullish SMT) and distribution (Bearish SMT)
    before major intermarket expansions.
    """

    CORRELATED_MAPPINGS: Dict[str, Tuple[str, SMTPairGroup]] = {
        "XAUUSD": ("XAGUSD", SMTPairGroup.METALS),
        "XAGUSD": ("XAUUSD", SMTPairGroup.METALS),
        "EURUSD": ("GBPUSD", SMTPairGroup.MAJORS),
        "GBPUSD": ("EURUSD", SMTPairGroup.MAJORS),
    }

    @classmethod
    def get_correlated_symbol(cls, symbol: str) -> Optional[Tuple[str, SMTPairGroup]]:
        sym = symbol.upper()
        return cls.CORRELATED_MAPPINGS.get(sym)

    @classmethod
    def detect_divergence_from_session_levels(
        cls,
        symbol_a: str,
        session_levels_a: Optional[Dict[str, Any]],
        symbol_b: str,
        session_levels_b: Optional[Dict[str, Any]],
        session_name: str = "asian",
        pair_group: SMTPairGroup = SMTPairGroup.METALS,
    ) -> Optional[SMTDivergenceDetail]:
        """
        Detects SMT divergence based on session sweeps (e.g. Asian or London session extremes).
        """
        if not session_levels_a or not session_levels_b:
            return None

        lvl_a = session_levels_a.get(session_name)
        lvl_b = session_levels_b.get(session_name)
        if not lvl_a or not lvl_b:
            return None

        swept_low_a = bool(getattr(lvl_a, "swept_low", False) if hasattr(lvl_a, "swept_low") else lvl_a.get("swept_low", False))
        swept_low_b = bool(getattr(lvl_b, "swept_low", False) if hasattr(lvl_b, "swept_low") else lvl_b.get("swept_low", False))
        swept_high_a = bool(getattr(lvl_a, "swept_high", False) if hasattr(lvl_a, "swept_high") else lvl_a.get("swept_high", False))
        swept_high_b = bool(getattr(lvl_b, "swept_high", False) if hasattr(lvl_b, "swept_high") else lvl_b.get("swept_high", False))

        # 1. Bullish SMT: One sweeps session low, other holds higher low
        if swept_low_a and not swept_low_b:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BULLISH_SMT,
                swept_symbol=symbol_a,
                strong_symbol=symbol_b,
                reference_level=f"{session_name.upper()}_LOW",
                primary_price_action="LOWER_LOW_SWEEP",
                correlated_price_action="HIGHER_LOW_REJECTION",
                confidence_score=0.90,
                summary=(
                    f"Bullish SMT Divergence detected: {symbol_a} swept {session_name.title()} Low, "
                    f"while {symbol_b} refused to break structure and held a Higher Low."
                ),
            )
        elif swept_low_b and not swept_low_a:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BULLISH_SMT,
                swept_symbol=symbol_b,
                strong_symbol=symbol_a,
                reference_level=f"{session_name.upper()}_LOW",
                primary_price_action="HIGHER_LOW_REJECTION",
                correlated_price_action="LOWER_LOW_SWEEP",
                confidence_score=0.90,
                summary=(
                    f"Bullish SMT Divergence detected: {symbol_b} swept {session_name.title()} Low, "
                    f"while {symbol_a} refused to break structure and held a Higher Low."
                ),
            )

        # 2. Bearish SMT: One sweeps session high, other forms lower high
        if swept_high_a and not swept_high_b:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BEARISH_SMT,
                swept_symbol=symbol_a,
                strong_symbol=symbol_b,
                reference_level=f"{session_name.upper()}_HIGH",
                primary_price_action="HIGHER_HIGH_SWEEP",
                correlated_price_action="LOWER_HIGH_REJECTION",
                confidence_score=0.90,
                summary=(
                    f"Bearish SMT Divergence detected: {symbol_a} swept {session_name.title()} High, "
                    f"while {symbol_b} refused to break structure and held a Lower High."
                ),
            )
        elif swept_high_b and not swept_high_a:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BEARISH_SMT,
                swept_symbol=symbol_b,
                strong_symbol=symbol_a,
                reference_level=f"{session_name.upper()}_HIGH",
                primary_price_action="LOWER_HIGH_REJECTION",
                correlated_price_action="HIGHER_HIGH_SWEEP",
                confidence_score=0.90,
                summary=(
                    f"Bearish SMT Divergence detected: {symbol_b} swept {session_name.title()} High, "
                    f"while {symbol_a} refused to break structure and held a Lower High."
                ),
            )

        return None

    @classmethod
    def detect_divergence_from_candles(
        cls,
        symbol_a: str,
        candles_a: List[Any],
        symbol_b: str,
        candles_b: List[Any],
        lookback: int = 15,
        pair_group: SMTPairGroup = SMTPairGroup.METALS,
    ) -> Optional[SMTDivergenceDetail]:
        """
        Detects SMT divergence between recent swing highs and swing lows in candle series.
        """
        if len(candles_a) < lookback or len(candles_b) < lookback:
            return None

        recent_a = candles_a[-lookback:]
        recent_b = candles_b[-lookback:]

        # Split into first half (reference anchor) and second half (test extreme)
        half = lookback // 2
        anchor_a, test_a = recent_a[:half], recent_a[half:]
        anchor_b, test_b = recent_b[:half], recent_b[half:]

        min_anc_a, min_test_a = min(c.low for c in anchor_a), min(c.low for c in test_a)
        min_anc_b, min_test_b = min(c.low for c in anchor_b), min(c.low for c in test_b)

        max_anc_a, max_test_a = max(c.high for c in anchor_a), max(c.high for c in test_a)
        max_anc_b, max_test_b = max(c.high for c in anchor_b), max(c.high for c in test_b)

        # Bullish SMT: A breaks below anchor (LL), B stays above anchor (HL)
        a_made_lower_low = min_test_a < min_anc_a
        b_made_lower_low = min_test_b < min_anc_b

        if a_made_lower_low and not b_made_lower_low:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BULLISH_SMT,
                swept_symbol=symbol_a,
                strong_symbol=symbol_b,
                reference_level="SWING_LOW",
                primary_price_action="LOWER_LOW",
                correlated_price_action="HIGHER_LOW",
                confidence_score=0.85,
                summary=(
                    f"Bullish SMT Divergence: {symbol_a} swept swing low to lower low, "
                    f"whereas correlated {symbol_b} maintained a Higher Low."
                ),
            )
        elif b_made_lower_low and not a_made_lower_low:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BULLISH_SMT,
                swept_symbol=symbol_b,
                strong_symbol=symbol_a,
                reference_level="SWING_LOW",
                primary_price_action="HIGHER_LOW",
                correlated_price_action="LOWER_LOW",
                confidence_score=0.85,
                summary=(
                    f"Bullish SMT Divergence: {symbol_b} swept swing low to lower low, "
                    f"whereas {symbol_a} maintained a Higher Low showing relative strength."
                ),
            )

        # Bearish SMT: A breaks above anchor (HH), B stays below anchor (LH)
        a_made_higher_high = max_test_a > max_anc_a
        b_made_higher_high = max_test_b > max_anc_b

        if a_made_higher_high and not b_made_higher_high:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BEARISH_SMT,
                swept_symbol=symbol_a,
                strong_symbol=symbol_b,
                reference_level="SWING_HIGH",
                primary_price_action="HIGHER_HIGH",
                correlated_price_action="LOWER_HIGH",
                confidence_score=0.85,
                summary=(
                    f"Bearish SMT Divergence: {symbol_a} swept swing high to higher high, "
                    f"whereas correlated {symbol_b} failed to make a new high (Lower High)."
                ),
            )
        elif b_made_higher_high and not a_made_higher_high:
            return SMTDivergenceDetail(
                pair_group=pair_group,
                primary_symbol=symbol_a,
                correlated_symbol=symbol_b,
                divergence_type=SMTDivergenceType.BEARISH_SMT,
                swept_symbol=symbol_b,
                strong_symbol=symbol_a,
                reference_level="SWING_HIGH",
                primary_price_action="LOWER_HIGH",
                correlated_price_action="HIGHER_HIGH",
                confidence_score=0.85,
                summary=(
                    f"Bearish SMT Divergence: {symbol_b} swept swing high to higher high, "
                    f"whereas {symbol_a} failed to make a new high (Lower High)."
                ),
            )

        return None

    @classmethod
    async def evaluate_smt_for_symbol(
        cls,
        symbol: str,
        db: AsyncSession,
        timeframe: str = "15m",
        session_levels: Optional[Dict[str, Any]] = None,
    ) -> SMTContext:
        """
        Asynchronously loads correlated pair candles from CandleService and computes SMT divergence state.
        """
        sym = symbol.upper()
        mapping = cls.get_correlated_symbol(sym)
        if not mapping:
            return SMTContext(symbol=sym, has_smt_divergence=False)

        corr_sym, pair_group = mapping

        from app.services.candle_service import CandleService
        candle_svc = CandleService(db)

        candles_a = await candle_svc.get_candles(sym, timeframe=timeframe, limit=30, auto_fetch=False)
        candles_b = await candle_svc.get_candles(corr_sym, timeframe=timeframe, limit=30, auto_fetch=False)

        div_detail = None

        # 1. Try session-level divergence if session levels provided
        if session_levels:
            for s_name in ["asian", "london"]:
                div_detail = cls.detect_divergence_from_session_levels(
                    symbol_a=sym,
                    session_levels_a=session_levels,
                    symbol_b=corr_sym,
                    session_levels_b=session_levels, # or query other if available
                    session_name=s_name,
                    pair_group=pair_group,
                )
                if div_detail:
                    break

        # 2. Try candle swing divergence if session didn't trigger
        if not div_detail and candles_a and candles_b:
            div_detail = cls.detect_divergence_from_candles(
                symbol_a=sym,
                candles_a=candles_a,
                symbol_b=corr_sym,
                candles_b=candles_b,
                pair_group=pair_group,
            )

        if div_detail:
            confluence = "BULLISH" if div_detail.divergence_type == SMTDivergenceType.BULLISH_SMT else "BEARISH"
            return SMTContext(
                symbol=sym,
                correlated_symbol=corr_sym,
                has_smt_divergence=True,
                active_divergence=div_detail,
                all_correlations=[div_detail],
                confluence_bias=confluence,
                confidence_boost=0.15,
            )

        return SMTContext(
            symbol=sym,
            correlated_symbol=corr_sym,
            has_smt_divergence=False,
            confluence_bias="NEUTRAL",
            confidence_boost=0.0,
        )
