from __future__ import annotations

import os

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

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

    def get_trade_history(self, limit: int = 20) -> list[TradeHistoryEntry]:
        orders = self.client.get_orders()
        return [
            TradeHistoryEntry(
                symbol=order.symbol,
                qty=float(order.qty) if order.qty else 0,
                side=str(order.side),
                status=str(order.status),
                filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else 0,
            )
            for order in list(orders)[:limit]
        ]
