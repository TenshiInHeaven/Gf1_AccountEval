"""Unified mecha component guide from all 秋水Ameth activity tables."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        self.page = 0
        self.page_size = 9
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
        sub = QLabel("秋水Ameth 全部活动表统一统计；金框 = 所有方案要求，绿框 = 部分方案，灰框 = 无方案。")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        title_box.addWidget(sub)
        header_layout.addLayout(title_box, 1)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全量评价（并集）", "all")
        for scheme in self.schemes:
            self.filter_combo.addItem(str(scheme.get("short") or scheme.get("name")), str(scheme.get("id")))
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
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

        pager = QHBoxLayout()
        pager.setSpacing(6)
        pager.addStretch(1)
        self.prev_button = QPushButton("上一页")
        self.prev_button.setObjectName("Chip")
        self.prev_button.clicked.connect(self._prev_page)
        pager.addWidget(self.prev_button)
        self.page_buttons = []
        for index in range(3):
            button = QPushButton(str(index + 1))
            button.setObjectName("Chip")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, value=index: self._goto_page(value))
            self.page_buttons.append(button)
            pager.addWidget(button)
        self.next_button = QPushButton("下一页")
        self.next_button.setObjectName("Chip")
        self.next_button.clicked.connect(self._next_page)
        pager.addWidget(self.next_button)
        root.addLayout(pager)
        self._render()

    def _level(self, component: dict) -> str:
        schemes = component.get("schemes") or []
        if len(schemes) >= len(self.schemes):
            return "gold"
        if schemes:
            return "green"
        return "gray"

    def _on_filter_changed(self, *_args) -> None:
        self.page = 0
        self._render()

    def _goto_page(self, index: int) -> None:
        self.page = max(0, min(2, index))
        self._render()

    def _prev_page(self) -> None:
        self._goto_page(self.page - 1)

    def _next_page(self) -> None:
        self._goto_page(self.page + 1)

    def _render(self) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        selected = str(self.filter_combo.currentData() or "all")
        components = self.data.get("components") or []
        counts = {
            "gold": sum(1 for item in components if self._level(item) == "gold"),
            "green": sum(1 for item in components if self._level(item) == "green"),
            "gray": sum(1 for item in components if self._level(item) == "gray"),
        }
        level_rank = {"gold": 0, "green": 1, "gray": 2}
        if selected == "all":
            ordered = sorted(components, key=lambda item: (level_rank[self._level(item)], str(item.get("name") or "")))
        else:
            ordered = sorted(
                components,
                key=lambda item: (
                    0 if selected in (item.get("schemes") or []) else 1,
                    level_rank[self._level(item)],
                    str(item.get("name") or ""),
                ),
            )
        pages = 3
        self.page = max(0, min(pages - 1, self.page))
        start = self.page * self.page_size
        shown = ordered[start : start + self.page_size]
        self.count_label.setText(
            f"共 {len(components)} 个组件 · 金框 {counts['gold']} / 绿框 {counts['green']} / 灰框 {counts['gray']} · "
            f"第 {self.page + 1}/{pages} 页"
        )
        for component in shown:
            self.rows_layout.addWidget(self._row(component))
        self.rows_layout.addStretch(1)
        self.prev_button.setEnabled(self.page > 0)
        self.next_button.setEnabled(self.page < pages - 1)
        for index, button in enumerate(self.page_buttons):
            button.setChecked(index == self.page)

    def _row(self, component: dict) -> QFrame:
        level = self._level(component)
        colors = {
            "gold": ("#FFF9E8", "#D4AF37"),
            "green": ("#F2FBF5", "#5BB98B"),
            "gray": ("#F1F3F6", "#8D99A6"),
        }
        background, border = colors[level]
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {background}; border: 2px solid {border}; border-radius: 9px; }}"
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
        schemes = component.get("schemes") or []
        scheme_text = " / ".join(
            next((str(s.get("short") or s.get("name")) for s in self.schemes if s.get("id") == key), key)
            for key in schemes
        ) or "无方案记录"
        scheme_label = QLabel(scheme_text)
        scheme_label.setFixedWidth(118)
        scheme_label.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        layout.addWidget(scheme_label)
        return row
