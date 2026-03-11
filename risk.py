"""APEX — Risk Routes (Risk management and kill switch)"""
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter()


@router.get("/status")
async def get_risk_status():
    """Get current risk manager status"""
    try:
        from core.risk.manager import RiskManager
        rm = RiskManager()
        return rm.get_status()
    except Exception as e:
        logger.error(f"get_risk_status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill-switch/activate")
async def activate_kill_switch():
    """Activate emergency kill switch"""
    try:
        from core.risk.manager import RiskManager
        rm = RiskManager()
        rm.activate_kill_switch("Manual activation via API")
        return {"kill_switch": True, "message": "Kill switch ACTIVATED — all trading halted"}
    except Exception as e:
        logger.error(f"activate_kill_switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch():
    """Deactivate kill switch"""
    try:
        from core.risk.manager import RiskManager
        rm = RiskManager()
        rm.deactivate_kill_switch()
        return {"kill_switch": False, "message": "Kill switch deactivated"}
    except Exception as e:
        logger.error(f"deactivate_kill_switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
