import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.models.instrument import Instrument
from app.models.candle import Candle
from app.schemas.candle import CandleDTO
from app.services.candle_service import CandleService

@pytest.mark.asyncio
async def test_instrument_creation_and_fields(db_session):
    inst = Instrument(
        symbol="EURUSD",
        base_asset="EUR",
        quote_asset="USD",
        pip_size=0.0001,
        is_active=True
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    assert inst.id is not None
    assert inst.symbol == "EURUSD"
    assert float(inst.pip_size) == 0.0001
    assert inst.is_active is True

@pytest.mark.asyncio
async def test_candle_unique_constraint(db_session):
    inst = Instrument(symbol="GBPUSD", base_asset="GBP", quote_asset="USD", pip_size=0.0001)
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    ts = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)

    c1 = Candle(
        instrument_id=inst.id,
        timeframe="15m",
        timestamp_utc=ts,
        open=1.3000,
        high=1.3050,
        low=1.2990,
        close=1.3020,
        volume=500.0,
        provider="deriv"
    )
    db_session.add(c1)
    await db_session.commit()

    # Attempting to insert exact same instrument, timeframe, timestamp directly via ORM must fail integrity
    c2 = Candle(
        instrument_id=inst.id,
        timeframe="15m",
        timestamp_utc=ts,
        open=1.3010,
        high=1.3060,
        low=1.2995,
        close=1.3030,
        volume=400.0,
        provider="deriv"
    )
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

@pytest.mark.asyncio
async def test_candle_service_idempotent_save(db_session):
    service = CandleService(db_session)
    ts = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)

    candles = [
        CandleDTO(
            symbol="XAUUSD",
            timeframe="1h",
            timestamp_utc=ts,
            open=2650.0,
            high=2660.0,
            low=2645.0,
            close=2655.0,
            volume=150.0,
            provider="deriv"
        )
    ]

    # First insert
    saved_first = await service.save_candles(candles)
    assert saved_first == 1

    # Second insert of identical candle - must NOT raise error, should ignore conflict
    saved_second = await service.save_candles(candles)
    assert saved_second >= 0

    # Verify only one candle exists in database for this specific timestamp
    retrieved = await service.get_candles("XAUUSD", "1h")
    matching = [c for c in retrieved if c.timestamp_utc.strftime("%Y-%m-%d %H:%M") == ts.strftime("%Y-%m-%d %H:%M")]
    assert len(matching) == 1
    assert matching[0].close == 2655.0
