"""Rate limiter en memoria, por réplica — la primera barrera del login.

Ventana deslizante simple por clave (aquí, la IP del cliente). No sustituye
el lockout por cuenta (que vive en BD y aplica entre réplicas) ni el rate
limiting del gateway/ingress en producción — los complementa: sin esto, una
sola IP puede quemar CPU en bcrypt a voluntad incluso sin acertar cuentas.
"""

import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Registra un intento para la clave y dice si sigue dentro del límite."""
        if self.limit <= 0:  # deshabilitado (suites de prueba)
            return True
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self.window_seconds
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
