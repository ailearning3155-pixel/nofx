"""APEX — Trade Dataset Collector (Implementation Guide Item 10)
Stores every executed trade with features for ML retraining."""
from __future__ import annotations
import csv, json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
CSV_FILE = DATA_DIR / "trade_dataset.csv"
FIELDS = ["timestamp","pair","strategy","ai_model","direction","entry_price","exit_price",
          "stop_loss","take_profit","confidence","ml_probability","regime","session",
          "profit_pct","won","hold_bars","sl_distance","features_json"]

@dataclass
class TradeRecord:
    pair:str; strategy:str; direction:str; entry_price:float; exit_price:float
    confidence:float; regime:str; won:bool
    ai_model:str=""; ml_probability:float=0.0
    stop_loss:Optional[float]=None; take_profit:Optional[float]=None
    session:str=""; hold_bars:int=0; sl_distance:float=0.0
    features:Dict[str,Any]=field(default_factory=dict)
    timestamp:str=field(default_factory=lambda:datetime.utcnow().isoformat())

    @property
    def profit_pct(self):
        if self.entry_price<=0: return 0.0
        if self.direction=="BUY": return (self.exit_price-self.entry_price)/self.entry_price*100
        return (self.entry_price-self.exit_price)/self.entry_price*100

class TradeDatasetCollector:
    def __init__(self):
        if not CSV_FILE.exists():
            with open(CSV_FILE,"w",newline="") as f:
                csv.DictWriter(f,fieldnames=FIELDS).writeheader()

    def record(self, trade: TradeRecord):
        row={"timestamp":trade.timestamp,"pair":trade.pair,"strategy":trade.strategy,
             "ai_model":trade.ai_model,"direction":trade.direction,
             "entry_price":round(trade.entry_price,5),"exit_price":round(trade.exit_price,5),
             "stop_loss":round(trade.stop_loss,5) if trade.stop_loss else "",
             "take_profit":round(trade.take_profit,5) if trade.take_profit else "",
             "confidence":round(trade.confidence,4),"ml_probability":round(trade.ml_probability,4),
             "regime":trade.regime,"session":trade.session,"profit_pct":round(trade.profit_pct,4),
             "won":int(trade.won),"hold_bars":trade.hold_bars,"sl_distance":round(trade.sl_distance,5),
             "features_json":json.dumps(trade.features)}
        with open(CSV_FILE,"a",newline="") as f:
            csv.DictWriter(f,fieldnames=FIELDS).writerow(row)

    def get_stats(self) -> dict:
        try:
            import pandas as pd
            df=pd.read_csv(CSV_FILE)
            if df.empty: return {"total":0}
            return {"total":len(df),"win_rate":round(df["won"].mean()*100,1),
                    "avg_profit":round(df["profit_pct"].mean(),3),
                    "by_strategy":df.groupby("strategy")["won"].mean().round(3).to_dict(),
                    "by_regime":df.groupby("regime")["won"].mean().round(3).to_dict()}
        except: return {"total":0}

_collector:Optional[TradeDatasetCollector]=None
def get_trade_collector() -> TradeDatasetCollector:
    global _collector
    if _collector is None: _collector=TradeDatasetCollector()
    return _collector
