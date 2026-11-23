"""Tank / tactical-mecha component guidance panel."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..core.mecha import classification, get_mecha_data
from .theme import BORDER, GREEN, GOLD, MUTED, ORANGE, PANEL_2, TEXT, TEXT_SOFT


class MechaSection(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.data = get_mecha_data()
        self.schemes = self.data.get("schemes") or []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("机动装甲（坦克 / 战术人型机甲）组件")
        title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 700;")
        title_box.addWidget(title)
        sub = QLabel("按三套养成方案归类：三套都有 = 必需，至少一套 = 部分方案，三套都没有 = 完全fw。")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        title_box.addWidget(sub)
        header.addLayout(title_box, 1)
        self.tank_combo = QComboBox()
        for tank in self.data.get("tanks") or []:
            self.tank_combo.addItem(str(tank.get("name") or tank.get("id")), tank.get("id"))
        self.tank_combo.currentIndexChanged.connect(self._rebuild)
        header.addWidget(self.tank_combo)
        layout.addLayout(header)

        scheme_row = QHBoxLayout()
        scheme_row.setSpacing(6)
        label = QLabel("方案")
        label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        scheme_row.addWidget(label)
        self.scheme_combo = QComboBox()
        self.scheme_combo.addItem("全部方案", "")
        for scheme in self.schemes:
            self.scheme_combo.addItem(str(scheme.get("name") or scheme.get("id")), scheme.get("id"))
        self.scheme_combo.currentIndexChanged.connect(self._rebuild)
        scheme_row.addWidget(self.scheme_combo)
        scheme_row.addStretch(1)
        layout.addLayout(scheme_row)

        self.body = QVBoxLayout()
        self.body.setSpacing(5)
        layout.addLayout(self.body)
        self._rebuild()

    def _tank(self) -> dict:
        key = self.tank_combo.currentData()
        return next(
            (tank for tank in self.data.get("tanks") or [] if tank.get("id") == key),
            (self.data.get("tanks") or [{}])[0],
        )

    def _rebuild(self, *_args) -> None:
        while self.body.count():
            item = self.body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        tank = self._tank()
        selected = str(self.scheme_combo.currentData() or "")
        scheme_count = len(self.schemes)
        components = tank.get("components") or []
        if selected:
            components = [
                component for component in components if selected in (component.get("schemes") or [])
            ]
        if not components:
            empty = QLabel("该方案暂无组件记录。")
            empty.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            self.body.addWidget(empty)
            return
        for component in components:
            row = QFrame()
            row.setStyleSheet(
                f"QFrame {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px; }}"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 10, 6)
            row_layout.setSpacing(8)
            name = QLabel(str(component.get("name") or ""))
            name.setFixedWidth(130)
            name.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 600;")
            row_layout.addWidget(name)
            category = QLabel(str(component.get("category") or ""))
            category.setFixedWidth(82)
            category.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            row_layout.addWidget(category)
            words = QLabel(str(component.get("words") or ""))
            words.setWordWrap(True)
            words.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 11px;")
            row_layout.addWidget(words, 1)
            level = classification(component, scheme_count)
            level_text = {"must": "必需", "partial": "部分方案", "fw": "完全fw"}[level]
            level_color = {"must": GREEN, "partial": ORANGE, "fw": MUTED}[level]
            tag = QLabel(level_text)
            tag.setStyleSheet(
                f"color: {level_color}; font-size: 11px; font-weight: 700;"
                f" border: 1px solid {level_color}; border-radius: 5px; padding: 1px 5px;"
            )
            row_layout.addWidget(tag)
            self.body.addWidget(row)
