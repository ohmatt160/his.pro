import threading
import time
from collections import defaultdict


class MetricsService:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, int | float] = defaultdict(int)
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: int | float) -> None:
        with self._lock:
            self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            bucket = self._histograms[name]
            bucket.append(value)
            if len(bucket) > 1000:
                del bucket[: len(bucket) - 1000]

    def snapshot(self) -> dict:
        with self._lock:
            histograms = {}
            for name, values in self._histograms.items():
                ordered = sorted(values)
                count = len(ordered)
                histograms[name] = {
                    "count": count,
                    "avg": sum(ordered) / count if count else 0,
                    "p95": ordered[int(count * 0.95) - 1] if count else 0,
                    "max": ordered[-1] if count else 0,
                }
            return {
                "generated_at": time.time(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histograms,
            }


metrics_service = MetricsService()
