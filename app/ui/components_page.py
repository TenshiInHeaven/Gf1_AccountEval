"""Owned vehicle-component library, split into common / other columns."""
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

from ..core.vehicle_components import build_inventory, load_guide
from ..core.paths import PROJECT_ROOT
from .theme import BORDER, GOLD, GREEN, MUTED, PANEL_2, TEXT, TEXT_SOFT


class ComponentPage(QWidget):
    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.guide = load_guide()
        self.schemes = self.guide.get("schemes") or []
        index_path = None
        source = getattr(state, "source_path", None) if state is not None else None
        if source is not None:
            candidate = (PROJECT_ROOT / "snapshots") / source.name.replace("account_android_", "index_")
            if candidate.is_file():
                index_path = candidate
        self.entries = build_inventory(index_path)
        self.page = 0
        self.page_size = 20
        self.levels = {
            "gold": len(self.schemes),
            "green": max(1, len(self.schemes) - 1),
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 16)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("HeroCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 16, 22, 16)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("机动装甲组件库")
        title.setStyleSheet(f"color: {TEXT}; font-size: 25px; font-weight: 800;")
        title_box.addWidget(title)
        sub = QLabel("显示当前账号的全部组件（通用 / 其他），金色 = 所有方案都要求，绿色 = 部分方案，灰色 = 无方案。")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        title_box.addWidget(sub)
        header_layout.addLayout(title_box, 1)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部组件库", "all")
        self.filter_combo.addItem("全量评价（并集）", "union")
        for scheme in self.schemes:
            self.filter_combo.addItem(str(scheme.get("name") or scheme.get("id")), str(scheme.get("id")))
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
        self.columns = QHBoxLayout(self.canvas)
        self.columns.setContentsMargins(2, 2, 2, 8)
        self.columns.setSpacing(12)
        self.common_column = QVBoxLayout()
        self.common_column.setSpacing(6)
        self.other_column = QVBoxLayout()
        self.other_column.setSpacing(6)
        self.common_title = QLabel("通用组件")
        self.common_title.setStyleSheet(f"color: {GOLD}; font-size: 14px; font-weight: 700;")
        self.other_title = QLabel("其他组件")
        self.other_title.setStyleSheet(f"color: {MUTED}; font-size: 14px; font-weight: 700;")
        self.common_column.addWidget(self.common_title)
        self.other_column.addWidget(self.other_title)
        self.common_rows = QVBoxLayout()
        self.common_rows.setSpacing(6)
        self.other_rows = QVBoxLayout()
        self.other_rows.setSpacing(6)
        self.common_column.addLayout(self.common_rows)
        self.other_column.addLayout(self.other_rows)
        self.common_column.addStretch(1)
        self.other_column.addStretch(1)
        self.columns.addLayout(self.common_column, 1)
        self.columns.addLayout(self.other_column, 1)
        root.addWidget(scroll, 1)

        pager = QHBoxLayout()
        pager.addStretch(1)
        self.prev_button = QPushButton("上一页")
        self.prev_button.setObjectName("Chip")
        self.prev_button.clicked.connect(self._prev_page)
        pager.addWidget(self.prev_button)
        self.page_label = QLabel()
        self.page_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        pager.addWidget(self.page_label)
        self.next_button = QPushButton("下一页")
        self.next_button.setObjectName("Chip")
        self.next_button.clicked.connect(self._next_page)
        pager.addWidget(self.next_button)
        root.addLayout(pager)
        self._render()

    def refresh(self, _evaluation=None) -> None:
        index_path = None
        source = getattr(self, "state", None)
        if source is not None:
            candidate = (PROJECT_ROOT / "snapshots") / source.source_path.name.replace("account_android_", "index_") if source.source_path else None
            if candidate and candidate.is_file():
                index_path = candidate
        self.entries = build_inventory(index_path)
        self.page = 0
        self._render()

    def _level(self, entry: dict) -> str:
        schemes = entry.get("schemes") or []
        if len(schemes) >= len(self.schemes):
            return "gold"
        if schemes:
            return "green"
        return "gray"

    def _on_filter_changed(self, *_args) -> None:
        self.page = 0
        self._render()

    def _goto_page(self, value: int) -> None:
        pages = max(1, (self._filtered_count() + self.page_size - 1) // self.page_size)
        self.page = max(0, min(pages - 1, value))
        self._render()

    def _prev_page(self) -> None:
        self._goto_page(self.page - 1)

    def _next_page(self) -> None:
        self._goto_page(self.page + 1)

    def _filtered(self) -> list[dict]:
        selected = str(self.filter_combo.currentData() or "all")
        if selected == "all":
            return list(self.entries)
        if selected == "union":
            return [entry for entry in self.entries if entry.get("schemes")]
        return [
            entry
            for entry in self.entries
            if selected in (entry.get("schemes") or [])
        ]

    def _filtered_count(self) -> int:
        return len(self._filtered())

    def _clear_rows(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render(self) -> None:
        entries = self._filtered()
        entries.sort(
            key=lambda entry: (
                {"gold": 0, "green": 1, "gray": 2}[self._level(entry)],
                0 if entry.get("type_id") == 0 else 1,
                str(entry.get("name") or ""),
            )
        )
        pages = max(1, (len(entries) + self.page_size - 1) // self.page_size)
        self.page = max(0, min(pages - 1, self.page))
        start = self.page * self.page_size
        shown = entries[start : start + self.page_size]
        self._clear_rows(self.common_rows)
        self._clear_rows(self.other_rows)
        common = [entry for entry in shown if entry.get("type_id") == 0]
        other = [entry for entry in shown if entry.get("type_id") != 0]
        for entry in common:
            self.common_rows.addWidget(self._row(entry))
        for entry in other:
            self.other_rows.addWidget(self._row(entry))
        self.common_title.setText(f"通用组件 · {len(common)}")
        self.other_title.setText(f"其他组件 · {len(other)}")
        self.count_label.setText(
            f"组件实例 {sum(int(entry.get('count') or 0) for entry in self.entries)} 个 · "
            f"去重 {len(self.entries)} 条 · 当前筛选 {len(entries)} 条"
        )
        self.page_label.setText(f"第 {self.page + 1}/{pages} 页")
        self.prev_button.setEnabled(self.page > 0)
        self.next_button.setEnabled(self.page < pages - 1)

    def _row(self, entry: dict) -> QFrame:
        level = self._level(entry)
        colors = {
            "gold": ("#FFF9E8", "#D4AF37"),
            "green": ("#F2FBF5", "#5BB98B"),
            "gray": ("#F1F3F6", "#8D99A6"),
        }
        background, border = colors[level]
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {background}; border: 2px solid {border}; border-radius: 8px; }}"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(9, 6, 9, 6)
        layout.setSpacing(6)
        name = QLabel(str(entry.get("name") or ""))
        name.setFixedWidth(96)
        name.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 700;")
        layout.addWidget(name)
        count = QLabel(f"×{int(entry.get('count') or 0)}")
        count.setFixedWidth(30)
        count.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: 700;")
        layout.addWidget(count)
        words = QLabel(str(entry.get("words") or ""))
        words.setWordWrap(True)
        words.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 10px;")
        layout.addWidget(words, 1)
        type_name = QLabel(str(entry.get("type_name") or "其他"))
        type_name.setFixedWidth(58)
        type_name.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        layout.addWidget(type_name)
        return row
