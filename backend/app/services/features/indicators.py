import math
from typing import Dict, List, Optional
from app.schemas.candle import CandleRead

class TechnicalIndicators:
    """
    Institutional technical indicator suite.
    Calculated purely as neutral, deterministic mathematical market context.
    Does NOT assert buy/sell signals or strategy assumptions.
    """

    @staticmethod
    def calculate_ema(closes: List[float], period: int) -> List[Optional[float]]:
        """
        Exponential Moving Average (EMA).
        Alpha = 2 / (period + 1)
        """
        n = len(closes)
        if n < period or period <= 0:
            return [None] * n

        emas: List[Optional[float]] = [None] * (period - 1)
        # Seed with initial SMA
        initial_sma = sum(closes[:period]) / period
        emas.append(round(initial_sma, 6))

        alpha = 2.0 / (period + 1)
        for i in range(period, n):
            prev_ema = emas[-1]
            current_ema = (closes[i] * alpha) + (prev_ema * (1.0 - alpha))
            emas.append(round(current_ema, 6))

        return emas

    @staticmethod
    def calculate_atr(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> List[Optional[float]]:
        """
        Average True Range (ATR) with Wilder's smoothing.
        True Range (TR) = max(H - L, |H - PrevC|, |L - PrevC|)
        """
        n = len(closes)
        if n < period + 1 or period <= 0:
            return [None] * n

        # 1. Compute True Range (TR)
        tr_list: List[float] = [highs[0] - lows[0]]
        for i in range(1, n):
            h = highs[i]
            l = lows[i]
            prev_c = closes[i - 1]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)

        # 2. Initial SMA of TR
        atrs: List[Optional[float]] = [None] * (period - 1)
        initial_atr = sum(tr_list[:period]) / period
        atrs.append(round(initial_atr, 6))

        # 3. Wilder's Smoothing: ATR_t = (ATR_{t-1} * (period - 1) + TR_t) / period
        for i in range(period, n):
            prev_atr = atrs[-1]
            current_atr = ((prev_atr * (period - 1)) + tr_list[i]) / period
            atrs.append(round(current_atr, 6))

        return atrs

    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
        """
        Relative Strength Index (RSI) using Wilder's smoothed averages.
        """
        n = len(closes)
        if n < period + 1 or period <= 0:
            return [None] * n

        # Price changes
        gains: List[float] = []
        losses: List[float] = []
        for i in range(1, n):
            delta = closes[i] - closes[i - 1]
            gains.append(max(delta, 0.0))
            losses.append(max(-delta, 0.0))

        # Initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsis: List[Optional[float]] = [None] * period
        if avg_loss == 0.0:
            rsis.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsis.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

        # Wilder's smoothing
        for i in range(period, len(gains)):
            avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

            if avg_loss == 0.0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = round(100.0 - (100.0 / (1.0 + rs)), 2)
            rsis.append(rsi)

        return rsis

    @staticmethod
    def calculate_macd(
        closes: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, List[Optional[float]]]:
        """
        Moving Average Convergence Divergence (MACD).
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(signal) of MACD Line
        Histogram = MACD Line - Signal Line
        """
        fast_ema = TechnicalIndicators.calculate_ema(closes, fast_period)
        slow_ema = TechnicalIndicators.calculate_ema(closes, slow_period)

        n = len(closes)
        macd_line: List[Optional[float]] = [None] * n
        valid_macd_indices = []
        valid_macd_values = []

        for i in range(n):
            if fast_ema[i] is not None and slow_ema[i] is not None:
                val = round(fast_ema[i] - slow_ema[i], 6)
                macd_line[i] = val
                valid_macd_indices.append(i)
                valid_macd_values.append(val)

        signal_line: List[Optional[float]] = [None] * n
        histogram: List[Optional[float]] = [None] * n

        if len(valid_macd_values) >= signal_period:
            sig_values = TechnicalIndicators.calculate_ema(valid_macd_values, signal_period)
            for idx, sig_val in zip(valid_macd_indices, sig_values):
                signal_line[idx] = sig_val
                if sig_val is not None and macd_line[idx] is not None:
                    histogram[idx] = round(macd_line[idx] - sig_val, 6)

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }

    @staticmethod
    def calculate_adx(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Dict[str, List[Optional[float]]]:
        """
        Average Directional Index (ADX) measuring trend strength.
        Returns: +DI, -DI, ADX
        """
        n = len(closes)
        if n < period * 2 or period <= 0:
            return {
                "plus_di": [None] * n,
                "minus_di": [None] * n,
                "adx": [None] * n,
            }

        # 1. TR and Directional Movement (+DM, -DM)
        tr_list = [highs[0] - lows[0]]
        plus_dm_list = [0.0]
        minus_dm_list = [0.0]

        for i in range(1, n):
            up_move = highs[i] - highs[i - 1]
            down_move = lows[i - 1] - lows[i]

            plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
            minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

            tr_list.append(tr)
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        # 2. Smooth TR, +DM, -DM
        smoothed_tr = sum(tr_list[:period])
        smoothed_plus_dm = sum(plus_dm_list[:period])
        smoothed_minus_dm = sum(minus_dm_list[:period])

        plus_di_list: List[Optional[float]] = [None] * (period - 1)
        minus_di_list: List[Optional[float]] = [None] * (period - 1)
        dx_list: List[float] = []

        for i in range(period - 1, n):
            if i >= period:
                smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr_list[i]
                smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm_list[i]
                smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm_list[i]

            p_di = (100.0 * smoothed_plus_dm / smoothed_tr) if smoothed_tr > 0 else 0.0
            m_di = (100.0 * smoothed_minus_dm / smoothed_tr) if smoothed_tr > 0 else 0.0
            plus_di_list.append(round(p_di, 2))
            minus_di_list.append(round(m_di, 2))

            di_sum = p_di + m_di
            dx = (100.0 * abs(p_di - m_di) / di_sum) if di_sum > 0 else 0.0
            dx_list.append(dx)

        # 3. Smooth DX to get ADX
        adx_list: List[Optional[float]] = [None] * (period - 1 + period - 1)
        if len(dx_list) >= period:
            initial_adx = sum(dx_list[:period]) / period
            adx_list.append(round(initial_adx, 2))
            current_adx = initial_adx

            for i in range(period, len(dx_list)):
                current_adx = ((current_adx * (period - 1)) + dx_list[i]) / period
                adx_list.append(round(current_adx, 2))

        # Pad adx_list to match length n
        while len(adx_list) < n:
            adx_list.insert(0, None)

        return {
            "plus_di": plus_di_list,
            "minus_di": minus_di_list,
            "adx": adx_list,
        }
