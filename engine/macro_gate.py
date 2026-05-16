"""MacroState enum and manual CLI override for macro market state (REQ-001)."""

from __future__ import annotations

import argparse
import json
import os
from enum import StrEnum
from pathlib import Path

_CACHE_FILE: Path = Path("data/cache/macro_state.json")


class MacroState(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


TARGET_ELASTIC_BY_MACRO_STATE: dict[MacroState, float] = {
    MacroState.GREEN: 0.38,
    MacroState.YELLOW: 0.33,
    MacroState.RED: 0.20,
}


def get_macro_state() -> MacroState:
    try:
        raw = json.loads(_CACHE_FILE.read_text())
        if isinstance(raw, dict):
            value = raw.get("state")
            if isinstance(value, str):
                return MacroState(value)
    except (OSError, ValueError):
        pass
    return MacroState.YELLOW


def set_macro_state_override(state: MacroState) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"state": state.value}))
    os.replace(tmp, _CACHE_FILE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set macro state override.")
    parser.add_argument(
        "--set",
        choices=["green", "yellow", "red"],
        required=True,
        dest="state",
        help="New macro state (lowercase).",
    )
    args = parser.parse_args()
    set_macro_state_override(MacroState(args.state))
