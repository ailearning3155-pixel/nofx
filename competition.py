"""APEX — Competition Routes (AI competition leaderboard)"""
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter()


@router.get("/leaderboard")
async def get_leaderboard():
    """Get current AI competition standings"""
    try:
        return {"leaderboard": [], "message": "Connect database and run paper trading to see competition data"}
    except Exception as e:
        logger.error(f"get_leaderboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{model}")
async def get_model_stats(model: str):
    """Get stats for a specific AI model"""
    try:
        return {"model": model, "message": "Stats available after paper trading begins"}
    except Exception as e:
        logger.error(f"get_model_stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_competition():
    """Reset competition scores"""
    try:
        return {"message": "Competition reset — implement with database in Phase 2"}
    except Exception as e:
        logger.error(f"reset_competition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
