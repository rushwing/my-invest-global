"""REQ-014: Session-level passphrase authentication gate."""
from __future__ import annotations

import os

import streamlit as st


def is_unlocked() -> bool:
    return st.session_state.get("unlocked", False)


def is_hash_configured() -> bool:
    return bool(os.getenv("DASHBOARD_PASSPHRASE_HASH", ""))


def try_unlock(passphrase: str) -> bool:
    stored = os.getenv("DASHBOARD_PASSPHRASE_HASH", "")
    if not stored:
        return False  # REQ-014: unconfigured hash must never unlock
    try:
        import bcrypt
        if bcrypt.checkpw(passphrase.encode(), stored.encode()):
            st.session_state["unlocked"] = True
            return True
    except ImportError:
        # bcrypt optional — fall back to plaintext comparison
        if passphrase == stored:
            st.session_state["unlocked"] = True
            return True
    return False


def lock() -> None:
    st.session_state.pop("unlocked", None)
    st.rerun()
