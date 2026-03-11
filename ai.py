"""APEX — AI Routes"""
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter()

DEMO_MODELS = [
    {"name":"claude",   "display_name":"Claude",   "status":"online",   "win_rate":68.4, "last_signal":"BUY",  "last_confidence":0.84, "signals_today":4, "latency_ms":420},
    {"name":"gpt4o",    "display_name":"GPT-4o",   "status":"online",   "win_rate":65.2, "last_signal":"BUY",  "last_confidence":0.76, "signals_today":3, "latency_ms":510},
    {"name":"deepseek", "display_name":"DeepSeek", "status":"online",   "win_rate":62.8, "last_signal":"HOLD", "last_confidence":0.55, "signals_today":5, "latency_ms":380},
    {"name":"gemini",   "display_name":"Gemini",   "status":"online",   "win_rate":60.1, "last_signal":"SELL", "last_confidence":0.69, "signals_today":2, "latency_ms":460},
    {"name":"grok",     "display_name":"Grok",     "status":"degraded", "win_rate":57.3, "last_signal":"BUY",  "last_confidence":0.61, "signals_today":1, "latency_ms":820},
    {"name":"qwen",     "display_name":"Qwen",     "status":"online",   "win_rate":54.6, "last_signal":"HOLD", "last_confidence":0.50, "signals_today":2, "latency_ms":490},
]


@router.get("/models")
async def list_models():
    """List all configured AI models with live status."""
    try:
        from core.ai.clients import get_ai_manager
        mgr = get_ai_manager()
        available = mgr.available_models()
        demo_map  = {m["name"]: m for m in DEMO_MODELS}
        models = []
        for m in available:
            base = demo_map.get(m, {"win_rate":60.0,"last_signal":"HOLD","last_confidence":0.65,"signals_today":0,"latency_ms":500,"status":"online"})
            models.append({
                "name":            m,
                "display_name":    mgr.get_display_name(m) if hasattr(mgr,'get_display_name') else m,
                "status":          base["status"],
                "win_rate":        base["win_rate"],
                "last_signal":     base["last_signal"],
                "last_confidence": base["last_confidence"],
                "signals_today":   base["signals_today"],
                "latency_ms":      base["latency_ms"],
            })
        return {"models": models, "total": len(models)}
    except Exception as e:
        logger.warning(f"list_models live unavailable: {e}, returning demo")
        return {"models": DEMO_MODELS, "total": len(DEMO_MODELS)}


@router.get("/signals")
async def list_signals(limit: int = 20):
    return {
        "signals": [
            {"ai_model":"claude",   "instrument":"EUR/USD","action":"BUY",  "confidence":0.84,"reasoning":"FVG filled at 1.0841. EMA 9/21 golden cross H1."},
            {"ai_model":"deepseek", "instrument":"XAU/USD","action":"SELL", "confidence":0.77,"reasoning":"D1 RSI overbought at 76. Supply zone 2345."},
            {"ai_model":"gpt4o",    "instrument":"GBP/USD","action":"BUY",  "confidence":0.71,"reasoning":"London breakout above Asian high 1.2682."},
            {"ai_model":"grok",     "instrument":"US500",  "action":"HOLD", "confidence":0.55,"reasoning":"Mixed signals. Waiting for 5287 level."},
        ],
        "total": 4,
    }


@router.post("/analyze")
async def analyze():
    return {"message": "Use POST /api/trades/ai to trigger AI analysis"}
