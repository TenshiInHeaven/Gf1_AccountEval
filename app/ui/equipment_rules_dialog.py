"""Editable equipment matching rules (three categories)."""
from __future__ import annotations

import copy
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.equipment import (
    load_equipment_payload,
    reset_equipment_payload,
    save_equipment_payload,
)
from ..state import AppState
from .theme import BORDER, MUTED, PANEL, TEXT, TEXT_SOFT


class EquipmentRulesDialog(QDialog):
    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.payload = copy.deepcopy(load_equipment_payload())
        self.rows: list[tuple[dict, QSpinBox, QLineEdit]] = []
        self.setWindowTitle("调整装备对应规则")
        self.resize(980, 720)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(f"QDialog {{ background: {PANEL}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)
        title = QLabel("装备对应规则")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)
        note = QLabel(
            "三个分区：配件 / 子弹 / 人形。match 支持 category、type、code_contains、"
            "name_contains、armor_piercing_min/max 等字段；保存后立即重新计算。"
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(note)

        tabs = QTabWidget()
        for category in self.payload.get("categories") or []:
            tabs.addTab(self._build_category(category), str(category.get("name") or category.get("id")))
        layout.addWidget(tabs, 1)

        footer = QHBoxLayout()
        reset = QPushButton("恢复默认")
        reset.setObjectName("Ghost")
        reset.clicked.connect(self._reset)
        footer.addWidget(reset)
        footer.addStretch(1)
        cancel = QPushButton("取消")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        save = QPushButton("保存并重算")
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        footer.addWidget(save)
        layout.addLayout(footer)

    def _build_category(self, category: dict) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        canvas = QWidget()
        rows = QVBoxLayout(canvas)
        rows.setContentsMargins(4, 4, 4, 4)
        rows.setSpacing(7)
        for target in category.get("items") or []:
            row = QHBoxLayout()
            name = QLabel(str(target.get("name") or target.get("id")))
            name.setFixedWidth(100)
            name.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 600;")
            row.addWidget(name)
            count = QSpinBox()
            count.setRange(0, 9999)
            count.setValue(int(target.get("target") or 0))
            count.setFixedWidth(70)
            row.addWidget(count)
            match = QLineEdit()
            match.setText(json.dumps(target.get("match") or {}, ensure_ascii=False))
            match.setStyleSheet(
                f"QLineEdit {{ background: #F8FBFF; color: {TEXT_SOFT};"
                f" border: 1px solid {BORDER}; border-radius: 6px; padding: 4px 7px;"
                " font-family: Consolas, monospace; font-size: 11px; }"
            )
            row.addWidget(match, 1)
            self.rows.append((target, count, match))
            rows.addLayout(row)
        rows.addStretch(1)
        scroll.setWidget(canvas)
        page_layout.addWidget(scroll)
        return page

    def _collect(self) -> dict:
        payload = copy.deepcopy(self.payload)
        for target, count, match in self.rows:
            try:
                rule = json.loads(match.text().strip() or "{}")
            except ValueError as exc:
                raise ValueError(f"{target.get('name')} 的 match 不是合法 JSON：{exc}") from exc
            if not isinstance(rule, dict):
                raise ValueError(f"{target.get('name')} 的 match 必须是 JSON 对象")
            target["target"] = int(count.value())
            target["match"] = rule
        return payload

    def _save(self) -> None:
        try:
            payload = self._collect()
            save_equipment_payload(payload)
            self.state.reload_equipment_rules()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self.accept()

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "恢复默认",
            "删除本地自定义规则并恢复内置规则？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        reset_equipment_payload()
        self.state.reload_equipment_rules()
        self.accept()
