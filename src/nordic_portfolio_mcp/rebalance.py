"""Pure calculation engine for non-executable portfolio rebalance proposals."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import RebalanceInputError


def _key(item: Mapping[str, Any]) -> str:
    identifiers = _identifiers(item)
    if identifiers:
        return identifiers[0]
    raise RebalanceInputError("Each target and position needs instrument_id or isin.")


def _identifiers(item: Mapping[str, Any]) -> list[str]:
    identifiers = []
    if item.get("instrument_id"):
        identifiers.append(f"id:{item['instrument_id']}")
    if item.get("isin"):
        identifiers.append(f"isin:{str(item['isin']).upper()}")
    return identifiers


def _validate_targets(targets: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    if not targets:
        raise RebalanceInputError("At least one target is required.")
    validated: dict[str, dict[str, Any]] = {}
    seen_identifiers: set[str] = set()
    total_weight = 0.0
    for target in targets:
        key = _key(target)
        identifiers = set(_identifiers(target))
        duplicates = identifiers & seen_identifiers
        if duplicates:
            raise RebalanceInputError(f"Duplicate target identifiers: {sorted(duplicates)}.")
        weight = float(target.get("target_weight", -1))
        if not 0 <= weight <= 1:
            raise RebalanceInputError(f"target_weight for {key} must be between 0 and 1.")
        total_weight += weight
        validated[key] = {**target, "target_weight": weight}
        seen_identifiers |= identifiers
    if not math.isclose(total_weight, 1.0, abs_tol=0.0001):
        raise RebalanceInputError(f"Target weights must sum to 1.0; received {total_weight:.6f}.")
    return validated


def _quote_map(quotes: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    mapped: dict[str, Mapping[str, Any]] = {}
    for quote in quotes:
        key = _key(quote)
        price = float(quote.get("price", 0))
        fx_rate = float(quote.get("fx_rate_to_base", 1))
        if price <= 0 or fx_rate <= 0:
            raise RebalanceInputError(f"Price and fx_rate_to_base must be positive for {key}.")
        for identifier in _identifiers(quote):
            mapped[identifier] = quote
    return mapped


def calculate_rebalance(
    portfolio: Mapping[str, Any],
    targets: Sequence[Mapping[str, Any]],
    market_quotes: Sequence[Mapping[str, Any]] = (),
    *,
    cash_buffer: float = 0.0,
    minimum_trade_value: float = 500.0,
    maximum_turnover_fraction: float = 1.0,
    liquidate_non_targets: bool = False,
) -> dict[str, Any]:
    """Calculate an indicative plan; this function never places an order."""
    if cash_buffer < 0 or minimum_trade_value < 0:
        raise RebalanceInputError("cash_buffer and minimum_trade_value cannot be negative.")
    if not 0 < maximum_turnover_fraction <= 1:
        raise RebalanceInputError("maximum_turnover_fraction must be in (0, 1].")

    target_map = _validate_targets(targets)
    quotes = _quote_map(market_quotes)
    aggregate: dict[str, dict[str, Any]] = {}
    holding_aliases: dict[str, str] = {}

    for position in portfolio.get("positions", []) or []:
        key = _key(position)
        existing = aggregate.setdefault(
            key,
            {
                "instrument_id": position.get("instrument_id"),
                "isin": position.get("isin"),
                "name": position.get("name"),
                "currency": position.get("currency"),
                "quote_currency": position.get("quote_currency"),
                "volume": 0.0,
                "portfolio_market_value": 0.0,
                "volume_factor": float(position.get("volume_factor") or 1.0),
            },
        )
        existing["volume"] += float(position.get("volume") or 0.0)
        existing["portfolio_market_value"] += float(position.get("market_value") or 0.0)
        for identifier in _identifiers(position):
            holding_aliases[identifier] = key

    remapped_targets: dict[str, dict[str, Any]] = {}
    for target_key, target in target_map.items():
        canonical_key = next(
            (
                holding_aliases[identifier]
                for identifier in _identifiers(target)
                if identifier in holding_aliases
            ),
            target_key,
        )
        if canonical_key in remapped_targets:
            raise RebalanceInputError(
                f"Multiple targets resolve to the same holding: {canonical_key}."
            )
        remapped_targets[canonical_key] = target
    target_map = remapped_targets

    cash_by_currency: defaultdict[str, float] = defaultdict(float)
    for cash in portfolio.get("cash", []) or []:
        cash_by_currency[str(cash.get("currency") or "SEK")] += float(cash.get("value") or 0.0)
    cash_total = sum(cash_by_currency.values())

    for holding in aggregate.values():
        quote = next(
            (quotes[identifier] for identifier in _identifiers(holding) if identifier in quotes),
            None,
        )
        if quote:
            holding["current_value"] = (
                holding["volume"]
                * float(quote["price"])
                * float(quote.get("fx_rate_to_base", 1))
                * holding["volume_factor"]
            )
            holding["price"] = float(quote["price"])
            holding["fx_rate_to_base"] = float(quote.get("fx_rate_to_base", 1))
            holding["as_of"] = quote.get("as_of")
            holding["value_source"] = "external_market_quote"
        else:
            holding["current_value"] = holding["portfolio_market_value"]
            holding["price"] = None
            holding["fx_rate_to_base"] = None
            holding["as_of"] = None
            holding["value_source"] = "avanza_portfolio_value"

    managed_keys = set(target_map)
    if liquidate_non_targets:
        managed_keys |= set(aggregate)

    managed_holdings_value = sum(
        aggregate.get(key, {}).get("current_value", 0.0) for key in managed_keys
    )
    investable_value = managed_holdings_value + cash_total - cash_buffer
    if investable_value <= 0:
        raise RebalanceInputError(
            "Managed holdings plus cash must exceed the requested cash buffer."
        )

    rows: list[dict[str, Any]] = []
    for key in sorted(managed_keys):
        holding = aggregate.get(key, {})
        target = target_map.get(key)
        target_weight = float(target["target_weight"]) if target else 0.0
        current_value = float(holding.get("current_value") or 0.0)
        target_value = investable_value * target_weight
        delta = target_value - current_value
        identity = {**holding, **(target or {})}
        quote = next(
            (quotes[identifier] for identifier in _identifiers(identity) if identifier in quotes),
            None,
        )
        price = holding.get("price")
        fx_rate = holding.get("fx_rate_to_base")
        quote_as_of = holding.get("as_of")
        value_source = holding.get("value_source", "not_held")
        if not holding and quote:
            price = float(quote["price"])
            fx_rate = float(quote.get("fx_rate_to_base", 1))
            quote_as_of = quote.get("as_of")
            value_source = "external_market_quote"
        rows.append(
            {
                "key": key,
                "instrument_id": identity.get("instrument_id"),
                "isin": identity.get("isin"),
                "name": identity.get("name") or holding.get("name"),
                "current_value": current_value,
                "current_weight": current_value / investable_value,
                "target_weight": target_weight,
                "target_value": target_value,
                "raw_delta_value": delta,
                "price": price,
                "fx_rate_to_base": fx_rate,
                "quote_as_of": quote_as_of,
                "value_source": value_source,
                "current_volume": holding.get("volume", 0.0),
                "volume_factor": holding.get("volume_factor", 1.0),
            }
        )

    raw_turnover = sum(abs(row["raw_delta_value"]) for row in rows) / 2
    turnover_cap = investable_value * maximum_turnover_fraction
    scale = min(1.0, turnover_cap / raw_turnover) if raw_turnover else 1.0

    proposals = []
    ignored = []
    for row in rows:
        delta = row.pop("raw_delta_value") * scale
        if abs(delta) < minimum_trade_value:
            ignored.append(
                {
                    **row,
                    "delta_value": delta,
                    "reason": "below_minimum_trade_value",
                }
            )
            continue
        price = row.get("price")
        fx_rate = row.get("fx_rate_to_base")
        factor = float(row.get("volume_factor") or 1.0)
        estimated_units = None
        if price and fx_rate and factor:
            estimated_units = delta / (float(price) * float(fx_rate) * factor)
        proposals.append(
            {
                **row,
                "action": "BUY" if delta > 0 else "SELL",
                "delta_value": delta,
                "estimated_units": estimated_units,
            }
        )

    return {
        "execution_enabled": False,
        "base_currency_assumption": (
            "All supplied values and FX-converted quotes share one base currency."
        ),
        "investable_value": investable_value,
        "cash_total_unconverted": cash_total,
        "cash_by_currency": dict(sorted(cash_by_currency.items())),
        "cash_buffer": cash_buffer,
        "raw_turnover": raw_turnover,
        "turnover_cap": turnover_cap,
        "turnover_scale_applied": scale,
        "proposals": proposals,
        "ignored": ignored,
        "warnings": [
            "Indicative analysis only; no orders were or can be placed.",
            "Review FX rates, prices, spread, fees, taxes, liquidity, and instrument rules.",
            "Cash values in multiple currencies require external FX conversion before use.",
        ],
    }
