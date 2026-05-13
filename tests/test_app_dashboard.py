from app.dashboard import main


def test_dashboard_entrypoint_smoke() -> None:
    assert callable(main)

