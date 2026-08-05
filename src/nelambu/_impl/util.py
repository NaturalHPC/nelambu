import time

_DEFAULT_BASE_DELAY = 0.5
_DEFAULT_TIMEOUT = 30.0
_FACTOR = 2.0 ** (1.0 / 3.0)


class Retrier:
    """Helper class for retrying things with a delay and timeout.

    This backs off exponentially, immediately retrying on the first attempt, then
    waiting 2**tries * base_delay seconds between tries.
    """

    def __init__(
        self, timeout: float = _DEFAULT_TIMEOUT, base_delay: float = _DEFAULT_BASE_DELAY
    ) -> None:
        """Create a Retrier.

        Args:
            timeout: Timeout in seconds after which to give up
            base_delay: Base delay in seconds between retries
        """
        self._base_delay = base_delay
        self._factor = _FACTOR
        self._timeout = timeout

        self._tries = 0
        self._start = 0.0

    def sleep(self) -> None:
        """Sleep until it's time for the next retry."""
        if self._tries == 0:
            delay = 0.0
        else:
            delay = self._base_delay * self._factor ** (self._tries - 1)

        time.sleep(delay)
        self._tries += 1

    def should_give_up(self) -> bool:
        """Return whether to give up or retry."""
        if self._tries == 0:
            self._start = time.monotonic()
        elapsed = time.monotonic() - self._start
        return elapsed >= self._timeout
