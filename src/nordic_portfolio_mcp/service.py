"""Application service shared by MCP tools and offline tests."""

from __future__ import annotations

from datetime import date
from typing import Any

from .gateway import ReadOnlyAvanzaGateway
from .normalize import normalize_overview, normalize_portfolio, normalize_transactions
from .rebalance import calculate_rebalance


class PortfolioService:
    def __init__(self, gateway: ReadOnlyAvanzaGateway | None = None) -> None:
        self._gateway = gateway or ReadOnlyAvanzaGateway()

    def connection_status(self) -> dict[str, Any]:
        return normalize_overview(self._gateway.overview())

    def portfolio(self) -> dict[str, Any]:
        return normalize_portfolio(self._gateway.positions())

    def transactions(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
        max_elements: int,
    ) -> dict[str, Any]:
        return normalize_transactions(
            self._gateway.transactions(
                transactions_from=date_from,
                transactions_to=date_to,
                max_elements=max_elements,
            )
        )

    def rebalance(
        self,
        *,
        targets: list[dict[str, Any]],
        market_quotes: list[dict[str, Any]],
        cash_buffer: float,
        minimum_trade_value: float,
        maximum_turnover_fraction: float,
        liquidate_non_targets: bool,
    ) -> dict[str, Any]:
        return calculate_rebalance(
            self.portfolio(),
            targets,
            market_quotes,
            cash_buffer=cash_buffer,
            minimum_trade_value=minimum_trade_value,
            maximum_turnover_fraction=maximum_turnover_fraction,
            liquidate_non_targets=liquidate_non_targets,
        )
