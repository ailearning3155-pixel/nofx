"""APEX — Debate Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


class DebateRequest(BaseModel):
    instrument: str = "EUR_USD"
    granularity: str = "H1"
    count: int = 200


async def _fallback_debate(instrument: str):
    """Return a realistic demo debate result when OANDA/AI not configured."""
    import random, asyncio
    await asyncio.sleep(0.3)          # brief artificial delay
    fa = random.choice(["BUY", "SELL", "HOLD"])
    fc = round(0.60 + random.random() * 0.28, 2)
    def ac(): return round(0.5 + random.random() * 0.45, 2)
    return {
        "instrument": instrument,
        "final_action": fa,
        "final_confidence": fc,
        "consensus_reached": True,
        "duration_seconds": round(2.4 + random.random() * 3.2, 1),
        "head_trader_model": "claude",
        "final_reasoning": (
            f"Demo mode (live services not configured). Simulated {fa} on "
            f"{instrument.replace('_','/')} at {fc:.0%} confidence. "
            "Bull and Analyst aligned; Risk Manager approved 1% sizing with clean SL."
        ),
        "bull":         {"stance":"BUY",  "confidence":ac(), "argument":"EMA 9/21 golden cross confirmed H1. FVG at prior structure filled. Order block respected.", "key_points":["EMA cross","FVG fill","OB support"]},
        "bear":         {"stance":"HOLD", "confidence":ac(), "argument":"DXY showing mild bid. 4H possible double-top. Waiting for cleaner structure before committing.", "key_points":["DXY strength","4H resistance"]},
        "analyst":      {"stance":"BUY",  "confidence":ac(), "argument":"RSI 54 — not overbought. ADX 28 rising. MACD histogram turning positive. Volume above 20-session average.", "key_points":["RSI neutral","ADX rising","MACD positive"]},
        "risk_manager": {"stance":"BUY",  "confidence":ac(), "argument":"1% risk viable. SL below structure is clean. 1:2.5 R:R achievable. Currency exposure within 40% limit.", "key_points":["1% risk","Clean SL","1:2.5 R:R"]},
    }


@router.post("/run")
@router.post("/trigger")
async def run_debate(req: DebateRequest):
    """Run a full 4-agent debate for the given instrument."""
    try:
        from core.oanda.connector import get_oanda
        from core.ai.clients import get_ai_manager
        from core.debate.engine import DebateEngine
        from core.strategies.registry import get_strategy_registry
        from core.ai.agent import MarketContextBuilder
        from core.indicators import ind
        import pandas as pd

        oanda  = get_oanda()
        ai_mgr = get_ai_manager()
        reg    = get_strategy_registry()

        candles = oanda.get_candles(req.instrument, req.granularity, req.count)
        price   = oanda.get_current_price(req.instrument)
        balance = oanda.get_balance()
        open_tr = oanda.get_open_trades()

        df = pd.DataFrame(candles)
        df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
        indicators = {
            "rsi_14":    float(ind.rsi(df["close"], 14).iloc[-1]),
            "ema_9":     float(ind.ema(df["close"], 9).iloc[-1]),
            "ema_21":    float(ind.ema(df["close"], 21).iloc[-1]),
            "ema_50":    float(ind.ema(df["close"], 50).iloc[-1]),
            "macd_line": float(ind.macd(df["close"])["macd"].iloc[-1]),
            "atr_14":    float(ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]),
        }
        ctx = MarketContextBuilder.build(
            instrument=req.instrument, candles=candles, indicators=indicators,
            current_price=price, account_balance=balance, open_trades=open_tr,
            available_strategies=reg.list_strategy_names(),
        )
        engine = DebateEngine(ai_mgr)
        result = await engine.run_debate(req.instrument, ctx)
        return result.to_dict()

    except Exception as e:
        logger.warning(f"Debate live mode unavailable ({e}), returning demo result")
        return await _fallback_debate(req.instrument)


@router.get("/history")
async def debate_history(limit: int = 20):
    return {"debates": [], "total": 0, "message": "Connect database to persist debate history"}


@router.get("/{debate_id}")
async def get_debate(debate_id: str):
    raise HTTPException(404, f"Debate {debate_id} not found — connect database")
