"""Minimal ingestion entry point for ADR-002 agent files."""

from __future__ import annotations

from pathlib import Path

DEFAULT_AGENT_INPUT_DIR = Path("data/agent_input")


def list_agent_inputs(input_dir: Path = DEFAULT_AGENT_INPUT_DIR) -> list[Path]:
    """Return agent input files in deterministic order."""

    if not input_dir.exists():
        return []
    return sorted(
        path for path in input_dir.iterdir() if path.is_file() and path.name != ".gitkeep"
    )


def main() -> None:
    """Print a small ingestion status summary."""

    files = list_agent_inputs()
    print(f"Found {len(files)} agent input file(s).")


if __name__ == "__main__":
    main()
