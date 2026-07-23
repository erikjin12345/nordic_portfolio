"""Minimal local connectivity check with no private values in stdout."""

from __future__ import annotations

from .service import PortfolioService


def main() -> None:
    status = PortfolioService().connection_status()
    print(f"Connected to Avanza. Read-only accounts available: {status['account_count']}.")


if __name__ == "__main__":
    main()
