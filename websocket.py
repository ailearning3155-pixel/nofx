"""
APEX — WebSocket Routes
Real-time updates: prices, trades, debate live feed, AI decisions
"""
import asyncio
import json
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter()


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info(f"WS connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        logger.info(f"WS disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active:
            return
        data = json.dumps(message)
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self.active -= dead

    async def send_to(self, ws: WebSocket, message: dict):
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.warning(f"WS send error: {e}")
            self.disconnect(ws)


# Global manager — import this in other modules to broadcast
ws_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return ws_manager


@router.websocket("/live")
async def websocket_live(websocket: WebSocket):
    """
    Main WebSocket endpoint.
    
    Clients receive:
    - price: live price updates
    - trade_opened: new trade opened
    - trade_closed: trade closed with P&L
    - debate_update: debate in progress (step by step)
    - ai_decision: AI made a decision
    - competition_update: leaderboard update
    - risk_alert: risk threshold triggered
    - account_update: balance/margin update
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial state
        from core.oanda.connector import get_oanda
        oanda = get_oanda()
        await ws_manager.send_to(websocket, {
            "type": "connected",
            "message": "APEX WebSocket connected",
        })

        # Keep connection alive, listen for client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)

                # Handle client requests
                if msg.get("type") == "subscribe_prices":
                    instruments = msg.get("instruments", [])
                    # TODO: start price stream for these instruments
                    await ws_manager.send_to(websocket, {
                        "type": "subscribed",
                        "instruments": instruments
                    })

                elif msg.get("type") == "ping":
                    await ws_manager.send_to(websocket, {"type": "pong"})

            except asyncio.TimeoutError:
                # Send heartbeat
                await ws_manager.send_to(websocket, {"type": "heartbeat"})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ─────────────────────────────────────────────
# Broadcast helpers (used by trading engine)
# ─────────────────────────────────────────────

async def broadcast_price(instrument: str, bid: float, ask: float, time: str):
    await ws_manager.broadcast({
        "type": "price",
        "instrument": instrument,
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / 2,
        "time": time,
    })


async def broadcast_trade_opened(trade_data: dict):
    await ws_manager.broadcast({
        "type": "trade_opened",
        **trade_data,
    })


async def broadcast_trade_closed(trade_data: dict):
    await ws_manager.broadcast({
        "type": "trade_closed",
        **trade_data,
    })


async def broadcast_debate_update(instrument: str, step: str, content: dict):
    """Broadcast live debate progress so users can watch it unfold."""
    await ws_manager.broadcast({
        "type": "debate_update",
        "instrument": instrument,
        "step": step,  # "bull_arguing" | "bear_arguing" | "head_trader_deciding" | "complete"
        **content,
    })


async def broadcast_ai_decision(model: str, instrument: str, action: str, confidence: float, reasoning: str):
    await ws_manager.broadcast({
        "type": "ai_decision",
        "model": model,
        "instrument": instrument,
        "action": action,
        "confidence": confidence,
        "reasoning": reasoning,
    })


async def broadcast_competition_update(leaderboard: list):
    await ws_manager.broadcast({
        "type": "competition_update",
        "leaderboard": leaderboard,
    })


async def broadcast_risk_alert(alert_type: str, message: str):
    await ws_manager.broadcast({
        "type": "risk_alert",
        "alert_type": alert_type,
        "message": message,
    })
