"""Credential storage backed exclusively by the operating-system keyring."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol

import keyring

from .errors import ConfigurationError

KEYRING_SERVICE = "com.erikjin.nordic-portfolio.avanza"
_USERNAME_KEY = "username"
_PASSWORD_KEY = "password"
_TOTP_SECRET_KEY = "totp-secret"


@dataclass(frozen=True, slots=True)
class AvanzaCredentials:
    username: str
    password: str
    totp_secret: str

    def as_avanza_dict(self) -> dict[str, str]:
        return {
            "username": self.username,
            "password": self.password,
            "totpSecret": self.totp_secret,
        }


class CredentialStore(Protocol):
    def load(self) -> AvanzaCredentials: ...


class KeyringCredentialStore:
    """Load private Avanza credentials without environment variables or files."""

    def __init__(self, service: str = KEYRING_SERVICE) -> None:
        self._service = service

    def load(self) -> AvanzaCredentials:
        values = {
            "username": keyring.get_password(self._service, _USERNAME_KEY),
            "password": keyring.get_password(self._service, _PASSWORD_KEY),
            "totp_secret": keyring.get_password(self._service, _TOTP_SECRET_KEY),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ConfigurationError(
                "Avanza credentials are missing from the system keyring. "
                "Run `uv run nordic-avanza-configure` locally."
            )
        return AvanzaCredentials(**values)  # type: ignore[arg-type]

    def save(self, credentials: AvanzaCredentials) -> None:
        keyring.set_password(self._service, _USERNAME_KEY, credentials.username)
        keyring.set_password(self._service, _PASSWORD_KEY, credentials.password)
        keyring.set_password(self._service, _TOTP_SECRET_KEY, credentials.totp_secret)

    def delete(self) -> None:
        for key in (_USERNAME_KEY, _PASSWORD_KEY, _TOTP_SECRET_KEY):
            with suppress(keyring.errors.PasswordDeleteError):
                keyring.delete_password(self._service, key)
