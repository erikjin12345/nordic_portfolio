"""Strict read-only boundary around the unofficial Avanza client."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, Protocol

import requests
from avanza import Avanza

from .credentials import CredentialStore, KeyringCredentialStore
from .errors import AvanzaConnectionError


class AvanzaReadClient(Protocol):
    def get_overview(self) -> dict[str, Any]: ...

    def get_accounts_positions(self) -> dict[str, Any]: ...

    def get_transactions_details(
        self,
        *,
        transactions_from: date | None,
        transactions_to: date | None,
        max_elements: int,
    ) -> dict[str, Any]: ...


class ReadOnlyAvanzaGateway:
    """Allow-list only the private read calls required by this MCP server."""

    def __init__(
        self,
        credential_store: CredentialStore | None = None,
        client_factory: Callable[[dict[str, str]], AvanzaReadClient] | None = None,
    ) -> None:
        self._credential_store = credential_store or KeyringCredentialStore()
        self._client_factory = client_factory or self._default_client_factory
        self._client: AvanzaReadClient | None = None

    @staticmethod
    def _default_client_factory(credentials: dict[str, str]) -> AvanzaReadClient:
        return Avanza(credentials, quiet=True)

    def _get_client(self) -> AvanzaReadClient:
        if self._client is None:
            credentials = self._credential_store.load()
            try:
                self._client = self._client_factory(credentials.as_avanza_dict())
            except (requests.RequestException, KeyError, ValueError) as exc:
                raise AvanzaConnectionError(
                    "Could not authenticate with Avanza. Verify the local credentials and "
                    "TOTP setup, then try again."
                ) from exc
        return self._client

    @staticmethod
    def _call(operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            return operation()
        except requests.RequestException as exc:
            raise AvanzaConnectionError(
                "The read-only request to Avanza failed. The unofficial endpoint may have changed "
                "or the session may have expired."
            ) from exc

    def overview(self) -> dict[str, Any]:
        client = self._get_client()
        return self._call(client.get_overview)

    def positions(self) -> dict[str, Any]:
        client = self._get_client()
        return self._call(client.get_accounts_positions)

    def transactions(
        self,
        *,
        transactions_from: date | None,
        transactions_to: date | None,
        max_elements: int,
    ) -> dict[str, Any]:
        client = self._get_client()
        return self._call(
            lambda: client.get_transactions_details(
                transactions_from=transactions_from,
                transactions_to=transactions_to,
                max_elements=max_elements,
            )
        )
