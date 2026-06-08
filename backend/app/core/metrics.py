from collections import deque
from threading import Lock
from typing import Deque


class SlidingWindowMetrics:
    def __init__(self, maxlen: int = 200):
        self._values: Deque[float] = deque(maxlen=maxlen)
        self._lock = Lock()

    def add(self, value_ms: float) -> tuple[float, float]:
        with self._lock:
            self._values.append(value_ms)
            values = sorted(self._values)
            avg = sum(values) / len(values)
            p95_index = max(0, int(len(values) * 0.95) - 1)
            p95 = values[p95_index]
            return avg, p95
