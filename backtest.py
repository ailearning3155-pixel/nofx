"""APEX — Backtest Routes"""
import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

router = APIRouter()

# In-memory store (use Redis in production)
_running: dict  = {}
_completed: dict = {}


class BacktestRequest(BaseModel):
    instrument: str        = "EUR_USD"
    granularity: str       = "H1"
    start_date: str        = "2024-01-01"
    end_date: str          = "2024-12-31"
    initial_balance: float = 10000.0
    risk_per_trade_pct: float = 1.0
    max_open_trades: int   = 3
    max_drawdown_pct: float = 20.0
    strategy: Optional[str] = "ema_crossover"
    ai_model: Optional[str] = None
    use_debate: bool        = False
    compare_all: bool       = False


@router.post("/run")
async def run_backtest(req: BacktestRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())[:8]
    _running[run_id] = {"status": "running", "message": "Fetching historical data..."}
    background_tasks.add_task(_run_task, run_id, req)
    return {"run_id": run_id, "status": "started", "message": "Backtest queued"}


async def _run_task(run_id: str, req: BacktestRequest):
    try:
        from core.backtest.engine import BacktestEngine, BacktestConfig
        engine = BacktestEngine()
        _running[run_id] = {"status": "running", "message": "Simulation in progress..."}

        if req.compare_all:
            results = await engine.run_all_strategies(BacktestConfig(
                instrument=req.instrument, granularity=req.granularity,
                start_date=req.start_date, end_date=req.end_date,
                initial_balance=req.initial_balance,
                risk_per_trade_pct=req.risk_per_trade_pct,
                max_drawdown_pct=req.max_drawdown_pct,
            ))
            _completed[run_id] = {"status": "completed", "compare_all": True, "results": results}
        else:
            config = BacktestConfig(
                instrument=req.instrument, granularity=req.granularity,
                start_date=req.start_date, end_date=req.end_date,
                initial_balance=req.initial_balance,
                risk_per_trade_pct=req.risk_per_trade_pct,
                max_open_trades=req.max_open_trades,
                max_drawdown_pct=req.max_drawdown_pct,
                strategy=req.strategy,
                ai_model=req.ai_model,
            )
            result = await engine.run(config)
            _completed[run_id] = {"status": "completed", **result.to_dict()}

        del _running[run_id]
    except Exception as e:
        logger.error(f"Backtest task {run_id} failed: {e}")
        _completed[run_id] = {"status": "failed", "error": str(e)}
        if run_id in _running:
            del _running[run_id]


@router.get("/status/{run_id}")
async def backtest_status(run_id: str):
    if run_id in _running:
        return _running[run_id]
    if run_id in _completed:
        return {"status": _completed[run_id].get("status", "completed")}
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.get("/results/{run_id}")
async def backtest_results(run_id: str):
    if run_id not in _completed:
        if run_id in _running:
            raise HTTPException(status_code=202, detail="Still running")
        raise HTTPException(status_code=404, detail="Not found")
    return _completed[run_id]


@router.get("/results")
async def list_results():
    return {"results": [{"run_id": k, "status": v.get("status"), "verdict": v.get("verdict")} for k,v in _completed.items()]}


@router.get("/strategies")
async def list_strategies():
    from core.strategies.registry import get_strategy_registry
    reg = get_strategy_registry()
    return {"strategies": reg.list_strategy_names(), "total": len(reg)}
