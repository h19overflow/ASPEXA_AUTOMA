"""
HTTP generator for Garak scanner.

DEPRECATED: Use libs.connectivity.adapters.GarakHttpGenerator directly.
This module exists for backwards compatibility only.

Sends probe prompts to an HTTP endpoint and collects responses.
"""
from libs.connectivity.adapters import GarakHttpGenerator
from libs.connectivity.contracts import ConnectivityError

# Re-export for backwards compatibility
HttpGenerator = GarakHttpGenerator


class HttpGeneratorError(ConnectivityError):
    """Raised when HTTP generator encounters an error.

    DEPRECATED: Use libs.connectivity.ConnectivityError instead.
    """

    pass


__all__ = ["HttpGenerator", "HttpGeneratorError"]
