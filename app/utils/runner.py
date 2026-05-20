"""Background task runner for dashboard triggers (data refresh + AI analysis).

Uses a module-level dict as the shared state store so background threads can
write status without depending on Streamlit's session_state (which is not
officially thread-safe).  The dashboard reads from _STATUS each render cycle.
"""
from __future__ import annotations

import subprocess
import threading
from datetime import datetime
from pathlib import Path

# ── Module-level shared state (persists across Streamlit reruns) ──────────────

_STATUS: dict[str, object] = {
    "refresh_status":   "idle",   # idle | running | ok | error
    "analysis_status":  "idle",
    "last_refresh":     None,     # datetime | None
    "last_analysis":    None,
    "refresh_error":    None,     # str | None
    "analysis_error":   None,
}

_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


# ── Internal ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], status_key: str, timestamp_key: str, error_key: str) -> None:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=_PROJECT_ROOT,
        )
        if result.returncode == 0:
            _STATUS[status_key] = "ok"
            _STATUS[error_key] = None
        else:
            _STATUS[status_key] = "error"
            _STATUS[error_key] = (result.stderr or result.stdout or "未知错误").strip()[-200:]
    except Exception as exc:
        _STATUS[status_key] = "error"
        _STATUS[error_key] = str(exc)[:200]
    finally:
        _STATUS[timestamp_key] = datetime.now()


# ── Public API ────────────────────────────────────────────────────────────────

def trigger_refresh() -> None:
    """Launch refresh-data-agent --once in a background thread."""
    if _STATUS["refresh_status"] == "running":
        return
    _STATUS["refresh_status"] = "running"
    _STATUS["refresh_error"] = None
    threading.Thread(
        target=_run,
        args=(
            ["uv", "run", "refresh-data-agent", "--once"],
            "refresh_status", "last_refresh", "refresh_error",
        ),
        daemon=True,
    ).start()


def trigger_analysis() -> None:
    """Launch run_analysis --once in a background thread."""
    if _STATUS["analysis_status"] == "running":
        return
    _STATUS["analysis_status"] = "running"
    _STATUS["analysis_error"] = None
    threading.Thread(
        target=_run,
        args=(
            ["uv", "run", "python", "-m", "scripts.run_analysis",
             "--once", "--db", "data/db/aidc.duckdb"],
            "analysis_status", "last_analysis", "analysis_error",
        ),
        daemon=True,
    ).start()


def get_status() -> dict[str, object]:
    """Return a snapshot of the current runner state (safe to read from any thread)."""
    return dict(_STATUS)
