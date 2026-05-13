"""Minimal dashboard entry point for the portfolio advisor."""

from __future__ import annotations


def main() -> None:
    """Run the advisor entry point.

    The full Streamlit dashboard will land in a later phase; this keeps the package
    installable and gives `uv run advisor` a stable smoke-test target.
    """

    try:
        import streamlit as st
    except ModuleNotFoundError:
        print("Advisor scaffold is installed. Install dashboard dependencies to run Streamlit.")
        return

    st.set_page_config(page_title="AI 基建股持仓顾问", layout="wide")
    st.title("AI 基建股持仓顾问")
    st.info("PR1 scaffold is ready. Dashboard views will be implemented in later phases.")


if __name__ == "__main__":
    main()

