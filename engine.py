"""
APEX — Debate Engine
4 AI agents debate a trade, Head Trader makes the final call.

Roles:
  🐂 BULL      — argues for buying
  🐻 BEAR      — argues for selling / against the trade
  📊 ANALYST   — neutral technical & fundamental view
  ⚠️  RISK_MGR  — evaluates risk, drawdown, position sizing
  🎯 HEAD_TRADER — reads all arguments, makes final decision
"""
import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from loguru import logger

from core.ai.clients import AIManager
from models.models import SignalAction


# ─────────────────────────────────────────────
# Debate Result
# ─────────────────────────────────────────────

@dataclass
class AgentArgument:
    role: str
    model: str
    argument: str
    stance: str             # BUY | SELL | HOLD
    confidence: float
    key_points: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DebateResult:
    instrument: str
    market_context: str

    bull: Optional[AgentArgument] = None
    bear: Optional[AgentArgument] = None
    analyst: Optional[AgentArgument] = None
    risk_manager: Optional[AgentArgument] = None

    final_action: SignalAction = SignalAction.HOLD
    final_confidence: float = 0.0
    final_reasoning: str = ""
    head_trader_model: str = ""

    consensus_reached: bool = False
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "instrument": self.instrument,
            "final_action": self.final_action.value,
            "final_confidence": self.final_confidence,
            "final_reasoning": self.final_reasoning,
            "head_trader_model": self.head_trader_model,
            "consensus_reached": self.consensus_reached,
            "duration_seconds": self.duration_seconds,
            "agents": {
                "bull": self._agent_to_dict(self.bull),
                "bear": self._agent_to_dict(self.bear),
                "analyst": self._agent_to_dict(self.analyst),
                "risk_manager": self._agent_to_dict(self.risk_manager),
            }
        }

    def _agent_to_dict(self, agent: Optional[AgentArgument]) -> Optional[Dict]:
        if agent is None:
            return None
        return {
            "role": agent.role,
            "model": agent.model,
            "argument": agent.argument,
            "stance": agent.stance,
            "confidence": agent.confidence,
            "key_points": agent.key_points,
            "error": agent.error,
        }


# ─────────────────────────────────────────────
# Agent Prompts
# ─────────────────────────────────────────────

BULL_PROMPT = """You are the BULL trader in a trading debate. Your job is to argue FOR a LONG (BUY) position.
Find every reason the price could go UP. Be persuasive but honest with your data.

Respond ONLY with valid JSON:
{
  "stance": "BUY",
  "confidence": 0.0-1.0,
  "argument": "Your full bullish argument",
  "key_points": ["point 1", "point 2", "point 3"]
}"""

BEAR_PROMPT = """You are the BEAR trader in a trading debate. Your job is to argue FOR a SHORT (SELL) position.
Find every reason the price could go DOWN. Be persuasive but honest with your data.

Respond ONLY with valid JSON:
{
  "stance": "SELL",
  "confidence": 0.0-1.0,
  "argument": "Your full bearish argument",
  "key_points": ["point 1", "point 2", "point 3"]
}"""

ANALYST_PROMPT = """You are the NEUTRAL ANALYST in a trading debate. Give an objective technical and fundamental view.
Do not be biased towards bull or bear. State the facts and what the data suggests.

Respond ONLY with valid JSON:
{
  "stance": "BUY" or "SELL" or "HOLD",
  "confidence": 0.0-1.0,
  "argument": "Your objective analysis",
  "key_points": ["observation 1", "observation 2", "observation 3"]
}"""

RISK_PROMPT = """You are the RISK MANAGER in a trading debate. Your job is to evaluate the RISK of any trade.
Consider: account drawdown, news events, spread costs, position sizing, and whether the reward justifies the risk.
You can veto any trade if the risk is too high.

Respond ONLY with valid JSON:
{
  "stance": "BUY" or "SELL" or "HOLD",
  "confidence": 0.0-1.0,
  "argument": "Your risk assessment",
  "key_points": ["risk 1", "risk 2", "risk 3"],
  "approved": true or false,
  "max_risk_pct": 0.5-2.0
}"""

HEAD_TRADER_PROMPT = """You are the HEAD TRADER. You have just heard arguments from 4 agents (Bull, Bear, Analyst, Risk Manager).
Weigh their arguments carefully. Make the FINAL trading decision.

CRITICAL RULES:
- If Risk Manager did NOT approve (approved: false), you must HOLD unless there is overwhelming consensus
- You need at least 3 out of 4 agents agreeing for action confidence above 0.7
- Be decisive but not reckless

Respond ONLY with valid JSON:
{
  "action": "BUY" or "SELL" or "HOLD",
  "confidence": 0.0-1.0,
  "reasoning": "Why you made this final decision, referencing each agent's argument",
  "who_won_the_debate": "BULL" or "BEAR" or "ANALYST" or "NEUTRAL",
  "entry_price": null or float,
  "stop_loss": null or float,
  "take_profit": null or float,
  "risk_pct": 0.5-2.0
}"""


# ─────────────────────────────────────────────
# Debate Engine
# ─────────────────────────────────────────────

class DebateEngine:
    """
    Orchestrates the 4-agent debate system.
    
    By default, assigns different AI models to different roles.
    This prevents echo chambers — each model brings its own perspective.
    """

    # Default role → model assignments
    # You can change these or make them configurable
    DEFAULT_ROLE_MODELS = {
        "bull":         "gpt4o",
        "bear":         "claude",
        "analyst":      "gemini",
        "risk_manager": "deepseek",
        "head_trader":  "grok",
    }

    def __init__(self, ai_manager: AIManager):
        self.ai = ai_manager
        self._assign_roles()

    def _assign_roles(self):
        """
        Assign available models to roles.
        Falls back gracefully if some models aren't configured.
        """
        available = self.ai.available_models()
        self.role_models = {}

        for role, preferred_model in self.DEFAULT_ROLE_MODELS.items():
            if preferred_model in available:
                self.role_models[role] = preferred_model
            elif available:
                # Use any available model as fallback
                self.role_models[role] = available[0]
            else:
                self.role_models[role] = None

        logger.info(f"Debate roles assigned: {self.role_models}")

    async def run_debate(
        self,
        instrument: str,
        market_context: str,
    ) -> DebateResult:
        """
        Run a full debate round for an instrument.
        
        1. Bull, Bear, Analyst, Risk Manager argue in parallel
        2. Head Trader reads all arguments and decides
        
        Returns a DebateResult with all arguments and final decision.
        """
        start_time = time.time()
        result = DebateResult(instrument=instrument, market_context=market_context)

        logger.info(f"🗣️  Starting debate for {instrument}")

        # Phase 1: Run all 4 agents in parallel
        bull_task = self._run_agent("bull", BULL_PROMPT, market_context)
        bear_task = self._run_agent("bear", BEAR_PROMPT, market_context)
        analyst_task = self._run_agent("analyst", ANALYST_PROMPT, market_context)
        risk_task = self._run_agent("risk_manager", RISK_PROMPT, market_context)

        result.bull, result.bear, result.analyst, result.risk_manager = await asyncio.gather(
            bull_task, bear_task, analyst_task, risk_task
        )

        # Phase 2: Head Trader makes final call
        debate_summary = self._format_debate_summary(result)
        result.final_action, result.final_confidence, result.final_reasoning, result.head_trader_model = \
            await self._run_head_trader(market_context, debate_summary)

        # Check consensus
        result.consensus_reached = self._check_consensus(result)
        result.duration_seconds = time.time() - start_time

        logger.info(
            f"✅ Debate complete: {instrument} → {result.final_action.value} "
            f"(confidence: {result.final_confidence:.2f}, consensus: {result.consensus_reached})"
        )

        return result

    async def _run_agent(
        self, role: str, system_prompt: str, market_context: str
    ) -> AgentArgument:
        """Run a single debate agent."""
        model = self.role_models.get(role)
        if not model:
            return AgentArgument(role=role, model="none", argument="Model not available",
                                 stance="HOLD", confidence=0.0, error="No model assigned")

        response = await self.ai.ask(model=model, system=system_prompt, user=market_context)

        if not response.success:
            return AgentArgument(role=role, model=model, argument="",
                                 stance="HOLD", confidence=0.0, error=response.error)

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content.strip())
            return AgentArgument(
                role=role,
                model=model,
                argument=data.get("argument", ""),
                stance=data.get("stance", "HOLD"),
                confidence=float(data.get("confidence", 0.0)),
                key_points=data.get("key_points", []),
            )
        except Exception as e:
            logger.warning(f"Failed to parse {role} response: {e}")
            return AgentArgument(role=role, model=model, argument=response.content,
                                 stance="HOLD", confidence=0.0, error=f"Parse error: {e}")

    def _format_debate_summary(self, result: DebateResult) -> str:
        """Format all agent arguments for the Head Trader."""
        parts = ["=== DEBATE SUMMARY ===\n"]

        for role_name, agent in [
            ("🐂 BULL", result.bull),
            ("🐻 BEAR", result.bear),
            ("📊 ANALYST", result.analyst),
            ("⚠️  RISK MANAGER", result.risk_manager),
        ]:
            if agent:
                parts.append(f"\n{role_name} [{agent.model.upper()}] — Stance: {agent.stance} (confidence: {agent.confidence:.2f})")
                parts.append(f"Argument: {agent.argument}")
                if agent.key_points:
                    parts.append("Key points:")
                    for pt in agent.key_points:
                        parts.append(f"  • {pt}")

        parts.append("\n=== YOUR DECISION ===")
        parts.append("Review all arguments above and make your final trading decision.")

        return "\n".join(parts)

    async def _run_head_trader(
        self, market_context: str, debate_summary: str
    ) -> tuple:
        """Run the Head Trader to make the final call."""
        model = self.role_models.get("head_trader")
        if not model:
            return SignalAction.HOLD, 0.0, "No head trader model", "none"

        full_context = f"{market_context}\n\n{debate_summary}"
        response = await self.ai.ask(model=model, system=HEAD_TRADER_PROMPT, user=full_context)

        if not response.success:
            return SignalAction.HOLD, 0.0, f"Error: {response.error}", model

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content.strip())
            action = SignalAction(data.get("action", "HOLD"))
            confidence = float(data.get("confidence", 0.0))
            reasoning = data.get("reasoning", "")
            return action, confidence, reasoning, model

        except Exception as e:
            logger.warning(f"Head Trader parse error: {e}")
            return SignalAction.HOLD, 0.0, f"Parse error: {e}", model

    def _check_consensus(self, result: DebateResult) -> bool:
        """Check if enough agents agree with the final decision."""
        votes = []
        for agent in [result.bull, result.bear, result.analyst, result.risk_manager]:
            if agent and not agent.error:
                votes.append(agent.stance)

        if not votes:
            return False

        final = result.final_action.value
        agreeing = sum(1 for v in votes if v == final)
        return agreeing >= 2  # at least 2 of 4 agents agree
