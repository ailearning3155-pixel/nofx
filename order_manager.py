"""APEX — Order Lifecycle Manager (Implementation Guide Item 6)
Full state machine: CREATED → SUBMITTED → FILLED | PARTIAL | CANCELLED | REJECTED"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from loguru import logger

class OrderState(str,Enum):
    CREATED="CREATED"; SUBMITTED="SUBMITTED"; FILLED="FILLED"
    PARTIAL="PARTIAL"; CANCELLED="CANCELLED"; REJECTED="REJECTED"

class OrderSide(str,Enum):
    BUY="BUY"; SELL="SELL"

class OrderType(str,Enum):
    MARKET="MARKET"; LIMIT="LIMIT"; STOP="STOP"

@dataclass
class Order:
    instrument: str; side: OrderSide; units: int
    order_type: OrderType = OrderType.MARKET
    stop_loss: Optional[float]=None; take_profit: Optional[float]=None
    strategy: str=""; ai_model: str=""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    state: OrderState = OrderState.CREATED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    submitted_at: Optional[str]=None; filled_at: Optional[str]=None
    fill_price: Optional[float]=None; units_filled: int=0
    broker_order_id: Optional[str]=None; pnl: Optional[float]=None

    def submit(self):
        self.state=OrderState.SUBMITTED; self.submitted_at=datetime.utcnow().isoformat()
        logger.debug(f"Order {self.order_id} SUBMITTED")

    def fill(self, fill_price: float, units_filled: Optional[int]=None):
        filled = units_filled or self.units
        self.fill_price=fill_price; self.units_filled=filled; self.filled_at=datetime.utcnow().isoformat()
        self.state = OrderState.FILLED if filled>=self.units else OrderState.PARTIAL
        logger.info(f"Order {self.order_id} {self.state.value} @ {fill_price:.5f}")

    def cancel(self, reason: str=""):
        if self.state not in (OrderState.FILLED,OrderState.CANCELLED,OrderState.REJECTED):
            self.state=OrderState.CANCELLED
            logger.info(f"Order {self.order_id} CANCELLED: {reason}")

    def reject(self, reason: str=""):
        self.state=OrderState.REJECTED
        logger.warning(f"Order {self.order_id} REJECTED: {reason}")

    @property
    def is_active(self): return self.state in (OrderState.CREATED,OrderState.SUBMITTED,OrderState.PARTIAL)
    @property
    def is_terminal(self): return self.state in (OrderState.FILLED,OrderState.CANCELLED,OrderState.REJECTED)

    def to_dict(self): return {
        "order_id":self.order_id,"instrument":self.instrument,"side":self.side.value,
        "units":self.units,"units_filled":self.units_filled,"state":self.state.value,
        "fill_price":self.fill_price,"stop_loss":self.stop_loss,"take_profit":self.take_profit,
        "strategy":self.strategy,"ai_model":self.ai_model,"pnl":self.pnl,
        "created_at":self.created_at,"filled_at":self.filled_at,
    }

class OrderManager:
    def __init__(self):
        self._orders: Dict[str,Order] = {}
        self._active_by_instrument: Dict[str,str] = {}

    def create_order(self, instrument:str, side:OrderSide, units:int, order_type:OrderType=OrderType.MARKET,
                     stop_loss=None, take_profit=None, strategy="", ai_model="") -> Order:
        inst = instrument.upper()
        ex_id = self._active_by_instrument.get(inst)
        if ex_id and (ex:=self._orders.get(ex_id)) and ex.is_active:
            raise ValueError(f"Duplicate blocked: active order exists for {inst}")
        order = Order(instrument=inst,side=side,units=units,order_type=order_type,
                      stop_loss=stop_loss,take_profit=take_profit,strategy=strategy,ai_model=ai_model)
        self._orders[order.order_id]=order; self._active_by_instrument[inst]=order.order_id
        logger.info(f"📋 Order {order.order_id}: {inst} {side.value} {units:,}")
        return order

    def fill_order(self, order_id:str, fill_price:float, units_filled:Optional[int]=None):
        if o:=self._orders.get(order_id):
            o.fill(fill_price,units_filled)
            if o.state==OrderState.FILLED: self._active_by_instrument.pop(o.instrument,None)

    def cancel_order(self, order_id:str, reason:str=""):
        if o:=self._orders.get(order_id):
            o.cancel(reason); self._active_by_instrument.pop(o.instrument,None)

    def cancel_all_active(self, reason:str="Kill switch"):
        for o in self.get_active_orders(): self.cancel_order(o.order_id,reason)

    def get_active_orders(self): return [o for o in self._orders.values() if o.is_active]

    def get_summary(self) -> dict:
        all_orders = list(self._orders.values())
        filled=[o for o in all_orders if o.state==OrderState.FILLED]
        total_pnl=sum(o.pnl for o in filled if o.pnl)
        return {"total_orders":len(all_orders),"active_orders":len(self.get_active_orders()),
                "filled_orders":len(filled),"rejected_orders":len([o for o in all_orders if o.state==OrderState.REJECTED]),
                "cancelled_orders":len([o for o in all_orders if o.state==OrderState.CANCELLED]),
                "total_pnl":round(total_pnl,2),"active":[o.to_dict() for o in self.get_active_orders()]}

_om: Optional[OrderManager] = None
def get_order_manager() -> OrderManager:
    global _om
    if _om is None: _om = OrderManager()
    return _om
