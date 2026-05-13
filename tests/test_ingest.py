from scripts.ingest import list_agent_inputs


def test_list_agent_inputs_returns_empty_for_missing_dir(tmp_path) -> None:
    assert list_agent_inputs(tmp_path / "missing") == []

