import time
from collections import defaultdict, deque
from threading import Lock


class FixedWindowRateLimiter:
    def __init__(self, max_attempts: int, period_seconds: int):
        self.max_attempts = max_attempts
        self.period_seconds = period_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            bucket = self._attempts[key]
            threshold = now - self.period_seconds
            while bucket and bucket[0] < threshold:
                bucket.popleft()
            if len(bucket) >= self.max_attempts:
                return False
            bucket.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
