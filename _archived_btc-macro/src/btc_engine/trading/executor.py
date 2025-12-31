"""
Trade Executor - Paper and Live trading
"""
import hmac
import hashlib
import time
import urllib.request
import urllib.parse
import json
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class TradeResult:
    """Result of a trade execution"""
    success: bool
    order_id: Optional[str]
    price: float
    quantity: float
    side: str
    timestamp: datetime
    error: Optional[str] = None
    oco_order_id: Optional[str] = None  # OCO order for SL/TP


@dataclass
class OCOResult:
    """Result of OCO order placement"""
    success: bool
    order_list_id: Optional[str]
    stop_loss_order_id: Optional[str]
    take_profit_order_id: Optional[str]
    stop_price: float
    limit_price: float
    error: Optional[str] = None


class PaperTrader:
    """Paper trading simulator"""

    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.position = 0.0  # BTC quantity
        self.entry_price = 0.0
        self.trades = []

    def get_balance(self) -> dict:
        return {
            "usdt": self.balance,
            "btc": self.position,
            "entry_price": self.entry_price
        }

    def buy(self, price: float, usdt_amount: float) -> TradeResult:
        """Execute paper buy"""
        if usdt_amount > self.balance:
            return TradeResult(
                success=False,
                order_id=None,
                price=price,
                quantity=0,
                side="BUY",
                timestamp=datetime.now(),
                error="Insufficient balance"
            )

        quantity = usdt_amount / price
        self.balance -= usdt_amount
        self.position += quantity
        self.entry_price = price

        order_id = f"PAPER_{int(time.time() * 1000)}"
        self.trades.append({
            "order_id": order_id,
            "side": "BUY",
            "price": price,
            "quantity": quantity,
            "timestamp": datetime.now().isoformat()
        })

        return TradeResult(
            success=True,
            order_id=order_id,
            price=price,
            quantity=quantity,
            side="BUY",
            timestamp=datetime.now()
        )

    def sell(self, price: float, btc_quantity: float = None) -> TradeResult:
        """Execute paper sell"""
        if btc_quantity is None:
            btc_quantity = self.position

        if btc_quantity > self.position:
            return TradeResult(
                success=False,
                order_id=None,
                price=price,
                quantity=0,
                side="SELL",
                timestamp=datetime.now(),
                error="Insufficient position"
            )

        usdt_received = btc_quantity * price
        self.balance += usdt_received
        self.position -= btc_quantity

        if self.position == 0:
            self.entry_price = 0

        order_id = f"PAPER_{int(time.time() * 1000)}"
        self.trades.append({
            "order_id": order_id,
            "side": "SELL",
            "price": price,
            "quantity": btc_quantity,
            "timestamp": datetime.now().isoformat()
        })

        return TradeResult(
            success=True,
            order_id=order_id,
            price=price,
            quantity=btc_quantity,
            side="SELL",
            timestamp=datetime.now()
        )

    def create_oco_order(self, symbol: str, quantity: float, entry_price: float,
                         stop_loss_pct: float, take_profit_pct: float) -> OCOResult:
        """Paper OCO - just track SL/TP levels"""
        stop_price = round(entry_price * (1 - stop_loss_pct / 100), 2)
        take_profit_price = round(entry_price * (1 + take_profit_pct / 100), 2)

        self.oco_order = {
            "stop_price": stop_price,
            "take_profit_price": take_profit_price,
            "quantity": quantity
        }

        return OCOResult(
            success=True,
            order_list_id=f"PAPER_OCO_{int(time.time() * 1000)}",
            stop_loss_order_id=f"PAPER_SL_{int(time.time() * 1000)}",
            take_profit_order_id=f"PAPER_TP_{int(time.time() * 1000)}",
            stop_price=stop_price,
            limit_price=take_profit_price
        )

    def cancel_oco_order(self, symbol: str, order_list_id: str) -> bool:
        """Cancel paper OCO"""
        self.oco_order = None
        return True

    def get_position(self, symbol: str = "BTCUSDT") -> dict:
        """Get paper position"""
        return {
            "symbol": symbol,
            "btc_quantity": self.position,
            "usdt_balance": self.balance,
            "has_position": self.position > 0.0001
        }

    def check_oco_triggered(self, current_price: float) -> Optional[str]:
        """Check if paper OCO should trigger

        Returns: 'STOP_LOSS', 'TAKE_PROFIT', or None
        """
        if not hasattr(self, 'oco_order') or not self.oco_order:
            return None

        if current_price <= self.oco_order["stop_price"]:
            return "STOP_LOSS"
        elif current_price >= self.oco_order["take_profit_price"]:
            return "TAKE_PROFIT"
        return None


class LiveTrader:
    """Live trading via Binance API"""

    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret

        if testnet:
            self.BASE_URL = "https://testnet.binance.vision"

    def _sign(self, params: dict) -> str:
        """Create HMAC signature"""
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _request(self, method: str, endpoint: str, params: dict = None, signed: bool = False) -> dict:
        """Make API request"""
        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._sign(params)

        url = f"{self.BASE_URL}{endpoint}"
        if params:
            url += f"?{urllib.parse.urlencode(params)}"

        headers = {"X-MBX-APIKEY": self.api_key}

        req = urllib.request.Request(url, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def get_balance(self) -> dict:
        """Get account balance"""
        result = self._request("GET", "/api/v3/account", signed=True)

        if "error" in result:
            return {"error": result["error"]}

        balances = {}
        for asset in result.get("balances", []):
            free = float(asset["free"])
            if free > 0:
                balances[asset["asset"]] = free

        return balances

    def get_price(self, symbol: str = "BTCUSDT") -> float:
        """Get current price"""
        result = self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})
        return float(result.get("price", 0))

    def buy(self, symbol: str, usdt_amount: float) -> TradeResult:
        """Execute market buy"""
        price = self.get_price(symbol)
        quantity = round(usdt_amount / price, 5)

        params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "quantity": quantity
        }

        result = self._request("POST", "/api/v3/order", params, signed=True)

        if "error" in result or "code" in result:
            return TradeResult(
                success=False,
                order_id=None,
                price=price,
                quantity=quantity,
                side="BUY",
                timestamp=datetime.now(),
                error=result.get("error") or result.get("msg")
            )

        return TradeResult(
            success=True,
            order_id=str(result.get("orderId")),
            price=float(result.get("fills", [{}])[0].get("price", price)),
            quantity=float(result.get("executedQty", quantity)),
            side="BUY",
            timestamp=datetime.now()
        )

    def sell(self, symbol: str, btc_quantity: float) -> TradeResult:
        """Execute market sell"""
        price = self.get_price(symbol)
        quantity = round(btc_quantity, 5)

        params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET",
            "quantity": quantity
        }

        result = self._request("POST", "/api/v3/order", params, signed=True)

        if "error" in result or "code" in result:
            return TradeResult(
                success=False,
                order_id=None,
                price=price,
                quantity=quantity,
                side="SELL",
                timestamp=datetime.now(),
                error=result.get("error") or result.get("msg")
            )

        return TradeResult(
            success=True,
            order_id=str(result.get("orderId")),
            price=float(result.get("fills", [{}])[0].get("price", price)),
            quantity=float(result.get("executedQty", quantity)),
            side="SELL",
            timestamp=datetime.now()
        )

    def create_oco_order(self, symbol: str, quantity: float, entry_price: float,
                         stop_loss_pct: float, take_profit_pct: float) -> OCOResult:
        """Create OCO order for SL/TP on server side

        CRITICAL: This places SL/TP on exchange, not local
        - If bot crashes, SL/TP still executes
        - Prevents unintended losses from connection issues
        """
        # Calculate prices
        stop_price = round(entry_price * (1 - stop_loss_pct / 100), 2)
        stop_limit_price = round(stop_price * 0.995, 2)  # 0.5% below stop for slippage
        take_profit_price = round(entry_price * (1 + take_profit_pct / 100), 2)

        quantity = round(quantity, 5)

        # OCO requires: stopPrice, stopLimitPrice, stopLimitTimeInForce, price (TP)
        params = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": take_profit_price,  # Take profit limit price
            "stopPrice": stop_price,  # Stop trigger price
            "stopLimitPrice": stop_limit_price,  # Stop limit price
            "stopLimitTimeInForce": "GTC"
        }

        result = self._request("POST", "/api/v3/order/oco", params, signed=True)

        if "error" in result or "code" in result:
            return OCOResult(
                success=False,
                order_list_id=None,
                stop_loss_order_id=None,
                take_profit_order_id=None,
                stop_price=stop_price,
                limit_price=take_profit_price,
                error=result.get("error") or result.get("msg")
            )

        # Extract order IDs from response
        orders = result.get("orders", [])
        sl_order_id = None
        tp_order_id = None
        for order in orders:
            if order.get("type") == "STOP_LOSS_LIMIT":
                sl_order_id = str(order.get("orderId"))
            elif order.get("type") == "LIMIT_MAKER":
                tp_order_id = str(order.get("orderId"))

        return OCOResult(
            success=True,
            order_list_id=str(result.get("orderListId")),
            stop_loss_order_id=sl_order_id,
            take_profit_order_id=tp_order_id,
            stop_price=stop_price,
            limit_price=take_profit_price
        )

    def cancel_oco_order(self, symbol: str, order_list_id: str) -> bool:
        """Cancel OCO order"""
        params = {
            "symbol": symbol,
            "orderListId": order_list_id
        }

        result = self._request("DELETE", "/api/v3/orderList", params, signed=True)
        return "error" not in result and "code" not in result

    def get_open_orders(self, symbol: str = None) -> list:
        """Get all open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol

        result = self._request("GET", "/api/v3/openOrders", params, signed=True)

        if "error" in result:
            return []
        return result if isinstance(result, list) else []

    def get_position(self, symbol: str = "BTCUSDT") -> dict:
        """Get current position (BTC balance)

        CRITICAL: Used for position sync on restart
        """
        balance = self.get_balance()
        btc_asset = symbol.replace("USDT", "")

        btc_qty = balance.get(btc_asset, 0)
        usdt_qty = balance.get("USDT", 0)

        return {
            "symbol": symbol,
            "btc_quantity": btc_qty,
            "usdt_balance": usdt_qty,
            "has_position": btc_qty > 0.0001  # Min meaningful position
        }


class TradeExecutor:
    """Unified trade executor"""

    def __init__(self, mode: str = "paper", api_key: str = "", api_secret: str = "",
                 initial_balance: float = 10000.0, testnet: bool = False):
        self.mode = mode

        if mode == "paper":
            self.trader = PaperTrader(initial_balance)
        else:
            self.trader = LiveTrader(api_key, api_secret, testnet)

    def get_balance(self) -> dict:
        return self.trader.get_balance()

    def buy(self, price: float = None, usdt_amount: float = None, symbol: str = "BTCUSDT") -> TradeResult:
        if self.mode == "paper":
            return self.trader.buy(price, usdt_amount)
        else:
            return self.trader.buy(symbol, usdt_amount)

    def sell(self, price: float = None, btc_quantity: float = None, symbol: str = "BTCUSDT") -> TradeResult:
        if self.mode == "paper":
            return self.trader.sell(price, btc_quantity)
        else:
            return self.trader.sell(symbol, btc_quantity)

    def create_oco_order(self, symbol: str, quantity: float, entry_price: float,
                         stop_loss_pct: float, take_profit_pct: float) -> OCOResult:
        """Create OCO order for SL/TP on server side"""
        return self.trader.create_oco_order(symbol, quantity, entry_price, stop_loss_pct, take_profit_pct)

    def cancel_oco_order(self, symbol: str, order_list_id: str) -> bool:
        """Cancel OCO order"""
        return self.trader.cancel_oco_order(symbol, order_list_id)

    def get_position(self, symbol: str = "BTCUSDT") -> dict:
        """Get current position for sync"""
        return self.trader.get_position(symbol)

    def check_oco_triggered(self, current_price: float) -> Optional[str]:
        """Check if OCO triggered (paper mode only)"""
        if self.mode == "paper" and hasattr(self.trader, 'check_oco_triggered'):
            return self.trader.check_oco_triggered(current_price)
        return None
