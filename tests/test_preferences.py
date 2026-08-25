from preferences import PreferencesService, UiPreferences


def test_preferences_round_trip():
    from tempfile import TemporaryDirectory
    from pathlib import Path
    with TemporaryDirectory() as folder:
        service = PreferencesService(Path(folder))
        saved = UiPreferences(theme="light", background_image=r"C:\images\background.png", language="zh")
        service.save(saved)
        assert service.load() == saved


def test_invalid_or_missing_preferences_use_safe_defaults(tmp_path):
    service = PreferencesService(tmp_path)
    assert service.load() == UiPreferences()
    service.path.parent.mkdir(parents=True, exist_ok=True)
    service.path.write_text('{"theme":"unexpected", "language":"unknown"}', encoding="utf-8")
    assert service.load() == UiPreferences()
