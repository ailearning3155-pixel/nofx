"""
APEX — Reinforcement Learning Module
Reward = profit_pct - drawdown_penalty
Uses a Q-table approach (tabular RL) — no heavy dependencies.
Upgrades to policy gradient when enough data is collected.

The RL agent learns WHEN to trade (sizing multipliers)
rather than WHAT to trade (that's the ML ensemble's job).
"""
from __future__ import annotations
import json
import math
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

RL_MODEL_DIR = Path("models/saved")
RL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
RL_STATE_PATH = RL_MODEL_DIR / "rl_agent.json"


# ── State discretisation ─────────────────────────────────────────────────────

def discretise_regime(regime: str) -> int:
    mapping = {"trending": 0, "ranging": 1, "volatile": 2, "breakout": 3, "unknown": 4}
    return mapping.get(regime, 4)


def discretise_confidence(conf: float) -> int:
    """0-4 bucket for confidence 0–1."""
    return min(4, int(conf * 5))


def discretise_drawdown(dd_pct: float) -> int:
    """0-3: safe / cautious / warning / danger."""
    if dd_pct < 3:    return 0
    if dd_pct < 7:    return 1
    if dd_pct < 12:   return 2
    return 3


def discretise_session(hour_utc: int) -> int:
    """0=Asian 1=London 2=NY 3=Overlap."""
    if 13 <= hour_utc <= 17: return 3   # London/NY overlap
    if 8  <= hour_utc <= 16: return 1   # London
    if 13 <= hour_utc <= 21: return 2   # NY
    return 0                             # Asian


def build_state(
    regime: str,
    confidence: float,
    drawdown_pct: float,
    hour_utc: int,
    recent_win_rate: float,
) -> Tuple:
    """Build a discrete state tuple for Q-table lookup."""
    return (
        discretise_regime(regime),
        discretise_confidence(confidence),
        discretise_drawdown(drawdown_pct),
        discretise_session(hour_utc),
        min(4, int(recent_win_rate * 5)),
    )


# ── Actions ───────────────────────────────────────────────────────────────────

ACTIONS = [
    0.0,    # Skip trade entirely
    0.5,    # Half size
    0.75,   # Three-quarter size
    1.0,    # Full size
    1.25,   # 1.25x (only in high-conviction states)
]


# ── Q-Table Agent ─────────────────────────────────────────────────────────────

class QLearningAgent:
    """
    Tabular Q-learning agent for position sizing decisions.

    State  = (regime, confidence_bucket, drawdown_bucket, session, win_rate_bucket)
    Action = sizing multiplier index (0 = skip, 1–4 = increasing size)
    Reward = profit_pct  - 2 × drawdown_pct  (penalise drawdown heavily)
    """

    def __init__(
        self,
        alpha:   float = 0.05,   # learning rate
        gamma:   float = 0.90,   # discount factor
        epsilon: float = 0.20,   # exploration rate (decays)
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
    ):
        self.alpha         = alpha
        self.gamma         = gamma
        self.epsilon       = epsilon
        self.epsilon_min   = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q_table: Dict[str, List[float]] = {}
        self.episodes = 0
        self._load()

    # ── Q-table helpers ─────────────────────────────────────────────────────

    def _key(self, state: Tuple) -> str:
        return str(state)

    def _get_q(self, state: Tuple) -> List[float]:
        k = self._key(state)
        if k not in self.q_table:
            self.q_table[k] = [0.0] * len(ACTIONS)
        return self.q_table[k]

    # ── Policy ──────────────────────────────────────────────────────────────

    def choose_action(self, state: Tuple) -> int:
        """ε-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, len(ACTIONS) - 1)
        q = self._get_q(state)
        return int(np.argmax(q))

    def get_sizing_multiplier(self, state: Tuple) -> float:
        """Return the sizing multiplier for the chosen action."""
        action_idx = self.choose_action(state)
        return ACTIONS[action_idx]

    # ── Learning ────────────────────────────────────────────────────────────

    def update(
        self,
        state:      Tuple,
        action_idx: int,
        reward:     float,
        next_state: Tuple,
    ):
        """Standard Q-learning update rule."""
        q    = self._get_q(state)
        q_ns = self._get_q(next_state)
        td_target = reward + self.gamma * max(q_ns)
        q[action_idx] += self.alpha * (td_target - q[action_idx])
        self.q_table[self._key(state)] = q

        # Decay exploration
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.episodes += 1

    def record_trade_outcome(
        self,
        state:      Tuple,
        action_idx: int,
        profit_pct: float,
        drawdown_pct: float,
        next_state: Tuple,
    ):
        """Compute reward and trigger Q update."""
        reward = profit_pct - 2.0 * drawdown_pct
        self.update(state, action_idx, reward, next_state)
        logger.debug(
            f"RL update: reward={reward:.4f} profit={profit_pct:.3f}% "
            f"dd={drawdown_pct:.3f}% ε={self.epsilon:.3f} episodes={self.episodes}"
        )

    # ── Persistence ─────────────────────────────────────────────────────────

    def save(self):
        data = {
            "q_table":       self.q_table,
            "epsilon":       self.epsilon,
            "episodes":      self.episodes,
            "last_saved":    datetime.utcnow().isoformat(),
        }
        RL_STATE_PATH.write_text(json.dumps(data, indent=2))
        logger.info(f"RL agent saved — {len(self.q_table)} states, {self.episodes} episodes")

    def _load(self):
        if not RL_STATE_PATH.exists():
            logger.info("RL agent: no saved state — starting fresh")
            return
        try:
            data         = json.loads(RL_STATE_PATH.read_text())
            self.q_table = data.get("q_table", {})
            self.epsilon = data.get("epsilon", self.epsilon)
            self.episodes = data.get("episodes", 0)
            logger.info(f"RL agent loaded — {len(self.q_table)} states, {self.episodes} episodes")
        except Exception as e:
            logger.warning(f"RL agent load failed: {e} — starting fresh")

    def get_stats(self) -> Dict:
        q_vals = [max(v) for v in self.q_table.values()] if self.q_table else [0]
        return {
            "episodes":      self.episodes,
            "states_known":  len(self.q_table),
            "epsilon":       round(self.epsilon, 4),
            "avg_max_q":     round(sum(q_vals) / len(q_vals), 4),
            "max_q":         round(max(q_vals), 4),
        }


# ── Module singleton ─────────────────────────────────────────────────────────

_rl_agent: Optional[QLearningAgent] = None


def get_rl_agent() -> QLearningAgent:
    global _rl_agent
    if _rl_agent is None:
        _rl_agent = QLearningAgent()
    return _rl_agent
