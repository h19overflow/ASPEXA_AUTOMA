"""
Rate limiter using token bucket algorithm for RPS limiting.

Purpose: Control request rate to prevent overwhelming targets
Dependencies: asyncio
Used by: execution/scanner.py
"""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for async operations.

    Implements a token bucket algorithm where:
    - Tokens are added at a constant rate (requests_per_second)
    - Each request consumes one token
    - If no tokens are available, the request waits
    - Burst capacity allows short bursts above the rate limit
    """

    def __init__(
        self,
        requests_per_second: float,
        burst_capacity: Optional[int] = None
    ):
        """Initialize rate limiter.

        Args:
            requests_per_second: Target rate in requests per second
            burst_capacity: Maximum burst size (defaults to requests_per_second)
        """
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be > 0")

        self.requests_per_second = requests_per_second
        self.burst_capacity = burst_capacity or int(requests_per_second)
        self.tokens = float(self.burst_capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

        logger.debug(
            f"RateLimiter initialized: {requests_per_second} RPS, "
            f"burst capacity: {self.burst_capacity}"
        )

    async def acquire(self) -> None:
        """Acquire a token, blocking if necessary until one is available.

        This method should be called before making a request to ensure
        rate limiting is enforced.
        """
        async with self._lock:
            # Update token count based on elapsed time
            now = time.monotonic()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time (at the specified rate)
            tokens_to_add = elapsed * self.requests_per_second
            self.tokens = min(self.burst_capacity, self.tokens + tokens_to_add)
            self.last_update = now

            # If we have tokens, consume one and proceed
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return

            # Calculate wait time needed to get a token
            tokens_needed = 1.0 - self.tokens
            wait_time = tokens_needed / self.requests_per_second

            # Update tokens to 0 (we'll wait for the needed amount)
            self.tokens = 0.0

        # Wait outside the lock to allow other coroutines to proceed
        await asyncio.sleep(wait_time)

        # Update last_update after waiting
        async with self._lock:
            self.last_update = time.monotonic()
            # After waiting, we should have exactly 1 token
            self.tokens = 0.0

    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        return {
            "requests_per_second": self.requests_per_second,
            "burst_capacity": self.burst_capacity,
            "current_tokens": self.tokens,
        }
