"""Tests for engine.data_agent.rate_limiter — token bucket, backoff, circuit breaker."""

import time

import pytest

from engine.data_agent.rate_limiter import DOMAIN_CONFIGS, RateLimiter


class TestAcquire:
    def test_acquire_unknown_domain_does_not_raise(self):
        rl = RateLimiter()
        # Should not raise; unknown domain gets _DEFAULT_CONFIG
        rl.acquire("unknown.domain.test")

    def test_acquire_blocks_at_least_min_delay(self):
        rl = RateLimiter()
        domain = "qt.gtimg.cn"
        # First call — no delay
        rl.acquire(domain)
        rl.record_success(domain)
        t0 = time.perf_counter()
        # Second call — should wait min_delay
        rl.acquire(domain)
        elapsed = time.perf_counter() - t0
        min_delay = DOMAIN_CONFIGS[domain]["min_delay"]
        # Allow 20% jitter tolerance below the floor
        assert elapsed >= min_delay * 0.7, (
            f"Expected ~{min_delay}s delay, got {elapsed:.3f}s"
        )


class TestCircuitBreaker:
    def test_circuit_opens_after_threshold(self):
        rl = RateLimiter()
        domain = "test.circuit.open"
        threshold = 3
        for _ in range(threshold):
            rl.record_failure(domain, 0)
        assert rl.is_circuit_open(domain)

    def test_circuit_stays_closed_below_threshold(self):
        rl = RateLimiter()
        domain = "test.circuit.closed"
        rl.record_failure(domain, 0)
        rl.record_failure(domain, 0)
        assert not rl.is_circuit_open(domain)

    def test_success_resets_consecutive_failures(self):
        rl = RateLimiter()
        domain = "test.reset"
        rl.record_failure(domain, 0)
        rl.record_failure(domain, 0)
        rl.record_success(domain)
        rl.record_failure(domain, 0)
        # Only 1 failure since last success — circuit should be closed
        assert not rl.is_circuit_open(domain)

    def test_circuit_closes_after_cooldown(self):
        rl = RateLimiter()
        domain = "test.cooldown"
        # Override cooldown to be very short for testing
        from engine.data_agent.rate_limiter import _DomainState
        state = rl._get_state(domain)
        state.cooldown_s = 0.01  # 10ms cooldown
        for _ in range(3):
            rl.record_failure(domain, 0)
        assert rl.is_circuit_open(domain)
        time.sleep(0.05)
        assert not rl.is_circuit_open(domain)

    def test_reset_clears_circuit(self):
        rl = RateLimiter()
        domain = "test.reset.circuit"
        for _ in range(5):
            rl.record_failure(domain, 0)
        assert rl.is_circuit_open(domain)
        rl.reset(domain)
        assert not rl.is_circuit_open(domain)


class TestStatus:
    def test_status_returns_dict(self):
        rl = RateLimiter()
        rl.acquire("qt.gtimg.cn")
        status = rl.status("qt.gtimg.cn")
        assert isinstance(status, dict)

    def test_status_shows_circuit_state(self):
        rl = RateLimiter()
        domain = "test.status"
        for _ in range(3):
            rl.record_failure(domain, 0)
        status = rl.status(domain)
        assert status["circuit_open"] is True


class TestDomainConfigs:
    def test_known_domains_present(self):
        expected = {
            "qt.gtimg.cn",
            "hq.sinajs.cn",
            "push2.eastmoney.com",
            "datacenter.eastmoney.com",
            "cninfo.com.cn",
            "tushare",
            "akshare",
        }
        for domain in expected:
            assert domain in DOMAIN_CONFIGS, f"{domain} missing from DOMAIN_CONFIGS"

    def test_cninfo_has_long_cooldown(self):
        assert DOMAIN_CONFIGS["cninfo.com.cn"]["cooldown_s"] >= 1800

    def test_all_configs_have_required_keys(self):
        for domain, cfg in DOMAIN_CONFIGS.items():
            assert "min_delay" in cfg, f"{domain} missing min_delay"
            assert "burst" in cfg, f"{domain} missing burst"
