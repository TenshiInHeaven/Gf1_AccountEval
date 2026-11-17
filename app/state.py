"""Application state shared by pages."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .core.account import AccountLoader, AccountView, SnapshotError
from .core.paths import SAMPLE_ACCOUNT, read_json, write_json
from .core.ratings import Evaluation, Evaluator


class AppState(QObject):
    account_changed = Signal(object)  # Evaluation
    error = Signal(str)
    notice = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.loader = AccountLoader()
        self.evaluator = Evaluator()
        self.account: AccountView | None = None
        self.evaluation: Evaluation | None = None
        self.source_path: Path | None = None

    # ------------------------------------------------------------------
    def load_path(self, path: Path, *, announce: bool = True) -> bool:
        try:
            account = self.loader.load(path)
        except (OSError, SnapshotError, ValueError) as exc:
            self.error.emit(f"读取快照失败：{exc}")
            return False
        return self._apply(account, path, announce=announce)

    def load_payload(self, payload: dict, source_path: Path | None = None, *, announce: bool = True) -> bool:
        try:
            account = self.loader.from_payload(payload, source_path=source_path)
        except (SnapshotError, ValueError) as exc:
            self.error.emit(f"解析快照失败：{exc}")
            return False
        return self._apply(account, source_path, announce=announce)

    def _apply(self, account: AccountView, path: Path | None, *, announce: bool) -> bool:
        try:
            evaluation = self.evaluator.evaluate(account)
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.error.emit(f"评估失败：{exc}")
            return False
        self.account = account
        self.evaluation = evaluation
        self.source_path = path
        self.account_changed.emit(evaluation)
        if announce:
            self.notice.emit(f"已载入 {account.nickname}（{account.uid}）")
        return True

    def load_sample(self, *, announce: bool = True) -> bool:
        return self.load_path(SAMPLE_ACCOUNT, announce=announce)

    def reload_equipment_rules(self) -> bool:
        self.loader.reload_equipment_engine()
        if self.source_path and self.source_path.is_file():
            return self.load_path(self.source_path, announce=False)
        self.notice.emit("装备规则已保存；重新载入账号后生效。")
        return True

    # ------------------------------------------------------------------
    def save_last_path(self, path: Path) -> None:
        try:
            from .core.paths import SETTINGS_FILE

            payload = read_json(SETTINGS_FILE, {}) or {}
            payload["last_snapshot"] = str(path)
            write_json(SETTINGS_FILE, payload)
        except OSError:
            pass

    def last_path(self) -> Path | None:
        from .core.paths import SETTINGS_FILE

        payload = read_json(SETTINGS_FILE, {}) or {}
        raw = payload.get("last_snapshot")
        if not raw:
            return None
        path = Path(raw)
        return path if path.is_file() else None
