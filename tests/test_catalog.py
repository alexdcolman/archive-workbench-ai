from archive_workbench_ai.catalog import MODEL_CATALOG, data_root, get_model_spec


def test_p2_catalog_has_unique_ids_and_storage_names() -> None:
    ids = [spec.model_id for spec in MODEL_CATALOG]
    storage = [spec.storage_name for spec in MODEL_CATALOG]
    assert len(ids) == len(set(ids))
    assert len(storage) == len(set(storage))
    assert len(ids) >= 3


def test_catalog_resolves_each_model() -> None:
    for spec in MODEL_CATALOG:
        assert get_model_spec(spec.model_id) is spec
        assert {file.role for file in spec.files} == {"model", "mmproj"}


def test_data_root_prefers_new_name_and_reuses_legacy_install(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AW_AI_DATA_HOME", raising=False)
    monkeypatch.delenv("AW_AI01_DATA_HOME", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    legacy = tmp_path / "archive-workbench-ai01"
    legacy.mkdir()
    assert data_root() == legacy.resolve()

    current = tmp_path / "archive-workbench-ai"
    current.mkdir()
    assert data_root() == current.resolve()


def test_data_root_accepts_legacy_environment_variable(tmp_path, monkeypatch) -> None:
    legacy = tmp_path / "legacy-data"
    monkeypatch.delenv("AW_AI_DATA_HOME", raising=False)
    monkeypatch.setenv("AW_AI01_DATA_HOME", str(legacy))
    assert data_root() == legacy.resolve()
