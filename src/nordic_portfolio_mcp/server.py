"""MCP server exposing only private read and analytical portfolio tools."""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from .service import PortfolioService

mcp = FastMCP(
    "Nordic Portfolio – private Avanza (read only)",
    json_response=True,
)
service = PortfolioService()


def _date_or_none(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


@mcp.tool()
def avanza_private_connection_status() -> dict[str, Any]:
    """Verify private Avanza access without returning balances or private identifiers."""
    return service.connection_status()


@mcp.tool()
def get_private_portfolio() -> dict[str, Any]:
    """Read normalized holdings and cash; account identifiers are pseudonymized."""
    return service.portfolio()


@mcp.tool()
def get_private_transactions(
    date_from: str | None = None,
    date_to: str | None = None,
    max_elements: int = 100,
) -> dict[str, Any]:
    """Read sanitized transactions. Dates use YYYY-MM-DD and max_elements is capped at 1000."""
    if not 1 <= max_elements <= 1000:
        raise ValueError("max_elements must be between 1 and 1000.")
    parsed_from = _date_or_none(date_from)
    parsed_to = _date_or_none(date_to)
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise ValueError("date_from cannot be later than date_to.")
    return service.transactions(
        date_from=parsed_from,
        date_to=parsed_to,
        max_elements=max_elements,
    )


@mcp.tool()
def calculate_portfolio_rebalance(
    targets: list[dict[str, Any]],
    market_quotes: list[dict[str, Any]] | None = None,
    cash_buffer: float = 0.0,
    minimum_trade_value: float = 500.0,
    maximum_turnover_fraction: float = 1.0,
    liquidate_non_targets: bool = False,
) -> dict[str, Any]:
    """Create a non-executable rebalance proposal from private holdings and market quotes.

    Target weights must sum to 1.0. Each target and quote uses instrument_id or ISIN.
    A quote contains price, optional fx_rate_to_base (default 1), and optional as_of.
    The result never places orders. Non-target holdings are untouched unless explicitly
    included with liquidate_non_targets=true.
    """
    return service.rebalance(
        targets=targets,
        market_quotes=market_quotes or [],
        cash_buffer=cash_buffer,
        minimum_trade_value=minimum_trade_value,
        maximum_turnover_fraction=maximum_turnover_fraction,
        liquidate_non_targets=liquidate_non_targets,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
