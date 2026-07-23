"""Interactive setup that writes Avanza credentials to the system keyring."""

from __future__ import annotations

import argparse
import base64
import binascii
import getpass

from .credentials import AvanzaCredentials, KeyringCredentialStore


def _normalize_totp_secret(value: str) -> str:
    normalized = "".join(value.split()).upper()
    if not normalized:
        raise ValueError("TOTP secret cannot be empty.")
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    try:
        base64.b32decode(normalized + padding, casefold=True)
    except binascii.Error as exc:
        raise ValueError("TOTP secret is not valid Base32.") from exc
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Store private Avanza credentials in the operating-system keyring."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the locally stored Avanza credentials.",
    )
    args = parser.parse_args()
    store = KeyringCredentialStore()
    if args.delete:
        store.delete()
        print("Stored Avanza credentials were removed from the system keyring.")
        return

    print("Credentials are stored only in the operating-system keyring.")
    print("Do not paste them into chat, source code, .env files, or Git.")
    username = input("Avanza username: ").strip()
    password = getpass.getpass("Avanza password: ")
    totp_secret = _normalize_totp_secret(getpass.getpass("Avanza TOTP secret: "))
    if not username or not password:
        raise SystemExit("Username and password cannot be empty.")
    store.save(
        AvanzaCredentials(
            username=username,
            password=password,
            totp_secret=totp_secret,
        )
    )
    print("Avanza credentials were stored in the system keyring.")


if __name__ == "__main__":
    main()
