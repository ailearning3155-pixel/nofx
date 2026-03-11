"""
APEX — OANDA v20 Connector
Handles all communication with OANDA: REST calls, streaming, order management
"""
import asyncio
from typing import AsyncGenerator, Optional, Dict, List, Callable
from datetime import datetime
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.positions as positions
from oandapyV20.contrib.requests import MarketOrderRequest, TakeProfitDetails, StopLossDetails
from loguru import logger
from config.settings import settings


class OandaConnector:
    """
    OANDA v20 API connector.
    
    Handles:
    - Account info & balance
    - Fetching candles (OHLCV)
    - Streaming live prices
    - Placing / closing orders
    - Querying open trades & positions
    """

    def __init__(self):
        env = settings.oanda.environment  # "practice" or "live"
        self.client = oandapyV20.API(
            access_token=settings.oanda.api_key,
            environment=env
        )
        self.account_id = settings.oanda.account_id
        self.is_paper = env == "practice"
        logger.info(f"OANDA connector initialized [{env.upper()}] account={self.account_id}")

    # ─────────────────────────────────────────────
    # Account
    # ─────────────────────────────────────────────

    def get_account(self) -> Dict:
        """Fetch full account details from OANDA."""
        r = accounts.AccountDetails(self.account_id)
        self.client.request(r)
        return r.response["account"]

    def get_balance(self) -> float:
        """Return current NAV (net asset value)."""
        acct = self.get_account()
        return float(acct["NAV"])

    def get_margin_used(self) -> float:
        acct = self.get_account()
        return float(acct["marginUsed"])

    # ─────────────────────────────────────────────
    # Candles / Market Data
    # ─────────────────────────────────────────────

    def get_candles(
        self,
        instrument: str,
        granularity: str = "M15",
        count: int = 200,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
    ) -> List[Dict]:
        """
        Fetch OHLCV candles for an instrument.
        
        Args:
            instrument: e.g. "EUR_USD", "XAU_USD", "US500"
            granularity: S5,S10,S15,S30,M1,M2,M4,M5,M10,M15,M30,H1,H2,H3,H4,H6,H8,H12,D,W,M
            count: number of candles (max 5000)
        
        Returns:
            List of dicts: {time, open, high, low, close, volume, complete}
        """
        params = {"granularity": granularity}
        if from_time and to_time:
            params["from"] = from_time
            params["to"] = to_time
        else:
            params["count"] = count

        r = instruments.InstrumentsCandles(instrument, params=params)
        self.client.request(r)

        candles = []
        for c in r.response["candles"]:
            if c["complete"]:  # only use completed candles
                candles.append({
                    "time": c["time"],
                    "open": float(c["mid"]["o"]),
                    "high": float(c["mid"]["h"]),
                    "low": float(c["mid"]["l"]),
                    "close": float(c["mid"]["c"]),
                    "volume": int(c["volume"]),
                    "complete": c["complete"],
                })
        return candles

    def get_current_price(self, instrument: str) -> Dict:
        """Get current bid/ask for an instrument."""
        params = {"instruments": instrument}
        r = pricing.PricingInfo(self.account_id, params=params)
        self.client.request(r)
        price = r.response["prices"][0]
        return {
            "instrument": instrument,
            "bid": float(price["bids"][0]["price"]),
            "ask": float(price["asks"][0]["price"]),
            "mid": (float(price["bids"][0]["price"]) + float(price["asks"][0]["price"])) / 2,
            "spread": float(price["asks"][0]["price"]) - float(price["bids"][0]["price"]),
            "tradeable": price["tradeable"],
            "time": price["time"],
        }

    def get_multiple_prices(self, instrument_list: List[str]) -> Dict[str, Dict]:
        """Get current prices for multiple instruments at once."""
        params = {"instruments": ",".join(instrument_list)}
        r = pricing.PricingInfo(self.account_id, params=params)
        self.client.request(r)
        result = {}
        for price in r.response["prices"]:
            instr = price["instrument"]
            result[instr] = {
                "bid": float(price["bids"][0]["price"]),
                "ask": float(price["asks"][0]["price"]),
                "mid": (float(price["bids"][0]["price"]) + float(price["asks"][0]["price"])) / 2,
                "tradeable": price["tradeable"],
                "time": price["time"],
            }
        return result

    # ─────────────────────────────────────────────
    # Orders
    # ─────────────────────────────────────────────

    def place_market_order(
        self,
        instrument: str,
        units: float,               # positive = buy, negative = sell
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        client_trade_id: Optional[str] = None,
    ) -> Dict:
        """
        Place a market order on OANDA.
        
        units > 0 = BUY, units < 0 = SELL
        """
        mktOrder = MarketOrderRequest(instrument=instrument, units=units)

        # Build order dict manually for full control
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(int(units)),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
            }
        }

        if stop_loss_price:
            order_data["order"]["stopLossOnFill"] = {
                "price": str(round(stop_loss_price, 5)),
                "timeInForce": "GTC"
            }

        if take_profit_price:
            order_data["order"]["takeProfitOnFill"] = {
                "price": str(round(take_profit_price, 5)),
                "timeInForce": "GTC"
            }

        if client_trade_id:
            order_data["order"]["clientExtensions"] = {
                "id": client_trade_id,
                "tag": "APEX",
            }

        r = orders.OrderCreate(self.account_id, data=order_data)
        self.client.request(r)
        logger.info(f"Order placed: {instrument} units={units}")
        return r.response

    def close_trade(self, oanda_trade_id: str, partial_units: Optional[float] = None) -> Dict:
        """Close an open trade fully or partially."""
        data = {}
        if partial_units:
            data = {"units": str(int(partial_units))}

        r = trades.TradeClose(self.account_id, oanda_trade_id, data=data or None)
        self.client.request(r)
        logger.info(f"Trade closed: {oanda_trade_id}")
        return r.response

    def close_all_trades(self) -> List[Dict]:
        """Emergency: close every open trade."""
        open_trades = self.get_open_trades()
        results = []
        for trade in open_trades:
            result = self.close_trade(trade["id"])
            results.append(result)
        logger.warning(f"Emergency close: closed {len(results)} trades")
        return results

    def modify_trade_sl_tp(
        self,
        oanda_trade_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict:
        """Modify stop loss / take profit on an open trade."""
        data = {}
        if stop_loss:
            data["stopLoss"] = {"price": str(round(stop_loss, 5)), "timeInForce": "GTC"}
        if take_profit:
            data["takeProfit"] = {"price": str(round(take_profit, 5)), "timeInForce": "GTC"}

        r = trades.TradeCRCDO(self.account_id, oanda_trade_id, data=data)
        self.client.request(r)
        return r.response

    # ─────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────

    def get_open_trades(self) -> List[Dict]:
        """Return all currently open trades."""
        r = trades.OpenTrades(self.account_id)
        self.client.request(r)
        return r.response.get("trades", [])

    def get_trade(self, oanda_trade_id: str) -> Dict:
        """Get details of a specific trade."""
        r = trades.TradeDetails(self.account_id, oanda_trade_id)
        self.client.request(r)
        return r.response["trade"]

    def get_open_positions(self) -> List[Dict]:
        """Return all open positions."""
        r = positions.OpenPositions(self.account_id)
        self.client.request(r)
        return r.response.get("positions", [])

    def get_pending_orders(self) -> List[Dict]:
        """Return all pending orders."""
        r = orders.OrdersPending(self.account_id)
        self.client.request(r)
        return r.response.get("orders", [])

    # ─────────────────────────────────────────────
    # Streaming
    # ─────────────────────────────────────────────

    async def stream_prices(
        self,
        instrument_list: List[str],
        callback: Callable[[Dict], None],
    ):
        """
        Stream live price ticks for instruments.
        Calls callback(tick_data) for every price update.
        
        This runs in a background task — do not block the callback.
        """
        from oandapyV20.endpoints.pricing import PricingStream
        params = {"instruments": ",".join(instrument_list)}
        r = PricingStream(self.account_id, params=params)

        logger.info(f"Starting price stream for: {instrument_list}")
        try:
            for tick in self.client.request(r):
                if tick.get("type") == "PRICE":
                    parsed = {
                        "instrument": tick["instrument"],
                        "bid": float(tick["bids"][0]["price"]),
                        "ask": float(tick["asks"][0]["price"]),
                        "time": tick["time"],
                        "tradeable": tick["tradeable"],
                    }
                    await asyncio.get_event_loop().run_in_executor(
                        None, callback, parsed
                    )
        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

    # ─────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────

    def calculate_units(
        self,
        instrument: str,
        risk_pct: float,
        stop_loss_pips: float,
        account_balance: Optional[float] = None,
    ) -> float:
        """
        Calculate position size based on risk percentage and stop loss distance.
        Uses OANDA's pip value conventions.
        """
        if account_balance is None:
            account_balance = self.get_balance()

        risk_amount = account_balance * (risk_pct / 100)

        # Pip value approximation (JPY pairs differ)
        if "JPY" in instrument:
            pip_value = 0.01
        elif instrument in ["XAU_USD", "XAG_USD"]:
            pip_value = 0.01
        else:
            pip_value = 0.0001

        units = risk_amount / (stop_loss_pips * pip_value)
        return round(units, 0)

    def pip_distance(self, instrument: str, price1: float, price2: float) -> float:
        """Calculate pip distance between two prices."""
        if "JPY" in instrument:
            return abs(price1 - price2) / 0.01
        elif instrument in ["XAU_USD"]:
            return abs(price1 - price2) / 0.01
        else:
            return abs(price1 - price2) / 0.0001


# Singleton
_connector: Optional[OandaConnector] = None

def get_oanda() -> OandaConnector:
    global _connector
    if _connector is None:
        _connector = OandaConnector()
    return _connector
