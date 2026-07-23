"""Domain-specific errors that are safe to return through MCP."""


class ConfigurationError(RuntimeError):
    """Raised when local credentials have not been configured."""


class AvanzaConnectionError(RuntimeError):
    """Raised when authentication or an Avanza request fails."""


class RebalanceInputError(ValueError):
    """Raised when a rebalance request is internally inconsistent."""
