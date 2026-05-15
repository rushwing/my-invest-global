"""
Per-domain rate limiter with token bucket, exponential backoff, and circuit breaker.

Each domain has:
  - min_delay:  minimum seconds between successive requests
  - burst:      max concurrent in-flight requests
  - cooldown_s: circuit-open cooldown after circuit_break_after consecutive failures

Usage:
    rl = RateLimiter()
    rl.acquire("qt.gtimg.cn")      # blocks until slot available
    try:
        ...
        rl.record_success("qt.gtimg.cn")
    except SomeNetworkError:
        rl.record_failure("qt.gtimg.cn", status=429)
"""

import random
import threading
import time
from dataclasses import dataclass, field


@dataclass
class _DomainState:
    # Token bucket
    min_delay: float
    burst: int
    _last_request: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    # Backoff / circuit breaker
    cooldown_s: float = 600.0
    _consecutive_failures: int = field(default=0, init=False)
    _circuit_open_until: float = field(default=0.0, init=False)
    _current_backoff: float = field(default=0.0, init=False)


# Domain-level rate limit configuration.
# min_delay: seconds between successive requests to this domain.
# burst:     max concurrent in-flight requests (not currently enforced; reserved).
# cooldown_s: circuit-open duration on 3 consecutive failures.
DOMAIN_CONFIGS: dict[str, dict] = {
    "qt.gtimg.cn":                    {"min_delay": 0.8,  "burst": 4},
    "web.ifzq.gtimg.cn":              {"min_delay": 1.0,  "burst": 2},
    "hq.sinajs.cn":                   {"min_delay": 1.5,  "burst": 2},
    "push2.eastmoney.com":            {"min_delay": 1.0,  "burst": 2},
    "push2his.eastmoney.com":         {"min_delay": 1.5,  "burst": 2},
    "datacenter.eastmoney.com":       {"min_delay": 2.0,  "burst": 1},
    "emweb.securities.eastmoney.com": {"min_delay": 3.0,  "burst": 1},
    "data.eastmoney.com":             {"min_delay": 2.5,  "burst": 1},
    "cninfo.com.cn":                  {"min_delay": 5.0,  "burst": 1, "cooldown_s": 1800},
    "tushare":                        {"min_delay": 0.2,  "burst": 8},
    "yahoo":                          {"min_delay": 1.5,  "burst": 3},
    "akshare":                        {"min_delay": 2.0,  "burst": 1},
}

_DEFAULT_CONFIG = {"min_delay": 2.0, "burst": 1}

# Backoff ladder in seconds: attempt 1→2→3 get these delays before circuit opens.
_BACKOFF_LADDER = [1.0, 2.0, 5.0, 15.0]
_CIRCUIT_BREAK_AFTER = 3   # consecutive failures before circuit opens
_JITTER_RATIO = 0.2        # ±20% random jitter on every delay


class RateLimiter:
    """Thread-safe, per-domain token-bucket + backoff + circuit breaker."""

    def __init__(self) -> None:
        self._states: dict[str, _DomainState] = {}
        self._global_lock = threading.Lock()

    def _get_state(self, domain: str) -> _DomainState:
        with self._global_lock:
            if domain not in self._states:
                cfg = DOMAIN_CONFIGS.get(domain, _DEFAULT_CONFIG)
                self._states[domain] = _DomainState(
                    min_delay=cfg["min_delay"],
                    burst=cfg.get("burst", 1),
                    cooldown_s=cfg.get("cooldown_s", 600.0),
                )
            return self._states[domain]

    def is_circuit_open(self, domain: str) -> bool:
        """Return True if this domain is in circuit-open (cooling down) state."""
        state = self._get_state(domain)
        return time.monotonic() < state._circuit_open_until

    def acquire(self, domain: str) -> None:
        """
        Block until it is safe to make a request to this domain.
        Raises RuntimeError if the circuit is open — callers that bypass
        AbstractSource._get() (e.g. batch methods) get an immediate error
        instead of silently sending requests during a cooldown.
        """
        state = self._get_state(domain)
        if time.monotonic() < state._circuit_open_until:
            raise RuntimeError(f"Circuit open for {domain} — request blocked by rate limiter")
        with state._lock:
            now = time.monotonic()
            elapsed = now - state._last_request
            base_delay = max(0.0, state.min_delay - elapsed)
            # Apply ±JITTER_RATIO relative jitter
            jitter = base_delay * _JITTER_RATIO * (2 * random.random() - 1)
            delay = max(0.0, base_delay + jitter)
            if delay > 0:
                time.sleep(delay)
            state._last_request = time.monotonic()

    def record_success(self, domain: str) -> None:
        state = self._get_state(domain)
        with state._lock:
            state._consecutive_failures = 0
            state._current_backoff = 0.0
            state._circuit_open_until = 0.0

    def record_failure(self, domain: str, status: int = 0) -> None:
        """
        Record a failed request. Applies exponential backoff; opens circuit after
        _CIRCUIT_BREAK_AFTER consecutive failures.
        """
        state = self._get_state(domain)
        with state._lock:
            state._consecutive_failures += 1
            n = min(state._consecutive_failures - 1, len(_BACKOFF_LADDER) - 1)
            backoff = _BACKOFF_LADDER[n]
            state._current_backoff = backoff
            if state._consecutive_failures >= _CIRCUIT_BREAK_AFTER:
                state._circuit_open_until = time.monotonic() + state.cooldown_s
            else:
                # Apply backoff delay immediately
                time.sleep(backoff)

    def reset(self, domain: str) -> None:
        """Manually reset circuit breaker (e.g., for testing)."""
        state = self._get_state(domain)
        with state._lock:
            state._consecutive_failures = 0
            state._current_backoff = 0.0
            state._circuit_open_until = 0.0

    def status(self, domain: str) -> dict:
        """Return current rate-limiter state for a domain (for logging/debugging)."""
        state = self._get_state(domain)
        now = time.monotonic()
        return {
            "domain": domain,
            "consecutive_failures": state._consecutive_failures,
            "circuit_open": now < state._circuit_open_until,
            "circuit_reopens_in_s": max(0.0, state._circuit_open_until - now),
            "current_backoff_s": state._current_backoff,
        }
