"""Non-sensitive visual preferences for P@ssw0rd."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from vault import application_data_directory


@dataclass(slots=True)
class UiPreferences:
    theme: str = "dark"
    background_image: str = ""
    language: str = "en"


class PreferencesService:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.path = (data_dir or application_data_directory()) / "ui_preferences.json"

    def load(self) -> UiPreferences:
        try:
            content = json.loads(self.path.read_text(encoding="utf-8"))
            theme = content.get("theme", "dark")
            background_image = content.get("background_image", "")
            language = content.get("language", "en")
            return UiPreferences(
                theme=theme if theme in {"light", "dark"} else "dark",
                background_image=background_image,
                language=language if language in {"en", "zh"} else "en",
            )
        except (OSError, json.JSONDecodeError):
            return UiPreferences()

    def save(self, preferences: UiPreferences) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(preferences), indent=2), encoding="utf-8")
