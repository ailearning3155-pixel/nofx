"""APEX — Portfolio Allocation Layer (Implementation Guide Item 9)
Allocates capital across strategy categories:
Trend 35% | Mean Reversion 20% | Stat Arb 20% | Volatility 15% | Scalping 10%"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

TARGET_ALLOCATIONS: Dict[str,float] = {
    "trend":0.35,"mean_reversion":0.20,"stat_arb":0.20,
    "volatility":0.15,"scalping":0.10,"composite":0.0,
    "microstructure":0.0,"macro":0.0,"ml":0.0,
}

@dataclass
class CategoryBucket:
    category: str; allocated: float=0.0; deployed: float=0.0
    realised_pnl: float=0.0; trades: int=0; wins: int=0
    peak_equity: float=0.0; pnls: List[float]=field(default_factory=list)

    @property
    def win_rate(self): return self.wins/self.trades*100 if self.trades else 0.0
    @property
    def available(self): return max(0.0, self.allocated - self.deployed)
    @property
    def sharpe(self):
        if len(self.pnls)<5: return 0.0
        import statistics
        m=statistics.mean(self.pnls); s=statistics.stdev(self.pnls)
        return round(m/(s+1e-9)*math.sqrt(252),2)

    def to_dict(self):
        return {"category":self.category,"allocated":round(self.allocated,2),"deployed":round(self.deployed,2),
                "available":round(self.available,2),"realised_pnl":round(self.realised_pnl,2),
                "win_rate":round(self.win_rate,1),"trades":self.trades,"sharpe":self.sharpe}

class PortfolioAllocator:
    def __init__(self, allocs: Optional[Dict[str,float]]=None):
        self.allocs = allocs or TARGET_ALLOCATIONS.copy()
        total = sum(self.allocs.values())
        if total>0: self.allocs = {k:v/total for k,v in self.allocs.items()}
        self._total: float = 0.0
        self._buckets: Dict[str,CategoryBucket] = {k:CategoryBucket(category=k) for k in self.allocs}
        self._last_rebalance: Optional[datetime] = None

    def set_total_capital(self, capital: float):
        self._total = capital
        for cat,pct in self.allocs.items():
            b=self._buckets.setdefault(cat,CategoryBucket(category=cat))
            b.allocated=capital*pct
            if b.allocated>b.peak_equity: b.peak_equity=b.allocated

    def get_available(self, category: str) -> float:
        return self._buckets.get(category,CategoryBucket(category=category)).available

    def can_open(self, category: str, cost: float) -> Tuple[bool,str]:
        avail=self.get_available(category)
        if avail<cost: return False,f"{category}: ${avail:.0f} available < ${cost:.0f} needed"
        return True,f"${avail:.0f} available"

    def record_open(self, category:str, cost:float):
        if b:=self._buckets.get(category): b.deployed+=cost

    def record_close(self, category:str, cost:float, pnl:float):
        if b:=self._buckets.get(category):
            b.deployed=max(0,b.deployed-cost); b.realised_pnl+=pnl
            b.allocated+=pnl; b.trades+=1; b.pnls.append(pnl)
            if pnl>0: b.wins+=1
            if b.allocated>b.peak_equity: b.peak_equity=b.allocated

    def rebalance(self):
        for cat,pct in self.allocs.items():
            if b:=self._buckets.get(cat):
                b.allocated=max(0,b.allocated+(self._total*pct-b.allocated)*0.5)
        self._last_rebalance=datetime.utcnow()

    def get_summary(self) -> dict:
        return {"total_capital":round(self._total,2),
                "total_deployed":round(sum(b.deployed for b in self._buckets.values()),2),
                "total_pnl":round(sum(b.realised_pnl for b in self._buckets.values()),2),
                "last_rebalance":self._last_rebalance.isoformat() if self._last_rebalance else None,
                "allocations":{k:f"{v:.0%}" for k,v in self.allocs.items()},
                "categories":{k:b.to_dict() for k,b in self._buckets.items()}}

_alloc: Optional[PortfolioAllocator]=None
def get_portfolio_allocator() -> PortfolioAllocator:
    global _alloc
    if _alloc is None: _alloc=PortfolioAllocator()
    return _alloc
