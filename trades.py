"""APEX — Trade Routes"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from core.oanda.connector import get_oanda, OandaConnector
from core.ai.agent import FreeWillAgent
from core.debate.engine import DebateEngine
from core.risk.manager import RiskManager
from loguru import logger

router = APIRouter()


class ManualTradeRequest(BaseModel):
    instrument: str
    direction: str          # BUY | SELL
    units: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_pct: float = 1.0


class AITradeRequest(BaseModel):
    instrument: str
    ai_model: str = "deepseek"   # which AI to use
    use_debate: bool = True       # use full debate engine?


@router.get("/open")
async def get_open_trades():
    """Get all currently open trades."""
    oanda = get_oanda()
    return oanda.get_open_trades()


@router.get("/history")
async def get_trade_history(limit: int = 50):
    """Get recent trade history from database."""
    # TODO: Query from DB
    return {"trades": [], "total": 0}


@router.post("/manual")
async def place_manual_trade(req: ManualTradeRequest):
    """Place a manual trade (bypasses AI, still goes through risk checks)."""
    oanda = get_oanda()
    units = req.units if req.direction == "BUY" else -req.units
    result = oanda.place_market_order(
        instrument=req.instrument,
        units=units,
        stop_loss_price=req.stop_loss,
        take_profit_price=req.take_profit,
    )
    return {"success": True, "result": result}


@router.post("/ai")
async def request_ai_trade(req: AITradeRequest, background_tasks: BackgroundTasks):
    """
    Ask an AI model to analyze and potentially trade an instrument.
    Runs debate engine if requested.
    """
    background_tasks.add_task(_run_ai_analysis, req.instrument, req.ai_model, req.use_debate)
    return {"message": f"AI analysis started for {req.instrument}", "model": req.ai_model}


@router.post("/close/{trade_id}")
async def close_trade(trade_id: str, units: Optional[float] = None):
    """Close an open trade by OANDA trade ID."""
    oanda = get_oanda()
    result = oanda.close_trade(trade_id, units)
    return {"success": True, "result": result}


@router.post("/close-all")
async def emergency_close_all():
    """Emergency: close ALL open trades immediately."""
    oanda = get_oanda()
    results = oanda.close_all_trades()
    return {"success": True, "closed": len(results), "results": results}


@router.get("/positions")
async def get_positions():
    """Get all open positions (aggregated by instrument)."""
    oanda = get_oanda()
    return oanda.get_open_positions()


async def _run_ai_analysis(instrument: str, ai_model: str, use_debate: bool):
    """Background task: full AI analysis pipeline."""
    from core.ai.clients import get_ai_manager
    from core.strategies.registry import get_strategy_registry
    from core.indicators import ind
    import pandas as pd

    oanda = get_oanda()
    ai_mgr = get_ai_manager()
    registry = get_strategy_registry()

    try:
        # Fetch data
        candles = oanda.get_candles(instrument, count=200)
        price = oanda.get_current_price(instrument)
        balance = oanda.get_balance()
        open_trades = oanda.get_open_trades()

        # Calculate indicators
        df = pd.DataFrame(candles)
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        indicators = {
            "rsi_14":   float(ind.rsi(df["close"], 14).iloc[-1]),
            "ema_9":    float(ind.ema(df["close"], 9).iloc[-1]),
            "ema_21":   float(ind.ema(df["close"], 21).iloc[-1]),
            "ema_50":   float(ind.ema(df["close"], 50).iloc[-1]),
            "macd_line": float(ind.macd(df["close"])["macd"].iloc[-1]),
            "atr_14":   float(ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]),
        }

        if use_debate:
            from core.ai.agent import MarketContextBuilder
            context = MarketContextBuilder.build(
                instrument=instrument, candles=candles, indicators=indicators,
                current_price=price, account_balance=balance, open_trades=open_trades,
                available_strategies=registry.list_strategy_names()
            )
            debate_engine = DebateEngine(ai_mgr)
            debate_result = await debate_engine.run_debate(instrument, context)
            logger.info(f"Debate result: {debate_result.final_action.value} @ {debate_result.final_confidence:.2f}")
        else:
            agent = FreeWillAgent(ai_mgr, registry)
            decision = await agent.analyze(
                model=ai_model, instrument=instrument, candles=candles,
                indicators=indicators, current_price=price,
                account_balance=balance, open_trades=open_trades,
            )
            logger.info(f"AI decision: {decision.action.value} @ {decision.confidence:.2f}")

    except Exception as e:
        logger.error(f"AI analysis error for {instrument}: {e}")
