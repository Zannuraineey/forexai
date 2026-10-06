import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
import websockets

from app.core.config import settings
from app.core.logging import logger
from app.schemas.candle import CandleDTO
from app.services.market_data.base import IMarketDataProvider
from app.services.market_data.catalog import STANDARD_TO_DERIV_MAP, DERIV_TO_STANDARD_MAP

DERIV_SYMBOL_MAP = {
    "XAUUSD": "frxXAUUSD",
    "XAGUSD": "frxXAGUSD",
    "EURUSD": "frxEURUSD",
    "GBPUSD": "frxGBPUSD",
    "USDJPY": "frxUSDJPY",
    "AUDUSD": "frxAUDUSD",
    "USDCHF": "frxUSDCHF",
    "USDCAD": "frxUSDCAD",
    **STANDARD_TO_DERIV_MAP
}

REVERSE_DERIV_MAP = {
    **{v: k for k, v in DERIV_SYMBOL_MAP.items()},
    **DERIV_TO_STANDARD_MAP
}

DERIV_TIMEFRAME_MAP = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

REVERSE_TIMEFRAME_MAP = {v: k for k, v in DERIV_TIMEFRAME_MAP.items()}

class DerivMarketDataProvider(IMarketDataProvider):
    """
    Deriv market data provider utilizing WebSocket API v3.
    Supports historical tick/candle retrieval (gap filling) and live candle streaming.
    """

    def __init__(self, ws_url: Optional[str] = None, app_id: Optional[str] = None):
        self._app_id = app_id or settings.DERIV_APP_ID
        self._base_url = ws_url or settings.DERIV_WS_URL
        self._ws: Optional[Any] = None
        self._connected = False
        self._req_counter = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._live_queue: asyncio.Queue[CandleDTO] = asyncio.Queue(maxsize=10000)
        self._listen_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

    @property
    def name(self) -> str:
        return "deriv"

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    def map_symbol(self, standard_symbol: str) -> str:
        return DERIV_SYMBOL_MAP.get(standard_symbol, standard_symbol)

    def unmap_symbol(self, provider_symbol: str) -> str:
        if provider_symbol in REVERSE_DERIV_MAP:
            return REVERSE_DERIV_MAP[provider_symbol]
        if provider_symbol.startswith("frx"):
            return provider_symbol[3:]
        if provider_symbol.startswith("cry"):
            return provider_symbol[3:]
        return provider_symbol

    def _next_req_id(self) -> int:
        self._req_counter += 1
        return self._req_counter

    async def connect(self) -> None:
        """Establish WebSocket connection to Deriv."""
        if self.is_connected:
            return

        if "options/ws" in self._base_url or "?" in self._base_url:
            endpoint = self._base_url
        else:
            endpoint = f"{self._base_url}?app_id={self._app_id}&l=en"
            
        logger.info(f"Connecting to Deriv WebSocket at {endpoint}...")
        
        self._ws = await websockets.connect(
            endpoint,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        )
        self._connected = True
        logger.info("Successfully connected to Deriv WebSocket.")
        
        # Start background listener and ping worker
        self._listen_task = asyncio.create_task(self._listener_loop())
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def disconnect(self) -> None:
        """Gracefully disconnect WebSocket and cancel background tasks."""
        self._connected = False
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Disconnected from Deriv WebSocket.")

    async def _ping_loop(self) -> None:
        """Deriv application-level ping every 30s to keep connection alive."""
        try:
            while self._connected:
                await asyncio.sleep(30)
                if self._ws and self._connected:
                    req_id = self._next_req_id()
                    await self._ws.send(json.dumps({"ping": 1, "req_id": req_id}))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Deriv ping loop encountered error: {e}")

    async def _listener_loop(self) -> None:
        """Reads incoming frames from Deriv WebSocket and routes to awaiting futures or live queues."""
        try:
            async for raw_message in self._ws:
                data = json.loads(raw_message)
                req_id = data.get("req_id")

                # Check if this message resolves a request future
                if req_id and req_id in self._pending_requests:
                    future = self._pending_requests.pop(req_id)
                    if not future.done():
                        if "error" in data:
                            err_code = data["error"].get("code", "")
                            if err_code == "MarketIsClosed":
                                logger.info(f"Deriv market is currently closed ({data['error'].get('message')}).")
                                future.set_result({"candles": [], "market_closed": True})
                            else:
                                future.set_exception(RuntimeError(data["error"].get("message", "Deriv API error")))
                        else:
                            future.set_result(data)
                    continue

                if "error" in data:
                    err_msg = data["error"].get("message", "Deriv notification")
                    logger.info(f"Deriv API notice: {err_msg}")
                    continue

                # Handle live OHLC candle feed stream
                if "ohlc" in data:
                    ohlc_data = data["ohlc"]
                    symbol = self.unmap_symbol(ohlc_data.get("symbol", ""))
                    granularity = ohlc_data.get("granularity", 60)
                    timeframe = REVERSE_TIMEFRAME_MAP.get(granularity, "1m")
                    epoch = int(ohlc_data.get("open_time", ohlc_data.get("epoch", 0)))
                    ts_utc = datetime.fromtimestamp(epoch, tz=timezone.utc)

                    candle = CandleDTO(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp_utc=ts_utc,
                        open=float(ohlc_data["open"]),
                        high=float(ohlc_data["high"]),
                        low=float(ohlc_data["low"]),
                        close=float(ohlc_data["close"]),
                        volume=0.0,
                        provider="deriv",
                        is_complete=True
                    )
                    try:
                        self._live_queue.put_nowait(candle)
                    except asyncio.QueueFull:
                        logger.warning("Deriv live candle queue full; dropping oldest update.")
                        self._live_queue.get_nowait()
                        self._live_queue.put_nowait(candle)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Deriv listener loop failed: {e}")
            self._connected = False

    async def fetch_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        count: Optional[int] = None,
    ) -> List[CandleDTO]:
        """
        Queries historical candles via Deriv `ticks_history` request.
        """
        if not self.is_connected:
            await self.connect()

        deriv_symbol = self.map_symbol(symbol)
        granularity = DERIV_TIMEFRAME_MAP.get(timeframe, 60)
        start_epoch = int(start_time.timestamp())
        end_epoch = int(end_time.timestamp())
        
        req_id = self._next_req_id()
        payload = {
            "ticks_history": deriv_symbol,
            "adjust_start_time": 1,
            "style": "candles",
            "granularity": granularity,
            "start": start_epoch,
            "end": end_epoch,
            "req_id": req_id
        }
        if count:
            payload["count"] = min(count, 5000)

        future = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = future

        await self._ws.send(json.dumps(payload))
        response = await asyncio.wait_for(future, timeout=30.0)

        candles_raw = response.get("candles", [])
        result: List[CandleDTO] = []
        for c in candles_raw:
            ts_utc = datetime.fromtimestamp(c["epoch"], tz=timezone.utc)
            result.append(
                CandleDTO(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp_utc=ts_utc,
                    open=float(c["open"]),
                    high=float(c["high"]),
                    low=float(c["low"]),
                    close=float(c["close"]),
                    volume=0.0,
                    provider="deriv",
                    is_complete=True
                )
            )
        result.sort(key=lambda x: x.timestamp_utc)
        return result

    async def subscribe_live_candles(
        self,
        symbols: List[str],
        timeframes: List[str],
    ) -> AsyncGenerator[CandleDTO, None]:
        """
        Subscribes to live candle ticks on Deriv and yields completed candles.
        """
        if not self.is_connected:
            await self.connect()

        for symbol in symbols:
            deriv_symbol = self.map_symbol(symbol)
            for tf in timeframes:
                granularity = DERIV_TIMEFRAME_MAP.get(tf, 60)
                req_id = self._next_req_id()
                sub_payload = {
                    "ticks_history": deriv_symbol,
                    "end": "latest",
                    "style": "candles",
                    "granularity": granularity,
                    "count": 1,
                    "subscribe": 1,
                    "req_id": req_id,
                }
                await self._ws.send(json.dumps(sub_payload))
                logger.info(f"Subscribed to live Deriv feed: {symbol} ({tf})")

        while self._connected:
            try:
                candle = await asyncio.wait_for(self._live_queue.get(), timeout=2.0)
                yield candle
            except asyncio.TimeoutError:
                continue

    async def subscribe_symbol(self, symbol: str, timeframes: List[str]) -> None:
        """Dynamically subscribes a new instrument into the live websocket stream."""
        if not self.is_connected or not self._ws:
            return
        deriv_symbol = self.map_symbol(symbol)
        for tf in timeframes:
            granularity = DERIV_TIMEFRAME_MAP.get(tf, 60)
            req_id = self._next_req_id()
            sub_payload = {
                "ticks_history": deriv_symbol,
                "end": "latest",
                "style": "candles",
                "granularity": granularity,
                "count": 1,
                "subscribe": 1,
                "req_id": req_id,
            }
            try:
                await self._ws.send(json.dumps(sub_payload))
                logger.info(f"Dynamically subscribed to live Deriv feed: {symbol} ({tf})")
            except Exception as e:
                logger.warning(f"Failed dynamic Deriv subscription for {symbol} ({tf}): {e}")

