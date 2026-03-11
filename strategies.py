"""APEX — Strategies Routes (Strategy library)"""
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter()


@router.get("/")
async def list_strategies():
    """List all available strategies"""
    try:
        from core.strategies.registry import get_strategy_registry
        reg = get_strategy_registry()
        return {"strategies": reg.get_all_info(), "total": len(reg), "categories": {"trend": reg.list_by_category("trend"), "mean_reversion": reg.list_by_category("mean_reversion"), "price_action": reg.list_by_category("price_action"), "momentum": reg.list_by_category("momentum"), "statistical": reg.list_by_category("statistical")}}
    except Exception as e:
        logger.error(f"list_strategies error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def run_strategy():
    """Run a strategy on an instrument now"""
    try:
        return {"message": "Strategy runner — implement with live OANDA data in Phase 2"}
    except Exception as e:
        logger.error(f"run_strategy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
