"""Project paths and small I/O helpers."""
from __future__ import annotations

import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
DATA_DIR = PACKAGE_ROOT / "data"
CODEX_DIR = DATA_DIR / "codex"
TIER_DIR = DATA_DIR / "tierlists"
ASSETS_DIR = PROJECT_ROOT / "assets"
AVATAR_DIR = ASSETS_DIR / "avatars"
SAMPLE_ACCOUNT = DATA_DIR / "sample_account.json"
HELP_FILE = PROJECT_ROOT / "docs" / "HELP.md"
SETTINGS_FILE = PROJECT_ROOT / ".account_forge_settings.json"


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
