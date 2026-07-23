import pytest

from nordic_portfolio_mcp.errors import RebalanceInputError
from nordic_portfolio_mcp.rebalance import calculate_rebalance

PORTFOLIO = {
    "positions": [
        {
            "instrument_id": "A",
            "isin": "SE0000000001",
            "name": "Alpha",
            "currency": "SEK",
            "volume": 10,
            "volume_factor": 1,
            "market_value": 1000,
        },
        {
            "instrument_id": "B",
            "isin": "SE0000000002",
            "name": "Beta",
            "currency": "SEK",
            "volume": 20,
            "volume_factor": 1,
            "market_value": 1000,
        },
    ],
    "cash": [{"currency": "SEK", "value": 1000}],
}


def test_rebalance_uses_external_quotes_and_never_enables_execution() -> None:
    result = calculate_rebalance(
        PORTFOLIO,
        [
            {"instrument_id": "A", "target_weight": 0.5},
            {"instrument_id": "B", "target_weight": 0.5},
        ],
        [
            {"instrument_id": "A", "price": 100, "fx_rate_to_base": 1},
            {"instrument_id": "B", "price": 50, "fx_rate_to_base": 1},
        ],
        minimum_trade_value=1,
    )

    assert result["execution_enabled"] is False
    assert result["investable_value"] == 3000
    assert {row["action"] for row in result["proposals"]} == {"BUY"}
    assert sum(row["delta_value"] for row in result["proposals"]) == pytest.approx(1000)
    assert all(row["value_source"] == "external_market_quote" for row in result["proposals"])


def test_rebalance_leaves_non_targets_untouched_by_default() -> None:
    result = calculate_rebalance(
        PORTFOLIO,
        [{"instrument_id": "A", "target_weight": 1.0}],
        minimum_trade_value=1,
    )

    assert result["investable_value"] == 2000
    assert all(row["instrument_id"] != "B" for row in result["proposals"])


def test_rebalance_can_propose_liquidating_non_targets() -> None:
    result = calculate_rebalance(
        PORTFOLIO,
        [{"instrument_id": "A", "target_weight": 1.0}],
        minimum_trade_value=1,
        liquidate_non_targets=True,
    )

    beta = next(row for row in result["proposals"] if row["instrument_id"] == "B")
    assert beta["action"] == "SELL"
    assert beta["delta_value"] == -1000


def test_rebalance_rejects_invalid_target_sum() -> None:
    with pytest.raises(RebalanceInputError, match="sum to 1.0"):
        calculate_rebalance(
            PORTFOLIO,
            [{"instrument_id": "A", "target_weight": 0.8}],
        )


def test_rebalance_matches_isin_target_and_prices_new_position() -> None:
    result = calculate_rebalance(
        PORTFOLIO,
        [
            {"isin": "SE0000000001", "target_weight": 0.5},
            {"instrument_id": "C", "target_weight": 0.5},
        ],
        [{"instrument_id": "C", "price": 25, "fx_rate_to_base": 1}],
        minimum_trade_value=1,
    )

    assert result["investable_value"] == 2000
    alpha = next(row for row in result["ignored"] if row["instrument_id"] == "A")
    new_position = next(row for row in result["proposals"] if row["instrument_id"] == "C")
    assert alpha["delta_value"] == 0
    assert new_position["estimated_units"] == 40
