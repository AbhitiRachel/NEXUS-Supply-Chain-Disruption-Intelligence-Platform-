"""Lightweight in-process API metrics for NEXUS."""

import time
from threading import Lock


class Metrics:
    def __init__(self):
        self._lock = Lock()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency_ms = 0.0
        self.last_latency_ms = 0.0

    def record(self, latency_ms: float, success: bool):
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms
            self.last_latency_ms = latency_ms

            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

    def snapshot(self):
        with self._lock:
            avg_latency = (
                self.total_latency_ms / self.total_requests
                if self.total_requests
                else 0.0
            )

            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "average_latency_ms": round(avg_latency, 2),
                "last_latency_ms": round(self.last_latency_ms, 2),
            }


metrics = Metrics()
