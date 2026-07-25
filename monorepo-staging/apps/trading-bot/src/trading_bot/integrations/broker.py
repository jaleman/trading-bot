from __future__ import annotations

import os

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest

from trading_bot.models import AccountSnapshot, OrderResult, PositionSnapshot, TradeHistoryEntry


class BrokerError(RuntimeError):
    """Raised when broker credentials or broker calls fail."""


class AlpacaBrokerClient:
    """Monorepo-native Alpaca broker adapter for paper trading."""

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        *,
        paper: bool = True,
    ) -> None:
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.paper = paper

        if not self.api_key or not self.secret_key:
            raise BrokerError(
                "Missing Alpaca broker credentials. Set ALPACA_API_KEY and ALPACA_SECRET_KEY."
            )

        self.client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper,
        )

    def get_account_balance(self) -> AccountSnapshot:
        account = self.client.get_account()
        return AccountSnapshot(
            cash=float(account.cash),
            portfolio_value=float(account.portfolio_value),
            buying_power=float(account.buying_power),
        )

    def get_open_positions(self) -> list[PositionSnapshot]:
        positions = self.client.get_all_positions()
        return [
            PositionSnapshot(
                symbol=position.symbol,
                qty=float(position.qty),
                avg_entry_price=float(position.avg_entry_price),
                current_price=float(position.current_price),
                unrealized_pl=float(position.unrealized_pl),
                unrealized_plpc=float(position.unrealized_plpc),
            )
            for position in positions
        ]

    def get_open_orders(self, limit: int = 20) -> list[OrderResult]:
        orders = self.client.get_orders(
            GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=limit)
        )
        return [
            OrderResult(
                id=str(order.id),
                symbol=order.symbol,
                qty=float(order.qty) if order.qty else 0,
                side=str(order.side),
                status=str(order.status),
            )
            for order in orders
        ]

    def get_asset_name(self, symbol: str) -> str | None:
        asset = self.client.get_asset(symbol)
        if not asset.name:
            return None

        return asset.name.strip() or None

    def place_paper_trade(self, symbol: str, qty: int, side: str) -> OrderResult:
        order = self.client.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
        )

        return OrderResult(
            id=str(order.id),
            symbol=order.symbol,
            qty=float(order.qty),
            side=str(order.side),
            status=str(order.status),
        )

    def get_trade_history(self, limit: int = 100) -> list[TradeHistoryEntry]:
        """Return order history, most recently filled first.

        Alpaca's `get_orders()` defaults to *open* orders only. Without an
        explicit status filter this returned nothing at all once orders had
        filled and closed, which is every order that ever mattered.
        """
        request = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
        orders = list(self.client.get_orders(filter=request))

        entries = [
            TradeHistoryEntry(
                symbol=order.symbol,
                qty=float(order.qty) if order.qty else 0,
                side=str(order.side).split(".")[-1],
                status=str(order.status).split(".")[-1],
                filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else 0,
                id=str(order.id),
                filled_qty=float(order.filled_qty) if order.filled_qty else 0,
                submitted_at=str(order.submitted_at) if order.submitted_at else "",
                filled_at=str(order.filled_at) if order.filled_at else "",
            )
            for order in orders
        ]
        entries.sort(key=lambda e: e.filled_at or e.submitted_at, reverse=True)
        return entries[:limit]
