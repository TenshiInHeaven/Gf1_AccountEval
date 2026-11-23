"""Unified mecha component guide from all 秋水Ameth activity tables."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import DATA_DIR, read_json
from .theme import BORDER, GOLD, GREEN, MUTED, ORANGE, PANEL_2, TEXT, TEXT_SOFT


class ComponentPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.data = read_json(DATA_DIR / "components.json", {}) or {}
        self.schemes = self.data.get("schemes") or []
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("HeroCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 16, 22, 16)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("机动装甲组件总表")
        title.setStyleSheet(f"color: {TEXT}; font-size: 25px; font-weight: 800;")
        title_box.addWidget(title)
        sub = QLabel("秋水Ameth 全部活动表统一统计；×N 表示组件在表中重复出现的最大数量。")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        title_box.addWidget(sub)
        header_layout.addLayout(title_box, 1)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部组件", "all")
        self.filter_combo.addItem("金框 · 所有方案都要求", "gold")
        self.filter_combo.addItem("绿框 · 部分方案需求", "green")
        self.filter_combo.addItem("灰框 · 没有方案需求", "gray")
        self.filter_combo.currentIndexChanged.connect(self._render)
        header_layout.addWidget(self.filter_combo)
        root.addWidget(header)

        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        root.addWidget(self.count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.canvas = QWidget()
        scroll.setWidget(self.canvas)
        self.rows_layout = QVBoxLayout(self.canvas)
        self.rows_layout.setContentsMargins(2, 2, 2, 10)
        self.rows_layout.setSpacing(6)
        root.addWidget(scroll, 1)
        self._render()

    def _render(self) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        selected = str(self.filter_combo.currentData() or "all")
        components = self.data.get("components") or []
        shown = []
        for component in components:
            schemes = component.get("schemes") or []
            if len(schemes) >= len(self.schemes):
                level = "gold"
            elif schemes:
                level = "green"
            else:
                level = "gray"
            if selected != "all" and level != selected:
                continue
            shown.append((component, level, schemes))
        counts = {"gold": 0, "green": 0, "gray": 0}
        for component in components:
            schemes = component.get("schemes") or []
            counts["gold" if len(schemes) >= len(self.schemes) else ("green" if schemes else "gray")] += 1
        self.count_label.setText(
            f"共 {len(components)} 个组件 · 金框 {counts['gold']} / 绿框 {counts['green']} / 灰框 {counts['gray']}"
        )
        for component, level, schemes in shown:
            row = self._row(component, level, schemes)
            self.rows_layout.addWidget(row)
        self.rows_layout.addStretch(1)

    def _row(self, component: dict, level: str, schemes: list[str]) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 9px; }}"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        name = QLabel(str(component.get("name") or ""))
        name.setFixedWidth(145)
        name.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 700;")
        layout.addWidget(name)
        count = QLabel(f"×{int(component.get('count') or 0)}")
        count.setFixedWidth(38)
        count.setAlignment(Qt.AlignCenter)
        count.setStyleSheet(f"color: {GOLD}; font-size: 12px; font-weight: 700;")
        layout.addWidget(count)
        category = QLabel(str(component.get("category") or "组件"))
        category.setFixedWidth(78)
        category.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(category)
        words = QLabel(str(component.get("words") or "—"))
        words.setWordWrap(True)
        words.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 11px;")
        layout.addWidget(words, 1)
        scheme_text = " / ".join(
            next((str(s.get("short") or s.get("name")) for s in self.schemes if s.get("id") == key), key)
            for key in schemes
        ) or "无方案记录"
        scheme_label = QLabel(scheme_text)
        scheme_label.setFixedWidth(118)
        scheme_label.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        layout.addWidget(scheme_label)
        color = {"gold": GOLD, "green": GREEN, "gray": MUTED}[level]
        label = {"gold": "金框", "green": "绿框", "gray": "灰框"}[level]
        badge = QLabel(label)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedWidth(48)
        badge.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 700;"
            f" border: 1px solid {color}; border-radius: 6px; padding: 2px;"
        )
        layout.addWidget(badge)
        return row
