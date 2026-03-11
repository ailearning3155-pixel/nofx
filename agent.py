"""
APEX — Free Will AI Trading Agent
The brain of APEX. Each AI gets full market context and decides:
1. WHAT mode to use (Strategy / Hybrid / Free Will)
2. Whether to trade at all
3. Full trade parameters with reasoning
"""
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from loguru import logger

from core.ai.clients import AIManager, AIResponse
from core.strategies.registry import StrategyRegistry
from models.models import AIMode, SignalAction


# ─────────────────────────────────────────────
# Trading Decision Dataclass
# ─────────────────────────────────────────────

@dataclass
class TradingDecision:
    """Structured output from the AI's trading analysis."""
    ai_model: str
    instrument: str
    action: SignalAction         # BUY | SELL | HOLD | CLOSE
    ai_mode: AIMode

    # Trade parameters (None if HOLD)
    confidence: float = 0.0      # 0.0 - 1.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_pct: float = 1.0

    # Reasoning
    reasoning: str = ""
    chain_of_thought: List[str] = field(default_factory=list)
    strategies_considered: List[str] = field(default_factory=list)
    strategy_chosen: Optional[str] = None
    market_thesis: str = ""

    # Raw response
    raw_response: str = ""
    error: Optional[str] = None

    @property
    def should_trade(self) -> bool:
        return self.action in (SignalAction.BUY, SignalAction.SELL) and self.confidence >= 0.6


# ─────────────────────────────────────────────
# Market Context Builder
# ─────────────────────────────────────────────

class MarketContextBuilder:
    """Builds the market context prompt for AI analysis."""

    @staticmethod
    def build(
        instrument: str,
        candles: List[Dict],
        indicators: Dict[str, Any],
        current_price: Dict,
        account_balance: float,
        open_trades: List[Dict],
        news_sentiment: Optional[Dict] = None,
        calendar_events: Optional[List[Dict]] = None,
        available_strategies: Optional[List[str]] = None,
    ) -> str:
        """Build a comprehensive market context string for the AI."""

        recent_candles = candles[-20:]  # last 20 candles
        candle_str = "\n".join([
            f"  {c['time'][:16]} | O:{c['open']:.5f} H:{c['high']:.5f} L:{c['low']:.5f} C:{c['close']:.5f} V:{c['volume']}"
            for c in recent_candles
        ])

        # Format indicators
        ind_lines = []
        for name, value in indicators.items():
            if isinstance(value, float):
                ind_lines.append(f"  {name}: {value:.5f}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    ind_lines.append(f"  {name}.{k}: {v:.5f}" if isinstance(v, float) else f"  {name}.{k}: {v}")
            else:
                ind_lines.append(f"  {name}: {value}")
        indicators_str = "\n".join(ind_lines)

        # Format open trades
        trades_str = "None"
        if open_trades:
            trades_str = "\n".join([
                f"  {t.get('instrument')} | {t.get('currentUnits')} units | P&L: {t.get('unrealizedPL', 0)}"
                for t in open_trades
            ])

        # Format news
        news_str = "No recent news."
        if news_sentiment:
            score = news_sentiment.get("score", 0)
            label = news_sentiment.get("label", "neutral")
            headlines = news_sentiment.get("headlines", [])[:3]
            news_str = f"Sentiment: {label} (score: {score:.2f})\nTop headlines:\n" + "\n".join(f"  - {h}" for h in headlines)

        # Format calendar
        calendar_str = "No major events upcoming."
        if calendar_events:
            calendar_str = "\n".join([
                f"  [{e.get('impact')}] {e.get('event_time')} - {e.get('title')} ({e.get('currency')})"
                for e in calendar_events[:5]
            ])

        # Format strategies
        strategies_str = "None loaded."
        if available_strategies:
            strategies_str = "\n".join(f"  - {s}" for s in available_strategies)

        return f"""
═══════════════════════════════════════════════
MARKET ANALYSIS REQUEST — {instrument}
═══════════════════════════════════════════════

CURRENT PRICE:
  Bid: {current_price.get('bid', 0):.5f}
  Ask: {current_price.get('ask', 0):.5f}
  Spread: {current_price.get('spread', 0):.5f}

RECENT CANDLES (M15, last 20):
{candle_str}

TECHNICAL INDICATORS:
{indicators_str}

NEWS SENTIMENT:
{news_str}

UPCOMING ECONOMIC EVENTS:
{calendar_str}

ACCOUNT STATUS:
  Balance: ${account_balance:,.2f}
  Open Trades:
{trades_str}

AVAILABLE STRATEGY LIBRARY:
{strategies_str}

═══════════════════════════════════════════════
"""


# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────

TRADING_SYSTEM_PROMPT = """You are APEX, an autonomous AI forex and CFD trader.

You have complete freedom — you can:
1. Use any strategy from the strategy library
2. Combine multiple strategies with your own reasoning (Hybrid)
3. Ignore all strategies and trade purely from your own analysis (Free Will)

You MUST respond with a valid JSON object and nothing else. No markdown, no preamble.

JSON format:
{
  "mode": "STRATEGY" | "HYBRID" | "FREE_WILL",
  "action": "BUY" | "SELL" | "HOLD" | "CLOSE",
  "confidence": 0.0-1.0,
  "entry_price": null or float,
  "stop_loss": null or float,
  "take_profit": null or float,
  "risk_pct": 0.5-2.0,
  "strategy_chosen": null or "strategy_name",
  "strategies_considered": ["list", "of", "strategies"],
  "chain_of_thought": [
    "Step 1: I observed that...",
    "Step 2: The indicator shows...",
    "Step 3: My conclusion is..."
  ],
  "market_thesis": "Brief summary of your market view",
  "reasoning": "Full explanation of why you made this decision"
}

RULES:
- Only trade if confidence >= 0.6. Otherwise action = "HOLD"
- Always provide stop_loss if action is BUY or SELL
- risk_pct must be between 0.5 and 2.0 (% of account per trade)
- Be honest about your uncertainty
- Consider news events and economic calendar before trading
- Never risk more than 2% per trade
- If there is a high-impact news event in the next 2 hours, action should be HOLD unless you have very strong conviction
"""


# ─────────────────────────────────────────────
# Free Will Agent
# ─────────────────────────────────────────────

class FreeWillAgent:
    """
    The core AI trading agent.
    Each model instance runs independently.
    """

    def __init__(self, ai_manager: AIManager, strategy_registry: StrategyRegistry):
        self.ai = ai_manager
        self.strategies = strategy_registry

    async def analyze(
        self,
        model: str,
        instrument: str,
        candles: List[Dict],
        indicators: Dict,
        current_price: Dict,
        account_balance: float,
        open_trades: List[Dict],
        news_sentiment: Optional[Dict] = None,
        calendar_events: Optional[List] = None,
    ) -> TradingDecision:
        """
        Ask an AI model to analyze market data and decide on a trade.
        Returns a structured TradingDecision.
        """
        available_strategies = self.strategies.list_strategy_names()

        # Build context
        market_context = MarketContextBuilder.build(
            instrument=instrument,
            candles=candles,
            indicators=indicators,
            current_price=current_price,
            account_balance=account_balance,
            open_trades=open_trades,
            news_sentiment=news_sentiment,
            calendar_events=calendar_events,
            available_strategies=available_strategies,
        )

        # Ask AI
        response: AIResponse = await self.ai.ask(
            model=model,
            system=TRADING_SYSTEM_PROMPT,
            user=market_context,
        )

        if not response.success:
            logger.error(f"{model} analysis failed: {response.error}")
            return TradingDecision(
                ai_model=model,
                instrument=instrument,
                action=SignalAction.HOLD,
                ai_mode=AIMode.FREE_WILL,
                error=response.error,
                reasoning="AI request failed",
            )

        # Parse JSON response
        return self._parse_response(model, instrument, response.content)

    def _parse_response(
        self, model: str, instrument: str, content: str
    ) -> TradingDecision:
        """Parse AI JSON response into TradingDecision."""
        try:
            # Strip any accidental markdown
            clean = content.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            data = json.loads(clean)

            return TradingDecision(
                ai_model=model,
                instrument=instrument,
                action=SignalAction(data.get("action", "HOLD")),
                ai_mode=AIMode(data.get("mode", "FREE_WILL")),
                confidence=float(data.get("confidence", 0.0)),
                entry_price=data.get("entry_price"),
                stop_loss=data.get("stop_loss"),
                take_profit=data.get("take_profit"),
                risk_pct=float(data.get("risk_pct", 1.0)),
                strategy_chosen=data.get("strategy_chosen"),
                strategies_considered=data.get("strategies_considered", []),
                chain_of_thought=data.get("chain_of_thought", []),
                market_thesis=data.get("market_thesis", ""),
                reasoning=data.get("reasoning", ""),
                raw_response=content,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse {model} response: {e}\nContent: {content[:200]}")
            return TradingDecision(
                ai_model=model,
                instrument=instrument,
                action=SignalAction.HOLD,
                ai_mode=AIMode.FREE_WILL,
                error=f"Parse error: {e}",
                raw_response=content,
                reasoning="Could not parse AI response as JSON",
            )

    async def analyze_all_models(
        self,
        instrument: str,
        candles: List[Dict],
        indicators: Dict,
        current_price: Dict,
        account_balance: float,
        open_trades: List[Dict],
        news_sentiment: Optional[Dict] = None,
        calendar_events: Optional[List] = None,
    ) -> Dict[str, TradingDecision]:
        """Run all AI models in parallel for competition mode."""
        import asyncio
        models = self.ai.available_models()
        tasks = [
            self.analyze(
                model=m,
                instrument=instrument,
                candles=candles,
                indicators=indicators,
                current_price=current_price,
                account_balance=account_balance,
                open_trades=open_trades,
                news_sentiment=news_sentiment,
                calendar_events=calendar_events,
            )
            for m in models
        ]
        results = await asyncio.gather(*tasks)
        return {m: r for m, r in zip(models, results)}
