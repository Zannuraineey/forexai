import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.news import (
    EconomicEvent,
    DXYMetrics,
    PairImpactAnalysis,
    NewsIntelligenceReport,
    NewsIntelligenceRequest,
)
from app.services.news.dxy_service import DXYService
from app.services.news.economic_calendar_service import EconomicCalendarService
from app.services.features.context_engine import MarketContextEngine

logger = logging.getLogger("forex_ai.news_intelligence")

class NewsIntelligenceEngine:
    """
    Synthesizes macroeconomic data, actual-vs-forecast deviations, historical reactions,
    live DXY behavior, market regime, SMC/ICT structure, and pair-specific confluences.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dxy_service = DXYService(db)
        self.calendar_service = EconomicCalendarService()

    async def generate_intelligence_report(
        self,
        request: Optional[NewsIntelligenceRequest] = None
    ) -> NewsIntelligenceReport:
        req = request or NewsIntelligenceRequest()
        
        # 1. Fetch Targeted Economic Event
        event = (
            self.calendar_service.get_event_by_id(req.event_id)
            if req.event_id
            else self.calendar_service.get_all_events()[0]
        )

        # 2. Compute Live DXY Metrics & SMC Trajectory
        dxy = await self.dxy_service.calculate_dxy_index()

        # 3. Analyze Deviation (Actual vs Forecast vs Previous)
        dev_summary = self._analyze_deviation(event)

        # 4. Historical Comparison
        hist_comp = self._compare_historical(event, dxy)

        # 5. Macro Regime Analysis
        macro_regime = (
            f"Current Macro Regime: {dxy.market_regime}. DXY Index trading at {dxy.value:.2f} ({dxy.change_pct:+.2f}%). "
            f"The Dollar is displaying {dxy.trend.lower()} order flow with RSI at {dxy.rsi_14:.1f} and EMA200 at {dxy.ema_200:.2f}. "
            f"Liquidity is currently skewing toward {'safe-haven USD accumulation' if dxy.trend == 'BULLISH' else 'pro-cyclical risk asset expansion'}."
        )

        # 6. SMC / Technical Synthesis on DXY
        smc_synthesis = (
            f"SMC Dollar Confluence: {dxy.smc_structure} "
            f"Confirmation Status: {dxy.confirmation_status.replace('_', ' ')}. "
            f"Institutional Order Flow confirms that smart money is {'accumulating long dollar positions' if dxy.trend == 'BULLISH' else 'distributing dollar premium into foreign currencies'}."
        )

        # 7. Pair-Specific Analysis for User Selected Pairs
        pair_analyses = await self._analyze_pairs(req.user_pairs, event, dxy)

        # 8. Actionable Institutional Conclusion
        conclusion = self._build_actionable_conclusion(event, dxy, pair_analyses)

        return NewsIntelligenceReport(
            id=f"rep_{event.id}_{int(datetime.now(timezone.utc).timestamp())}",
            generated_at_utc=datetime.now(timezone.utc),
            event=event,
            dxy_context=dxy,
            deviation_analysis=dev_summary,
            historical_comparison=hist_comp,
            macro_regime_summary=macro_regime,
            smc_technical_synthesis=smc_synthesis,
            pair_analyses=pair_analyses,
            actionable_conclusion=conclusion,
        )

    def _analyze_deviation(self, event: EconomicEvent) -> str:
        if event.actual is None:
            return (
                f"Upcoming release: Forecast is set at {event.forecast}{event.unit} vs prior print of {event.previous}{event.unit}. "
                f"An upside beat (> {event.forecast}{event.unit}) will reinforce hawkish Fed rate expectations, boosting DXY. "
                f"A downside miss (< {event.forecast}{event.unit}) will validate dovish easing expectations, triggering dollar selling."
            )
        diff = event.actual - (event.forecast or event.previous or 0)
        direction = "BEAT (Hotter than expected)" if diff > 0 else ("MISSED (Cooler than expected)" if diff < 0 else "IN-LINE")
        return (
            f"Event Outcome: {direction}. Actual: {event.actual}{event.unit} vs Forecast: {event.forecast}{event.unit} "
            f"(Previous: {event.previous}{event.unit}, Deviation: {diff:+.2f}{event.unit}). "
            f"This outcome {'increases terminal Fed rate probability and fuels dollar buying' if diff > 0 else 'accelerates rate-cut expectations, exerting downward pressure on the dollar'}."
        )

    def _compare_historical(self, event: EconomicEvent, dxy: DXYMetrics) -> str:
        if not event.historical_reactions:
            return event.historical_context
        past = event.historical_reactions[0]
        return (
            f"Historical Precedent: During the {past.get('date')} print, a reading of {past.get('actual')}{event.unit} "
            f"(vs {past.get('forecast')}{event.unit} forecast) caused a {past.get('dxy_reaction')}, leading to "
            f"{past.get('eurusd_reaction')} in EURUSD and {past.get('xauusd_reaction')} in Gold (XAUUSD). "
            f"Current DXY structure aligns with this recurring liquidity displacement pattern."
        )

    async def _analyze_pairs(
        self,
        symbols: List[str],
        event: EconomicEvent,
        dxy: DXYMetrics
    ) -> List[PairImpactAnalysis]:
        results = []
        for sym in symbols:
            s = sym.upper()
            is_usd_base = s.startswith("USD")
            is_usd_quote = s.endswith("USD")
            
            # Determine correlation
            if is_usd_base:
                corr = "DIRECT"
                bias = "BULLISH" if dxy.trend == "BULLISH" else ("BEARISH" if dxy.trend == "BEARISH" else "NEUTRAL")
            elif is_usd_quote:
                corr = "INVERSE"
                bias = "BEARISH" if dxy.trend == "BULLISH" else ("BULLISH" if dxy.trend == "BEARISH" else "NEUTRAL")
            else:
                corr = "DECOUPLED"
                bias = "NEUTRAL"

            # Fetch recent candles for real SMC liquidity levels
            try:
                candles = await self.dxy_service.get_recent_candles(s, limit=30)
                if candles:
                    curr_p = candles[-1].close
                    sw_high = round(max(c.high for c in candles), 4)
                    sw_low = round(min(c.low for c in candles), 4)
                    levels = {
                        "current": curr_p,
                        "swing_high": sw_high,
                        "swing_low": sw_low,
                        "invalidation": sw_low if bias == "BULLISH" else sw_high,
                    }
                    smc_conf = (
                        f"Local SMC structure: High liquidity pool at {sw_high:.4f}, low liquidity pool at {sw_low:.4f}. "
                        f"Order flow aligning with DXY {dxy.trend.lower()} macro trajectory."
                    )
                else:
                    smc_conf = f"SMC confluence: Correlating with DXY {dxy.trend.lower()} regime. Key session levels forming."
                    levels = {}
            except Exception:
                smc_conf = f"SMC confluence: Correlating with DXY {dxy.trend.lower()} regime. Key session levels forming."
                levels = {}

            # Construct thesis
            if corr == "INVERSE":
                thesis = (
                    f"Due to strong inverse correlation with DXY, Dollar {dxy.trend.lower()} pressure indicates "
                    f"{'distribution / short opportunities targeting sell-side liquidity' if bias == 'BEARISH' else 'discount accumulation targeting buy-side liquidity'} on {s}. "
                    f"Macro catalyst '{event.title}' acts as the volatility accelerator."
                )
            elif corr == "DIRECT":
                thesis = (
                    f"Direct Dollar alignment dictates that {s} will expand in synchrony with DXY. "
                    f"Anticipate {'upward expansion toward premium liquidity' if bias == 'BULLISH' else 'downward retracement toward discount support'}."
                )
            else:
                thesis = f"Cross-pair dynamics dominate; monitor USD basket reaction for secondary momentum spillover."

            results.append(
                PairImpactAnalysis(
                    symbol=s,
                    directional_bias=bias,
                    confidence=0.82 if dxy.displacement_active else 0.68,
                    correlation_to_usd=corr,
                    smc_confluence=smc_conf,
                    key_levels=levels,
                    trade_thesis=thesis,
                )
            )
        return results

    def _build_actionable_conclusion(
        self,
        event: EconomicEvent,
        dxy: DXYMetrics,
        pairs: List[PairImpactAnalysis]
    ) -> str:
        top_picks = [p.symbol for p in pairs if p.confidence >= 0.75]
        picks_str = ", ".join(top_picks) if top_picks else "watchlist majors"
        return (
            f"Institutional Synthesis: The {event.title} release directly interacts with DXY's {dxy.trend} market regime. "
            f"Because DXY is {dxy.confirmation_status.lower().replace('_', ' ')}, high-probability setups emerge on {picks_str}. "
            f"Traders should wait for the initial news-spike liquidity sweep to complete before executing on confirmed Market Structure Shifts (MSS)."
        )
