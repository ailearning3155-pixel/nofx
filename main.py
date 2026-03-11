"""
APEX — FastAPI Main Application
REST API + WebSocket server

Startup is fault-tolerant: OANDA/AI errors are warnings, not crashes.
The server always starts so you can use the dashboard and backtest UI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from config.settings import settings
from api.routes import trades, ai, debate, strategies, account, backtest, competition, risk, websocket
from api.routes import upgrade as upgrade_routes


# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
import os
os.makedirs("logs", exist_ok=True)
logger.add("logs/apex_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", level="DEBUG")


# ─────────────────────────────────────────────
# App Lifecycle  — fault-tolerant startup
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 APEX Trading OS starting up...")

    # ── OANDA connection (warn, don't crash) ──
    if not settings.oanda.api_key or not settings.oanda.account_id:
        logger.warning(
            "⚠️  OANDA not configured — add OANDA_ACCOUNT_ID and OANDA_API_KEY to your .env file\n"
            "    Backtest UI and dashboard will load, but live/paper trading is disabled."
        )
    else:
        try:
            from core.oanda.connector import get_oanda
            oanda = get_oanda()
            acct = oanda.get_account()
            logger.info(
                f"✅ OANDA connected [{settings.oanda.environment.upper()}] "
                f"balance={acct['NAV']} {acct['currency']}"
            )
        except Exception as e:
            logger.warning(
                f"⚠️  OANDA connection failed: {e}\n"
                f"    Check your OANDA_API_KEY and OANDA_ACCOUNT_ID in .env\n"
                f"    Server will start anyway — fix the key and restart."
            )

    # ── AI Manager (warn, don't crash) ──
    try:
        from core.ai.clients import get_ai_manager
        ai_mgr = get_ai_manager()
        models = ai_mgr.available_models()
        if models:
            logger.info(f"✅ AI Manager ready: {models}")
        else:
            logger.warning(
                "⚠️  No AI models configured — add at least one API key to .env\n"
                "    Example: DEEPSEEK_API_KEY=sk-...  (cheapest option)"
            )
    except Exception as e:
        logger.warning(f"⚠️  AI Manager failed to start: {e}")

    # ── Strategy Registry (warn, don't crash) ──
    try:
        from core.strategies.registry import get_strategy_registry
        registry = get_strategy_registry()
        logger.info(f"✅ Strategy Registry: {len(registry)} strategies loaded")
    except Exception as e:
        logger.warning(f"⚠️  Strategy Registry failed: {e}")

    # ── Telegram (optional, skip silently if not configured) ──
    if settings.telegram.enabled and settings.telegram.bot_token:
        try:
            from services.telegram.bot import get_telegram_bot
            bot = get_telegram_bot()
            await bot.send_startup_message()
            logger.info("✅ Telegram bot ready")
        except Exception as e:
            logger.warning(f"⚠️  Telegram bot failed: {e}")

    # ── Retraining Scheduler ──
    try:
        from core.ml.retrainer import get_retraining_scheduler
        scheduler = get_retraining_scheduler()
        scheduler.start()
        logger.info("✅ Retraining scheduler started (weekly ML, hourly RL save)")
    except Exception as e:
        logger.warning(f"⚠️  Retraining scheduler failed to start: {e}")

    logger.info("🟢 APEX server is running — open http://localhost:8000/api/docs")
    # Register upgrade plan routes
    try:
        app.include_router(upgrade_routes.router)
        logger.info("✅ Upgrade plan routes registered (/v2/*)")
    except Exception as e:
        logger.warning(f"Could not load upgrade routes: {e}")

    yield

    logger.info("🔴 APEX shutting down...")
    try:
        from core.ml.retrainer import get_retraining_scheduler
        get_retraining_scheduler().stop()
    except Exception:
        pass


# ─────────────────────────────────────────────
# App Instance
# ─────────────────────────────────────────────

app = FastAPI(
    title="APEX Trading OS",
    description="Autonomous Python EXecution Trading OS — AI-powered forex & CFD trading",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

app.include_router(account.router,     prefix="/api/account",      tags=["Account"])
app.include_router(trades.router,      prefix="/api/trades",       tags=["Trades"])
app.include_router(ai.router,          prefix="/api/ai",           tags=["AI"])
app.include_router(debate.router,      prefix="/api/debate",       tags=["Debate"])
app.include_router(strategies.router,  prefix="/api/strategies",   tags=["Strategies"])
app.include_router(backtest.router,    prefix="/api/backtest",     tags=["Backtest"])
app.include_router(competition.router, prefix="/api/competition",  tags=["Competition"])
app.include_router(risk.router,        prefix="/api/risk",         tags=["Risk"])
app.include_router(websocket.router,   prefix="/ws",               tags=["WebSocket"])


# ─────────────────────────────────────────────
# Health & Status
# ─────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "APEX Trading OS", "version": "2.0.0"}


@app.get("/api/status", tags=["System"])
async def system_status():
    """Full system status — shows what's connected and what isn't."""
    status = {
        "oanda": {"connected": False, "environment": settings.oanda.environment, "balance": None},
        "ai": {"models": [], "count": 0},
        "trading": {
            "mode": settings.trading.mode,
            "instruments": settings.trading.instruments,
            "granularity": settings.trading.candle_granularity,
        },
        "features": {
            "debate_enabled": settings.debate.enabled,
            "competition_mode": settings.competition.enabled,
            "telegram_enabled": settings.telegram.enabled,
        },
        "config_issues": [],
    }

    # Check OANDA
    if not settings.oanda.api_key or not settings.oanda.account_id:
        status["config_issues"].append(
            "OANDA not configured — add OANDA_ACCOUNT_ID and OANDA_API_KEY to .env"
        )
    else:
        try:
            from core.oanda.connector import get_oanda
            balance = get_oanda().get_balance()
            status["oanda"]["connected"] = True
            status["oanda"]["balance"] = balance
        except Exception as e:
            status["config_issues"].append(f"OANDA error: {e}")

    # Check AI
    try:
        from core.ai.clients import get_ai_manager
        mgr = get_ai_manager()
        status["ai"]["models"] = mgr.available_models()
        status["ai"]["count"] = len(mgr.available_models())
        if not mgr.available_models():
            status["config_issues"].append(
                "No AI models — add at least DEEPSEEK_API_KEY to .env"
            )
    except Exception as e:
        status["config_issues"].append(f"AI Manager error: {e}")

    if not status["config_issues"]:
        status["ready"] = True
        status["message"] = "All systems operational"
    else:
        status["ready"] = False
        status["message"] = f"{len(status['config_issues'])} issue(s) need attention"

    return status
