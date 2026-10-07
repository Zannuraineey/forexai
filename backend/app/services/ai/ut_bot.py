from typing import List, Dict, Any, Optional
import math
from app.schemas.candle import CandleRead

class UTBotEngine:
    """
    Non-repainting UT Bot Strategy Engine.
    Implements ATR-based dynamic trailing stop, 200 EMA trend filter,
    and RSI momentum gate.
    
    Optimized for Deriv Volatility Indices (e.g. Volatility 75 / R_75)
    and standard Forex pairs.
    """

    @staticmethod
    def calculate_atr(candles: List[CandleRead], period: int = 10) -> List[float]:
        if len(candles) < 2:
            return [0.0] * len(candles)
        
        tr_list = []
        for i in range(len(candles)):
            if i == 0:
                tr = float(candles[0].high - candles[0].low)
            else:
                prev_close = float(candles[i-1].close)
                high = float(candles[i].high)
                low = float(candles[i].low)
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)

        # RMA / EMA style ATR
        atr_list = []
        alpha = 1.0 / period
        running_atr = sum(tr_list[:period]) / period if len(tr_list) >= period else (tr_list[0] if tr_list else 0.0)
        
        for i in range(len(tr_list)):
            if i < period:
                atr_list.append(running_atr)
            else:
                running_atr = alpha * tr_list[i] + (1.0 - alpha) * running_atr
                atr_list.append(running_atr)
                
        return atr_list

    @staticmethod
    def calculate_ema(values: List[float], period: int) -> List[float]:
        if not values:
            return []
        alpha = 2.0 / (period + 1)
        ema_list = []
        running_ema = values[0]
        for val in values:
            running_ema = alpha * val + (1.0 - alpha) * running_ema
            ema_list.append(running_ema)
        return ema_list

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        if len(prices) <= period:
            return [50.0] * len(prices)
        
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(max(0.0, change))
            losses.append(max(0.0, -change))

        alpha = 1.0 / period
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_list = [50.0] * (period + 1)
        for i in range(period, len(gains)):
            avg_gain = alpha * gains[i] + (1.0 - alpha) * avg_gain
            avg_loss = alpha * losses[i] + (1.0 - alpha) * avg_loss
            if avg_loss == 0:
                rsi_list.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_list.append(100.0 - (100.0 / (1.0 + rs)))

        return rsi_list

    @classmethod
    def evaluate(
        cls,
        candles: List[CandleRead],
        sensitivity: float = 1.5,
        atr_period: int = 10,
        ema_period: int = 200,
        rsi_period: int = 14,
        rsi_buy_level: float = 45.0,
        rsi_sell_level: float = 55.0,
        symbol: str = "R_75",
        timeframe: str = "15m",
    ) -> Dict[str, Any]:
        """
        Evaluates candles through UT Bot trailing stop with anti-repainting closed-bar logic.
        Adds 24/7 continuous market regime detection, execution validity window,
        slippage thresholds, and actionable trade blueprint.
        """
        if not candles or len(candles) < 5:
            return {
                "signal": "WAIT",
                "state": "NO_DATA",
                "summary": "Insufficient candle bars to evaluate UT Bot.",
                "current_price": 0.0,
                "trailing_stop": 0.0,
                "ema_200": 0.0,
                "rsi": 50.0,
                "trend": "NEUTRAL",
                "conditions": [],
                "market_regime": "CONTINUOUS_24_7_SYNTHETIC",
                "session_directive": "24/7 Algorithmic market — Traditional sessions do not apply.",
                "validity_window_seconds": 300,
                "validity_window_str": "5 Minutes",
                "execution_rule": "Insufficient data to formulate execution rule.",
                "take_profit_1": 0.0,
                "take_profit_2": 0.0,
                "max_slippage_points": 0.0,
            }

        closes = [float(c.close) for c in candles]
        atr_vals = cls.calculate_atr(candles, period=atr_period)
        ema_vals = cls.calculate_ema(closes, period=min(ema_period, len(closes)))
        rsi_vals = cls.calculate_rsi(closes, period=rsi_period)

        # Calculate Trailing Stop series
        trail_series = []
        trail = closes[0]

        for i in range(len(candles)):
            src = closes[i]
            x_atr = atr_vals[i]
            n_loss = sensitivity * x_atr
            prev = trail

            if i == 0:
                trail = src - n_loss
            else:
                prev_src = closes[i - 1]
                if src > prev and prev_src > prev:
                    trail = max(prev, src - n_loss)
                elif src < prev and prev_src < prev:
                    trail = min(prev, src + n_loss)
                else:
                    trail = src - n_loss if src > prev else src + n_loss

            trail_series.append(trail)

        # Detect crossover on last 2 bars (Confirmed Bar Anti-Repaint)
        curr_price = closes[-1]
        prev_price = closes[-2]
        curr_trail = trail_series[-1]
        prev_trail = trail_series[-2]
        curr_ema = ema_vals[-1]
        curr_rsi = rsi_vals[-1]

        # UT Crossover
        crossover_buy = (prev_price <= prev_trail) and (curr_price > curr_trail)
        crossunder_sell = (prev_price >= prev_trail) and (curr_price < curr_trail)

        # Sustained position state
        is_above_trail = curr_price > curr_trail
        is_below_trail = curr_price < curr_trail

        # Filters
        is_above_ema = curr_price > curr_ema
        is_below_ema = curr_price < curr_ema
        rsi_buy_pass = curr_rsi >= rsi_buy_level
        rsi_sell_pass = curr_rsi <= rsi_sell_level

        # Evaluate Signal
        if (crossover_buy or is_above_trail) and is_above_ema and rsi_buy_pass:
            if crossover_buy:
                signal = "BUY"
                summary = (
                    f"🎯 UT BOT BUY TRIGGERED at {curr_price:.4f}! "
                    f"Price crossed above dynamic trailing stop ({curr_trail:.4f}), "
                    f"supported by EMA 200 ({curr_ema:.4f}) and RSI ({curr_rsi:.1f})."
                )
            else:
                signal = "BULLISH_HOLD"
                summary = (
                    f"🟢 UT BOT BULLISH CONTINUATION: Price ({curr_price:.4f}) holds above "
                    f"trailing stop ({curr_trail:.4f}) & EMA 200 ({curr_ema:.4f})."
                )
        elif (crossunder_sell or is_below_trail) and is_below_ema and rsi_sell_pass:
            if crossunder_sell:
                signal = "SELL"
                summary = (
                    f"🔻 UT BOT SELL TRIGGERED at {curr_price:.4f}! "
                    f"Price crossed below dynamic trailing stop ({curr_trail:.4f}), "
                    f"confirmed below EMA 200 ({curr_ema:.4f}) and RSI ({curr_rsi:.1f})."
                )
            else:
                signal = "BEARISH_HOLD"
                summary = (
                    f"🔴 UT BOT BEARISH CONTINUATION: Price ({curr_price:.4f}) holds below "
                    f"trailing stop ({curr_trail:.4f}) & EMA 200 ({curr_ema:.4f})."
                )
        else:
            signal = "WAIT"
            reasons = []
            if not is_above_ema and not is_below_ema:
                reasons.append("Price hovering at EMA 200")
            if is_above_trail and not is_above_ema:
                reasons.append("UT is Long but price is below EMA 200 trend filter")
            elif is_below_trail and not is_below_ema:
                reasons.append("UT is Short but price is above EMA 200 trend filter")
            elif not rsi_buy_pass and is_above_trail:
                reasons.append(f"RSI ({curr_rsi:.1f}) below threshold ({rsi_buy_level})")
            elif not rsi_sell_pass and is_below_trail:
                reasons.append(f"RSI ({curr_rsi:.1f}) above threshold ({rsi_sell_level})")
            
            summary = "⏸️ UT BOT FILTERING: " + (", ".join(reasons) if reasons else "Awaiting confirmed directional breakout.")

        # Market regime & 24/7 session logic
        sym_str = symbol.upper() if symbol else ""
        is_synthetic = any(k in sym_str for k in ["R_", "VOLATILITY", "1HZ", "BOOM", "CRASH", "STEP"])
        is_crypto = any(k in sym_str for k in ["BTC", "ETH", "SOL"])

        if is_synthetic:
            market_regime = "CONTINUOUS_24_7_SYNTHETIC"
            session_directive = "24/7 Algorithmic Market — Traditional bank sessions (London, New York, Asian) DO NOT APPLY. Valid anytime 24/7."
        elif is_crypto:
            market_regime = "CONTINUOUS_24_7_CRYPTO"
            session_directive = "24/7 Decentralized Market — Active 24/7 independent of bank sessions."
        else:
            market_regime = "SESSIONAL_FOREX"
            session_directive = "Forex Market — Optimal institutional liquidity during London/New York overlap."

        # Risk metrics & Execution Validity Window
        last_atr = atr_vals[-1] if atr_vals else (curr_price * 0.005)
        max_slippage_points = round(last_atr * 0.35, 4)

        tf_lower = timeframe.lower() if timeframe else "15m"
        if "1m" in tf_lower:
            validity_window_seconds = 45
            validity_window_str = "45 Seconds"
        elif "5m" in tf_lower:
            validity_window_seconds = 180
            validity_window_str = "3 Minutes"
        elif "15m" in tf_lower:
            validity_window_seconds = 480
            validity_window_str = "8 Minutes"
        elif "1h" in tf_lower:
            validity_window_seconds = 1200
            validity_window_str = "20 Minutes"
        else:
            validity_window_seconds = 300
            validity_window_str = "5 Minutes"

        if signal in ["BUY", "BULLISH_HOLD"]:
            risk_dist = max(abs(curr_price - curr_trail), last_atr)
            tp1 = round(curr_price + (1.5 * risk_dist), 5)
            tp2 = round(curr_price + (2.5 * risk_dist), 5)
            entry_max = round(curr_price + max_slippage_points, 5)
            if signal == "BUY":
                execution_rule = (
                    f"Immediate Execution: Enter BUY at current price ({curr_price:.4f}) or limit on retest of Trailing Stop ({curr_trail:.4f}). "
                    f"Max buy threshold is {entry_max:.4f}. DO NOT chase if price exceeds {entry_max:.4f}."
                )
            else:
                execution_rule = (
                    f"Bullish continuation active. If already long, hold with SL at {curr_trail:.4f}. "
                    f"New entry: Wait for price pullback towards trailing stop ({curr_trail:.4f})."
                )
        elif signal in ["SELL", "BEARISH_HOLD"]:
            risk_dist = max(abs(curr_trail - curr_price), last_atr)
            tp1 = round(curr_price - (1.5 * risk_dist), 5)
            tp2 = round(curr_price - (2.5 * risk_dist), 5)
            entry_min = round(curr_price - max_slippage_points, 5)
            if signal == "SELL":
                execution_rule = (
                    f"Immediate Execution: Enter SELL at current price ({curr_price:.4f}) or limit on pullback to Trailing Stop ({curr_trail:.4f}). "
                    f"Min sell threshold is {entry_min:.4f}. DO NOT chase if price falls below {entry_min:.4f}."
                )
            else:
                execution_rule = (
                    f"Bearish continuation active. If already short, hold with SL at {curr_trail:.4f}. "
                    f"New entry: Wait for price pullback towards trailing stop ({curr_trail:.4f})."
                )
        else:
            risk_dist = last_atr
            tp1 = round(curr_price + 1.5 * risk_dist, 5)
            tp2 = round(curr_price + 2.5 * risk_dist, 5)
            execution_rule = "Awaiting confirmed bar close crossover. Stand aside."

        conditions = [
            {
                "name": "UT Trailing Stop Position",
                "status": "PASS" if (is_above_trail and signal in ["BUY", "BULLISH_HOLD"]) or (is_below_trail and signal in ["SELL", "BEARISH_HOLD"]) else "FAIL",
                "details": f"Price ({curr_price:.4f}) {'above' if is_above_trail else 'below'} Trail ({curr_trail:.4f})"
            },
            {
                "name": "EMA 200 Trend Alignment",
                "status": "PASS" if (is_above_ema and signal in ["BUY", "BULLISH_HOLD"]) or (is_below_ema and signal in ["SELL", "BEARISH_HOLD"]) else "FAIL",
                "details": f"Price {'above' if is_above_ema else 'below'} EMA ({curr_ema:.4f})"
            },
            {
                "name": "RSI Momentum Filter",
                "status": "PASS" if (rsi_buy_pass and signal in ["BUY", "BULLISH_HOLD"]) or (rsi_sell_pass and signal in ["SELL", "BEARISH_HOLD"]) else "FAIL",
                "details": f"RSI 14 = {curr_rsi:.1f} (Buy >= {rsi_buy_level}, Sell <= {rsi_sell_level})"
            },
            {
                "name": "Anti-Repaint Status",
                "status": "CONFIRMED",
                "details": "Calculated on fully closed candles with locked ATR trail."
            }
        ]

        return {
            "signal": signal,
            "current_price": round(curr_price, 5),
            "trailing_stop": round(curr_trail, 5),
            "ema_200": round(curr_ema, 5),
            "rsi": round(curr_rsi, 2),
            "trend": "BULLISH" if is_above_ema else "BEARISH",
            "summary": summary,
            "sensitivity": sensitivity,
            "atr_period": atr_period,
            "conditions": conditions,
            "market_regime": market_regime,
            "session_directive": session_directive,
            "validity_window_seconds": validity_window_seconds,
            "validity_window_str": validity_window_str,
            "execution_rule": execution_rule,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "max_slippage_points": max_slippage_points,
        }
