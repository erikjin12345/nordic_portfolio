from typing import Any

from nordic_portfolio_mcp.credentials import AvanzaCredentials
from nordic_portfolio_mcp.gateway import ReadOnlyAvanzaGateway


class FakeStore:
    def load(self) -> AvanzaCredentials:
        return AvanzaCredentials("user", "password", "JBSWY3DPEHPK3PXP")


class FakeClient:
    def get_overview(self) -> dict[str, Any]:
        return {"accounts": []}

    def get_accounts_positions(self) -> dict[str, Any]:
        return {"withOrderbook": [], "withoutOrderbook": [], "cashPositions": []}

    def get_transactions_details(self, **_: Any) -> dict[str, Any]:
        return {"transactions": []}


def test_gateway_only_exposes_read_operations() -> None:
    gateway = ReadOnlyAvanzaGateway(FakeStore(), lambda _: FakeClient())

    assert gateway.overview() == {"accounts": []}
    assert gateway.positions()["withOrderbook"] == []
    assert gateway.transactions(
        transactions_from=None,
        transactions_to=None,
        max_elements=10,
    ) == {"transactions": []}
    assert not hasattr(gateway, "place_order")
    assert not hasattr(gateway, "delete_order")
