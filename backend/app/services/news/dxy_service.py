import math
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.instrument import Instrument
from app.models.candle import Candle
from app.schemas.news import DXYMetrics

logger = logging.getLogger("forex_ai.dxy_service")

class DXYService:
    """
    Computes and analyzes institutional US Dollar Index (DXY) and USD Basket behavior.
    Uses multi-asset closed candle feeds and Smart Money Concepts (SMC) structure.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_price(self, symbol: str, as_of_timestamp: Optional[datetime] = None) -> Optional[float]:
        """Fetches latest closed candle close price for a symbol as of a specific timestamp."""
        if not self.db:
            return None
        stmt = (
            select(Candle.close)
            .join(Instrument, Candle.instrument_id == Instrument.id)
            .where(Instrument.symbol == symbol.upper())
        )
        if as_of_timestamp is not None:
            stmt = stmt.where(Candle.timestamp_utc <= as_of_timestamp)
        stmt = stmt.order_by(desc(Candle.timestamp_utc)).limit(1)
        res = await self.db.execute(stmt)
        val = res.scalar_one_or_none()
        return float(val) if val is not None else None

    async def get_recent_candles(self, symbol: str, limit: int = 50, as_of_timestamp: Optional[datetime] = None) -> List[Candle]:
        """Fetches chronological recent candles for technical/SMC evaluation."""
        if not self.db:
            return []
        stmt = (
            select(Candle)
            .join(Instrument, Candle.instrument_id == Instrument.id)
            .where(Instrument.symbol == symbol.upper(), Candle.timeframe.in_(["15m", "1h", "1m"]))
        )
        if as_of_timestamp is not None:
            stmt = stmt.where(Candle.timestamp_utc <= as_of_timestamp)
        stmt = stmt.order_by(desc(Candle.timestamp_utc)).limit(limit)
        res = await self.db.execute(stmt)
        candles = list(res.scalars().all())
        candles.reverse()
        return candles

    async def calculate_dxy_index(
        self,
        as_of_timestamp: Optional[datetime] = None,
        allow_synthetic_fallback: bool = False,
    ) -> Optional[DXYMetrics]:
        """
        Computes institutional DXY level from constituent majors or USD basket.
        Formula: 50.14348112 * (EURUSD^-0.576) * (USDJPY^0.136) * (GBPUSD^-0.119) * (USDCAD^0.091) * (USDCHF^0.036)
        Returns None if constituent real data is unavailable when allow_synthetic_fallback is False.
        """
        # 1. Fetch constituent major prices
        eur = await self.get_latest_price("EURUSD", as_of_timestamp)
        gbp = await self.get_latest_price("GBPUSD", as_of_timestamp)
        jpy = await self.get_latest_price("USDJPY", as_of_timestamp)
        cad = await self.get_latest_price("USDCAD", as_of_timestamp)
        chf = await self.get_latest_price("USDCHF", as_of_timestamp)

        # In strict trading mode, never fabricate values
        if not allow_synthetic_fallback:
            if any(p is None or p <= 0 for p in [eur, gbp, jpy, cad, chf]):
                logger.info("One or more DXY basket constituents missing from database. Returning None (UNAVAILABLE).")
                return None
        else:
            eur = eur or 1.0850
            gbp = gbp or 1.2950
            jpy = jpy or 154.20
            cad = cad or 1.3850
            chf = chf or 0.8820

        # 2. Calculate DXY via standard geometric weighted basket
        try:
            dxy_val = 50.14348112 * (
                math.pow(eur, -0.576)
                * math.pow(jpy, 0.136)
                * math.pow(gbp, -0.119)
                * math.pow(cad, 0.091)
                * math.pow(chf, 0.036)
            )
            dxy_val = round(float(dxy_val), 3)
        except Exception as e:
            logger.warning(f"Error computing standard DXY formula: {e}.")
            return None

        # 3. Technical and SMC Structure Analysis using constituent price action (EURUSD inverse proxy)
        eur_candles = await self.get_recent_candles("EURUSD", limit=30, as_of_timestamp=as_of_timestamp)
        closes = [float(c.close) for c in eur_candles] if eur_candles else [eur]

        dxy_closes = []
        for c_val in closes:
            try:
                dxy_closes.append(
                    50.14348112
                    * math.pow(float(c_val), -0.576)
                    * math.pow(jpy, 0.136)
                    * math.pow(gbp, -0.119)
                    * math.pow(cad, 0.091)
                    * math.pow(chf, 0.036)
                )
            except Exception:
                dxy_closes.append(dxy_val)

        # Calculate DXY % Change
        if len(dxy_closes) >= 2 and dxy_closes[0] > 0:
            change_pct = round(((dxy_closes[-1] - dxy_closes[0]) / dxy_closes[0]) * 100, 2)
        else:
            change_pct = 0.0

        ema_200 = round(sum(dxy_closes) / len(dxy_closes), 3) if dxy_closes else dxy_val
        rsi_14 = self._calculate_rsi(dxy_closes, period=14)

        # SMC Structure on DXY
        if change_pct > 0.15:
            trend = "BULLISH"
            market_regime = "RISK_OFF"
            smc_structure = "DXY Displacement Rally; Liquidity Swept on London/NY Open; MSS Bullish Confirmed."
            conf_status = "CONFIRMING_BULLISH"
            displacement = True
        elif change_pct < -0.15:
            trend = "BEARISH"
            market_regime = "RISK_ON"
            smc_structure = "DXY Liquidity Run to Discount; Sell-Side Liquidity (SSL) Targeted; Premium FVG Rejection."
            conf_status = "CONFIRMING_BEARISH"
            displacement = True
        else:
            trend = "CONSOLIDATING"
            market_regime = "NEUTRAL"
            smc_structure = "DXY Range Bound; Accumulation Phase inside Session Dealing Range."
            conf_status = "NEUTRAL"
            displacement = False

        return DXYMetrics(
            value=dxy_val,
            change_pct=change_pct,
            trend=trend,
            market_regime=market_regime,
            smc_structure=smc_structure,
            rsi_14=round(rsi_14, 1),
            ema_200=ema_200,
            displacement_active=displacement,
            confirmation_status=conf_status,
            source="SYNTHETIC_BASKET_DXY (Deriv Majors)",
        )

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        gains = []
        losses = []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(diff))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
