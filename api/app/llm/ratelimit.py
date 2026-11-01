"""In-memory token buckets per (provider, model), sized from each provider's requests per minute.

High-priority work, where a person is waiting, may use the whole bucket. Background work
stops while less than `HIGH_SHARE` of the bucket is left, so voice is never stuck behind a
batch of photo assessments. Production moves these buckets to Redis.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from api.app.enums import JobPriority

HIGH_SHARE = 0.7


@dataclass
class _Bucket:
    capacity: float
    tokens: float
    updated: float


class RateLimiter:
    def __init__(
        self,
        rpm_by_provider: dict[str, int | None],
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._rpm = rpm_by_provider
        self._clock = clock
        self._sleep = sleep
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock = threading.Lock()

    def acquire(self, provider: str, model: str, priority: JobPriority, timeout: float) -> bool:
        """Takes one request slot, waiting up to `timeout` seconds. False if none came free."""
        rpm = self._rpm.get(provider)
        if not rpm:
            # No limit configured: the provider console is the source, so nothing is guessed.
            return True
        deadline = self._clock() + timeout
        while True:
            with self._lock:
                bucket = self._refill(provider, model, rpm)
                floor = bucket.capacity * HIGH_SHARE if priority == JobPriority.LOW else 0.0
                if bucket.tokens - 1 >= floor:
                    bucket.tokens -= 1
                    return True
                wait = (floor + 1 - bucket.tokens) * 60 / rpm
            if self._clock() + wait > deadline:
                return False
            self._sleep(wait)

    def _refill(self, provider: str, model: str, rpm: int) -> _Bucket:
        now = self._clock()
        bucket = self._buckets.get((provider, model))
        if bucket is None:
            bucket = self._buckets[(provider, model)] = _Bucket(rpm, rpm, now)
        bucket.tokens = min(bucket.capacity, bucket.tokens + (now - bucket.updated) * rpm / 60)
        bucket.updated = now
        return bucket
