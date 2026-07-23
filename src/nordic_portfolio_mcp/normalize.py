"""Normalize private Avanza responses and remove account-level identifiers."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


def _number(container: Mapping[str, Any] | None, key: str = "value") -> float:
    if not container:
        return 0.0
    value = container.get(key, 0.0)
    return float(value) if isinstance(value, int | float) else 0.0


def _account_ref(account: Mapping[str, Any] | None) -> str:
    account = account or {}
    private_id = str(account.get("id") or account.get("urlParameterId") or "unknown")
    digest = hashlib.sha256(private_id.encode("utf-8")).hexdigest()[:12]
    return f"acct_{digest}"


def _position_rows(payload: Mapping[str, Any]) -> Iterable[tuple[Mapping[str, Any], str]]:
    for key, source in (("withOrderbook", "avanza_quote"), ("withoutOrderbook", "avanza_value")):
        for row in payload.get(key, []) or []:
            if isinstance(row, Mapping):
                yield row, source


def normalize_portfolio(payload: Mapping[str, Any]) -> dict[str, Any]:
    positions: list[dict[str, Any]] = []
    totals_by_currency: defaultdict[str, float] = defaultdict(float)

    for row, value_source in _position_rows(payload):
        account = row.get("account") if isinstance(row.get("account"), Mapping) else {}
        instrument = row.get("instrument") if isinstance(row.get("instrument"), Mapping) else {}
        orderbook = (
            instrument.get("orderbook") if isinstance(instrument.get("orderbook"), Mapping) else {}
        )
        value_data = row.get("value") if isinstance(row.get("value"), Mapping) else {}
        value_currency = str(value_data.get("unit") or "SEK")
        quote_currency = str(instrument.get("currency") or value_currency)
        market_value = _number(row.get("value"))
        totals_by_currency[value_currency] += market_value
        quote = orderbook.get("quote") if isinstance(orderbook.get("quote"), Mapping) else {}

        positions.append(
            {
                "account_ref": _account_ref(account),
                "account_name": account.get("name"),
                "account_type": account.get("type"),
                "instrument_id": str(orderbook.get("id")) if orderbook.get("id") else None,
                "isin": instrument.get("isin"),
                "name": instrument.get("name"),
                "instrument_type": instrument.get("type"),
                "currency": value_currency,
                "quote_currency": quote_currency,
                "volume": _number(row.get("volume")),
                "volume_factor": float(instrument.get("volumeFactor") or 1.0),
                "market_value": market_value,
                "average_acquired_price": _number(row.get("averageAcquiredPrice")),
                "acquired_value": _number(row.get("acquiredValue")),
                "latest_price": _number(quote.get("latest")) if quote else None,
                "value_source": value_source,
            }
        )

    cash: list[dict[str, Any]] = []
    for row in payload.get("cashPositions", []) or []:
        if not isinstance(row, Mapping):
            continue
        account = row.get("account") if isinstance(row.get("account"), Mapping) else {}
        balance = row.get("totalBalance") if isinstance(row.get("totalBalance"), Mapping) else {}
        currency = str(balance.get("unit") or "SEK")
        value = _number(balance)
        totals_by_currency[currency] += value
        cash.append(
            {
                "account_ref": _account_ref(account),
                "account_name": account.get("name"),
                "account_type": account.get("type"),
                "currency": currency,
                "value": value,
            }
        )

    base_total = sum(totals_by_currency.values())
    for position in positions:
        position["portfolio_weight_unconverted"] = (
            position["market_value"] / base_total if base_total else 0.0
        )

    return {
        "read_only": True,
        "positions": positions,
        "cash": cash,
        "totals_by_currency": dict(sorted(totals_by_currency.items())),
        "unconverted_total": base_total,
        "warnings": [
            "Values in different currencies are not FX-normalized in unconverted_total.",
            "No trade, transfer, or savings action is available through this MCP server.",
        ],
    }


def normalize_overview(payload: Mapping[str, Any]) -> dict[str, Any]:
    accounts = []
    for account in payload.get("accounts", []) or []:
        if not isinstance(account, Mapping):
            continue
        name = account.get("name") if isinstance(account.get("name"), Mapping) else {}
        accounts.append(
            {
                "account_ref": _account_ref(account),
                "name": name.get("userDefinedName") or name.get("defaultName"),
                "type": account.get("type"),
                "status": account.get("status"),
                "owner": account.get("owner"),
            }
        )
    return {"connected": True, "account_count": len(accounts), "accounts": accounts}


def normalize_transactions(payload: Mapping[str, Any]) -> dict[str, Any]:
    transactions = []
    for row in payload.get("transactions", []) or []:
        if not isinstance(row, Mapping):
            continue
        account = row.get("account") if isinstance(row.get("account"), Mapping) else {}
        orderbook = row.get("orderbook") if isinstance(row.get("orderbook"), Mapping) else {}
        transactions.append(
            {
                "date": row.get("date"),
                "trade_date": row.get("tradeDate"),
                "settlement_date": row.get("settlementDate"),
                "account_ref": _account_ref(account),
                "account_name": account.get("name"),
                "type": row.get("type"),
                "description": row.get("description"),
                "instrument_id": str(orderbook.get("id")) if orderbook.get("id") else None,
                "instrument_name": row.get("instrumentName") or orderbook.get("name"),
                "isin": row.get("isin") or orderbook.get("isin"),
                "currency": orderbook.get("currency"),
                "volume": _number(row.get("volume")) if row.get("volume") else None,
                "price": (
                    _number(row.get("priceInTradedCurrency"))
                    if row.get("priceInTradedCurrency")
                    else None
                ),
                "amount": _number(row.get("amount")) if row.get("amount") else None,
                "commission": _number(row.get("commission")) if row.get("commission") else None,
            }
        )
    return {
        "read_only": True,
        "count": len(transactions),
        "transactions": transactions,
    }
