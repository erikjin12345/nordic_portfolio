from nordic_portfolio_mcp.normalize import (
    normalize_overview,
    normalize_portfolio,
    normalize_transactions,
)


def test_normalize_portfolio_redacts_private_ids() -> None:
    payload = {
        "withOrderbook": [
            {
                "account": {
                    "id": "PRIVATE-ACCOUNT-ID",
                    "urlParameterId": "PRIVATE-URL-ID",
                    "name": "ISK",
                    "type": "INVESTMENT_SAVINGS_ACCOUNT",
                },
                "instrument": {
                    "type": "STOCK",
                    "name": "Example AB",
                    "currency": "USD",
                    "isin": "SE0000000001",
                    "volumeFactor": 1,
                    "orderbook": {
                        "id": "12345",
                        "quote": {"latest": {"value": 100}},
                    },
                },
                "volume": {"value": 10},
                "value": {"value": 1000, "unit": "SEK"},
                "averageAcquiredPrice": {"value": 80},
                "acquiredValue": {"value": 800},
            }
        ],
        "withoutOrderbook": [],
        "cashPositions": [
            {
                "id": "PRIVATE-CASH-ID",
                "account": {
                    "id": "PRIVATE-ACCOUNT-ID",
                    "urlParameterId": "PRIVATE-URL-ID",
                    "name": "ISK",
                    "type": "INVESTMENT_SAVINGS_ACCOUNT",
                },
                "totalBalance": {"value": 500, "unit": "SEK"},
            }
        ],
    }

    result = normalize_portfolio(payload)
    serialized = repr(result)

    assert "PRIVATE-ACCOUNT-ID" not in serialized
    assert "PRIVATE-URL-ID" not in serialized
    assert "PRIVATE-CASH-ID" not in serialized
    assert result["positions"][0]["instrument_id"] == "12345"
    assert result["positions"][0]["market_value"] == 1000
    assert result["positions"][0]["currency"] == "SEK"
    assert result["positions"][0]["quote_currency"] == "USD"
    assert result["cash"][0]["account_ref"].startswith("acct_")
    assert result["unconverted_total"] == 1500


def test_normalize_overview_returns_only_safe_account_metadata() -> None:
    result = normalize_overview(
        {
            "accounts": [
                {
                    "id": "PRIVATE-ID",
                    "urlParameterId": "PRIVATE-URL",
                    "name": {"defaultName": "ISK", "userDefinedName": "Långsiktigt"},
                    "type": "ISK",
                    "status": "OPEN",
                    "owner": True,
                }
            ]
        }
    )

    assert result["connected"] is True
    assert result["account_count"] == 1
    assert "PRIVATE-ID" not in repr(result)
    assert result["accounts"][0]["name"] == "Långsiktigt"


def test_normalize_transactions_removes_transaction_and_note_ids() -> None:
    result = normalize_transactions(
        {
            "transactions": [
                {
                    "id": "PRIVATE-TX",
                    "noteId": "PRIVATE-NOTE",
                    "date": "2026-07-01T12:00:00",
                    "tradeDate": "2026-07-01",
                    "settlementDate": "2026-07-03",
                    "account": {"id": "PRIVATE-ACCOUNT", "name": "ISK"},
                    "orderbook": {
                        "id": "12345",
                        "name": "Example AB",
                        "isin": "SE0000000001",
                        "currency": "SEK",
                    },
                    "type": "BUY",
                    "description": "Köp",
                    "volume": {"value": 2},
                    "priceInTradedCurrency": {"value": 100},
                    "amount": {"value": -200},
                    "commission": {"value": 1},
                    "isin": "SE0000000001",
                }
            ]
        }
    )

    serialized = repr(result)
    assert "PRIVATE-TX" not in serialized
    assert "PRIVATE-NOTE" not in serialized
    assert "PRIVATE-ACCOUNT" not in serialized
    assert result["transactions"][0]["instrument_id"] == "12345"
