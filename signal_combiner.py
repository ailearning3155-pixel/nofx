"""
APEX — Signal Combiner Engine
Aggregates outputs from multiple strategies into a single weighted decision score.
Filters by market regime, confidence threshold, and ML probability gate.
"""
from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger

from core.strategies.registry import StrategySignal, get_strategy_registry
from core.market_regime import RegimeResult, Regime, get_regime_detector
from models.models import SignalAction


# ── Category weights (sum to ~1.0) ─────────────────────────────────────────
CATEGORY_WEIGHTS: Dict[str, float] = {
    "trend":          1.0,
    "mean_reversion": 0.9,
    "volatility":     0.8,
    "scalping":       0.85,
    "stat_arb":       0.9,
    "microstructure": 0.75,
    "composite":      1.1,    # composite already blends multiple signals
    "macro":          0.7,
    "ml":             1.2,    # ML signals get a boost
}

# Strategies known to be high-quality — upweighted
HIGH_QUALITY_STRATEGIES = {
    "gradient_boosting_signal", "random_forest_signal",
    "hidden_markov_regime", "kalman_filter_trend",
    "fvg_market_structure", "ob_liquidity_sweep",
}


@dataclass
class CombinedSignal:
    """Unified output from the signal combiner."""
    action:         SignalAction
    score:          float                          # -1.0 (strong sell) to +1.0 (strong buy)
    confidence:     float                          # 0.0 – 1.0
    regime:         str = "unknown"
    regime_confidence: float = 0.0
    strategies_considered: int = 0
    strategies_actionable: int = 0
    buy_votes:      int   = 0
    sell_votes:     int   = 0
    hold_votes:     int   = 0
    avg_entry:      Optional[float] = None
    avg_stop_loss:  Optional[float] = None
    avg_take_profit: Optional[float] = None
    top_signals:    List[Dict] = field(default_factory=list)
    regime_blocked: bool = False
    ml_filtered:    bool = False
    reason:         str  = ""

    @property
    def should_trade(self) -> bool:
        return (
            self.action in (SignalAction.BUY, SignalAction.SELL)
            and self.confidence >= 0.55
            and not self.regime_blocked
            and not self.ml_filtered
        )


class SignalCombiner:
    """
    Aggregates all strategy signals into a single trading decision.

    Pipeline:
    1. Run all (or specified) strategies
    2. Filter by market regime suitability
    3. Weight signals by category quality and individual strategy strength
    4. Calculate directional score and confidence
    5. Apply ML probability gate if available
    """

    def __init__(
        self,
        min_confidence: float = 0.55,
        min_strategies: int   = 2,    # min agreeing strategies to act
        ml_threshold:   float = 0.65, # ML probability gate
        use_regime_filter: bool = True,
    ):
        self.min_confidence   = min_confidence
        self.min_strategies   = min_strategies
        self.ml_threshold     = ml_threshold
        self.use_regime_filter = use_regime_filter

    def combine(
        self,
        signals: Dict[str, StrategySignal],
        regime:  Optional[RegimeResult] = None,
        ml_prob: Optional[float] = None,        # ML ensemble probability (0–1)
        strategy_weights: Optional[Dict[str, float]] = None,  # dynamic weights
    ) -> CombinedSignal:
        """
        Combine a dict of {strategy_name: StrategySignal} into one decision.
        """
        if not signals:
            return CombinedSignal(
                action=SignalAction.HOLD,
                score=0.0,
                confidence=0.0,
                reason="No signals received",
            )

        actionable = {
            name: sig for name, sig in signals.items()
            if sig and sig.action in (SignalAction.BUY, SignalAction.SELL)
        }

        # ── Regime filter ─────────────────────────────────────────────────
        regime_blocked = False
        if self.use_regime_filter and regime and regime.regime != Regime.UNKNOWN:
            filtered = {}
            for name, sig in actionable.items():
                strat_cls = get_strategy_registry()._strategies.get(name)
                category  = getattr(strat_cls, "category", "unknown") if strat_cls else "unknown"
                if regime.allows_strategy(category):
                    filtered[name] = sig
                else:
                    logger.debug(f"Regime filter: {name} blocked in {regime.regime.value}")
            if not filtered and actionable:
                regime_blocked = True
            actionable = filtered

        if not actionable:
            return CombinedSignal(
                action=SignalAction.HOLD,
                score=0.0,
                confidence=0.0,
                strategies_considered=len(signals),
                regime=regime.regime.value if regime else "unknown",
                regime_confidence=regime.confidence if regime else 0.0,
                regime_blocked=regime_blocked,
                reason="No actionable signals after regime filter",
            )

        # ── Weighted scoring ─────────────────────────────────────────────
        buy_score  = 0.0
        sell_score = 0.0
        buy_votes  = 0
        sell_votes = 0
        hold_votes = len(signals) - len(actionable)

        entries, stops, tps = [], [], []
        top_signals = []

        for name, sig in actionable.items():
            strat_cls = get_strategy_registry()._strategies.get(name)
            category  = getattr(strat_cls, "category", "unknown") if strat_cls else "unknown"

            # Category weight
            cat_weight = CATEGORY_WEIGHTS.get(category, 0.75)

            # High-quality bonus
            quality_bonus = 1.2 if name in HIGH_QUALITY_STRATEGIES else 1.0

            # Dynamic weight from performance tracker
            dyn_weight = strategy_weights.get(name, 1.0) if strategy_weights else 1.0

            weight = cat_weight * quality_bonus * dyn_weight * sig.strength

            if sig.action == SignalAction.BUY:
                buy_score  += weight
                buy_votes  += 1
                if sig.entry:      entries.append(sig.entry)
                if sig.stop_loss:  stops.append(sig.stop_loss)
                if sig.take_profit: tps.append(sig.take_profit)
            elif sig.action == SignalAction.SELL:
                sell_score += weight
                sell_votes += 1
                if sig.entry:      entries.append(sig.entry)
                if sig.stop_loss:  stops.append(sig.stop_loss)
                if sig.take_profit: tps.append(sig.take_profit)

            top_signals.append({
                "name":     name,
                "action":   sig.action.value,
                "strength": round(sig.strength, 3),
                "weight":   round(weight, 3),
                "reason":   sig.reason[:100],
            })

        total = buy_score + sell_score or 1.0
        net_score = (buy_score - sell_score) / total   # -1 to +1

        # Directional decision
        if net_score > 0.15 and buy_votes >= self.min_strategies:
            action = SignalAction.BUY
            raw_confidence = buy_score / total
        elif net_score < -0.15 and sell_votes >= self.min_strategies:
            action = SignalAction.SELL
            raw_confidence = sell_score / total
        else:
            action = SignalAction.HOLD
            raw_confidence = abs(net_score)

        # ── ML probability gate ──────────────────────────────────────────
        ml_filtered = False
        if ml_prob is not None and action in (SignalAction.BUY, SignalAction.SELL):
            if ml_prob < self.ml_threshold:
                ml_filtered = True
                logger.info(
                    f"ML filter blocked {action.value}: ml_prob={ml_prob:.3f} < {self.ml_threshold}"
                )
                action = SignalAction.HOLD

        # Blend ML probability into confidence if available
        if ml_prob is not None:
            blended = 0.6 * raw_confidence + 0.4 * ml_prob
        else:
            blended = raw_confidence

        confidence = round(min(blended, 0.98), 3)

        # Average entry / SL / TP from agreeing signals
        avg_entry = statistics.mean(entries) if entries else None
        avg_sl    = statistics.mean(stops)   if stops   else None
        avg_tp    = statistics.mean(tps)     if tps     else None

        # Sort top signals by weight desc
        top_signals.sort(key=lambda x: x["weight"], reverse=True)

        return CombinedSignal(
            action=action,
            score=round(net_score, 4),
            confidence=confidence,
            regime=regime.regime.value if regime else "unknown",
            regime_confidence=regime.confidence if regime else 0.0,
            strategies_considered=len(signals),
            strategies_actionable=len(actionable),
            buy_votes=buy_votes,
            sell_votes=sell_votes,
            hold_votes=hold_votes,
            avg_entry=avg_entry,
            avg_stop_loss=avg_sl,
            avg_take_profit=avg_tp,
            top_signals=top_signals[:5],
            regime_blocked=regime_blocked,
            ml_filtered=ml_filtered,
            reason=f"score={net_score:.3f} buy={buy_votes} sell={sell_votes} conf={confidence:.2f}",
        )

    def run_all_and_combine(
        self,
        df,
        current_price: float,
        regime: Optional[RegimeResult] = None,
        ml_prob: Optional[float] = None,
        strategy_weights: Optional[Dict[str, float]] = None,
    ) -> CombinedSignal:
        """Convenience: run all strategies then combine."""
        registry = get_strategy_registry()
        signals  = registry.run_all(df, current_price)
        return self.combine(signals, regime=regime, ml_prob=ml_prob, strategy_weights=strategy_weights)


# Singleton
_combiner: Optional[SignalCombiner] = None

def get_signal_combiner() -> SignalCombiner:
    global _combiner
    if _combiner is None:
        _combiner = SignalCombiner()
    return _combiner
