from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.instrument import Instrument
from app.schemas.instrument import InstrumentRead, InstrumentCreate
from app.services.market_data.catalog import DERIV_CATALOG, CATALOG_BY_SYMBOL

router = APIRouter(prefix="/instruments", tags=["Instruments"])

@router.get("", response_model=List[InstrumentRead])
async def list_instruments(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve list of configured trading instruments."""
    stmt = select(Instrument)
    if active_only:
        stmt = stmt.where(Instrument.is_active == True)
    stmt = stmt.order_by(Instrument.symbol)
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/catalog")
async def get_instrument_catalog(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns the comprehensive catalog of all Deriv pairs and instruments,
    including Crash & Boom, Baskets, Range Break, Indices, and Forex.
    Includes live activation status from the database.
    """
    stmt = select(Instrument)
    result = await db.execute(stmt)
    db_instruments = {inst.symbol: inst for inst in result.scalars().all()}

    catalog_items = []
    for item in DERIV_CATALOG:
        if category and item["market"] != category and item["submarket"] != category:
            continue
        
        sym = item["symbol"]
        db_inst = db_instruments.get(sym)
        is_active = db_inst.is_active if db_inst else item.get("default_active", False)

        catalog_items.append({
            **item,
            "is_active": is_active,
            "is_configured": db_inst is not None,
        })

    # Group by market category
    grouped_categories: Dict[str, List[Dict[str, Any]]] = {}
    for item in catalog_items:
        m = item["market"]
        if m not in grouped_categories:
            grouped_categories[m] = []
        grouped_categories[m].append(item)

    return {
        "total_instruments": len(catalog_items),
        "markets": grouped_categories,
        "items": catalog_items,
    }

@router.post("/{symbol}/toggle")
async def toggle_instrument(
    symbol: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Toggles an instrument between active and inactive.
    If not previously in the database, provisions it from the official Deriv catalog.
    """
    sym = symbol.upper()
    stmt = select(Instrument).where(Instrument.symbol == sym)
    result = await db.execute(stmt)
    inst = result.scalar_one_or_none()

    if inst:
        inst.is_active = not inst.is_active
        await db.commit()
        await db.refresh(inst)

        if inst.is_active:
            from app.main import get_ingestion_worker
            from app.services.candle_service import CandleService
            worker = get_ingestion_worker()
            if worker:
                await worker.add_symbol(inst.symbol)
            try:
                svc = CandleService(db)
                await svc.get_candles(symbol=inst.symbol, timeframe="1m", limit=5, auto_fetch=True)
                await svc.get_candles(symbol=inst.symbol, timeframe="15m", limit=5, auto_fetch=True)
            except Exception:
                pass

        return {
            "symbol": inst.symbol,
            "is_active": inst.is_active,
            "message": f"Instrument {inst.symbol} is now {'active' if inst.is_active else 'inactive'}."
        }

    # If not in DB, lookup in catalog to provision
    catalog_info = CATALOG_BY_SYMBOL.get(sym)
    if not catalog_info:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol '{sym}' not found in catalog or configured instruments."
        )

    inst = Instrument(
        symbol=sym,
        base_asset=catalog_info["base_asset"],
        quote_asset=catalog_info["quote_asset"],
        pip_size=catalog_info["pip_size"],
        is_active=True
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)

    from app.main import get_ingestion_worker
    from app.services.candle_service import CandleService
    worker = get_ingestion_worker()
    if worker:
        await worker.add_symbol(inst.symbol)
    try:
        svc = CandleService(db)
        await svc.get_candles(symbol=inst.symbol, timeframe="1m", limit=5, auto_fetch=True)
        await svc.get_candles(symbol=inst.symbol, timeframe="15m", limit=5, auto_fetch=True)
    except Exception:
        pass

    return {
        "symbol": inst.symbol,
        "is_active": inst.is_active,
        "message": f"Instrument {inst.symbol} was added and activated successfully."
    }

@router.post("", response_model=InstrumentRead, status_code=201)
async def create_instrument(
    payload: InstrumentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register or enable an instrument manually."""
    stmt = select(Instrument).where(Instrument.symbol == payload.symbol.upper())
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Instrument {payload.symbol} already exists")

    inst = Instrument(
        symbol=payload.symbol.upper(),
        base_asset=payload.base_asset.upper(),
        quote_asset=payload.quote_asset.upper(),
        pip_size=payload.pip_size,
        is_active=payload.is_active
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return inst
