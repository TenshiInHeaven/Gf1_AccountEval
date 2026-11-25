"""Owned vehicle-component library page."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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

from ..core.vehicle_components import build_inventory, index_path_for_account, load_guide
from .theme import GOLD, MUTED, TEXT, TEXT_SOFT


class ComponentPage(QWidget):
    open_schemes = Signal()

    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.guide = load_guide()
        self.schemes = self.guide.get("schemes") or []
        self.entries = self._load_entries()
        self.page_size = 10
        self.common_page = 0
        self.other_page = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 14)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("HeroCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 14, 22, 14)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("机动装甲组件库")
        title.setStyleSheet(f"color: {TEXT}; font-size: 25px; font-weight: 800;")
        title_box.addWidget(title)
        sub = QLabel(
            "当前账号全部组件；金框 = 所有方案要求，绿框 = 部分方案，灰框 = 无方案。"
            "归海按 183 条词条组合、秋水按 21 张积分关卡表逐条校验。"
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        title_box.addWidget(sub)
        header_layout.addLayout(title_box, 1)
        catalog_button = QPushButton("归海方案全表")
        catalog_button.setObjectName("Ghost")
        catalog_button.setToolTip("列出 机动装甲武器.png 中全部 25 件组件 / 183 条词条组合")
        catalog_button.clicked.connect(self.open_schemes.emit)
        header_layout.addWidget(catalog_button)
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
        canvas = QWidget()
        scroll.setWidget(canvas)
        columns = QHBoxLayout(canvas)
        columns.setContentsMargins(2, 2, 2, 8)
        columns.setSpacing(12)

        self.common_column, self.common_title, self.common_rows, self.common_bar, self.common_label = self._column("通用组件")
        self.other_column, self.other_title, self.other_rows, self.other_bar, self.other_label = self._column("其他组件")
        columns.addLayout(self.common_column, 1)
        columns.addLayout(self.other_column, 1)
        root.addWidget(scroll, 1)
        self._render()

    def _column(self, title_text: str):
        column = QVBoxLayout()
        column.setSpacing(6)
        title = QLabel(title_text)
        title.setStyleSheet(f"color: {GOLD if title_text == '通用组件' else MUTED}; font-size: 14px; font-weight: 700;")
        column.addWidget(title)
        rows = QVBoxLayout()
        rows.setSpacing(6)
        column.addLayout(rows)
        column.addStretch(1)
        pager = QHBoxLayout()
        pager.addStretch(1)
        prev = QPushButton("上一页")
        prev.setObjectName("Chip")
        prev.clicked.connect(lambda: self._change_page("common" if title_text == "通用组件" else "other", -1))
        pager.addWidget(prev)
        label = QLabel()
        label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        pager.addWidget(label)
        nxt = QPushButton("下一页")
        nxt.setObjectName("Chip")
        nxt.clicked.connect(lambda: self._change_page("common" if title_text == "通用组件" else "other", 1))
        pager.addWidget(nxt)
        column.addLayout(pager)
        return column, title, rows, (prev, nxt), label

    def _load_entries(self) -> list[dict]:
        return build_inventory(index_path_for_account(self.state))

    def refresh(self, _evaluation=None) -> None:
        self.entries = self._load_entries()
        self.common_page = 0
        self.other_page = 0
        self._render()

    def _level(self, entry: dict) -> str:
        schemes = entry.get("schemes") or []
        if len(schemes) >= len(self.schemes):
            return "gold"
        if schemes:
            return "green"
        return "gray"

    def _on_filter_changed(self, *_args) -> None:
        self.common_page = 0
        self.other_page = 0
        self._render()

    def _filtered(self) -> list[dict]:
        selected = str(self.filter_combo.currentData() or "all")
        if selected == "all":
            entries = list(self.entries)
        elif selected == "union":
            entries = [entry for entry in self.entries if entry.get("schemes")]
        else:
            entries = [entry for entry in self.entries if selected in (entry.get("schemes") or [])]
        entries.sort(
            key=lambda entry: (
                {"gold": 0, "green": 1, "gray": 2}[self._level(entry)],
                str(entry.get("name") or ""),
            )
        )
        return entries

    def _change_page(self, side: str, delta: int) -> None:
        entries = self._filtered()
        rows = [entry for entry in entries if (entry.get("type_id") == 0) == (side == "common")]
        pages = max(1, (len(rows) + self.page_size - 1) // self.page_size)
        current = self.common_page if side == "common" else self.other_page
        value = max(0, min(pages - 1, current + delta))
        if side == "common":
            self.common_page = value
        else:
            self.other_page = value
        self._render()

    def _clear_rows(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Hide/detach immediately: deleteLater alone leaves the old
                # frame painted at its default 640x480 position until the
                # event loop runs, which overlaps the column title.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _render(self) -> None:
        entries = self._filtered()
        common = [entry for entry in entries if entry.get("type_id") == 0]
        other = [entry for entry in entries if entry.get("type_id") != 0]
        common_pages = max(1, (len(common) + self.page_size - 1) // self.page_size)
        other_pages = max(1, (len(other) + self.page_size - 1) // self.page_size)
        self.common_page = max(0, min(common_pages - 1, self.common_page))
        self.other_page = max(0, min(other_pages - 1, self.other_page))
        self._clear_rows(self.common_rows)
        self._clear_rows(self.other_rows)
        for entry in common[self.common_page * self.page_size : (self.common_page + 1) * self.page_size]:
            self.common_rows.addWidget(self._row(entry))
        for entry in other[self.other_page * self.page_size : (self.other_page + 1) * self.page_size]:
            self.other_rows.addWidget(self._row(entry))
        self.common_title.setText(f"通用组件 · {len(common)}")
        self.other_title.setText(f"其他组件 · {len(other)}")
        self.common_label.setText(f"{self.common_page + 1}/{common_pages}")
        self.other_label.setText(f"{self.other_page + 1}/{other_pages}")
        self.common_bar[0].setEnabled(self.common_page > 0)
        self.common_bar[1].setEnabled(self.common_page < common_pages - 1)
        self.other_bar[0].setEnabled(self.other_page > 0)
        self.other_bar[1].setEnabled(self.other_page < other_pages - 1)
        self.count_label.setText(
            f"组件实例 {sum(int(entry.get('count') or 0) for entry in self.entries)} 个 · "
            f"去重 {len(self.entries)} 条 · 当前筛选 {len(entries)} 条"
        )

    def _row(self, entry: dict) -> QFrame:
        colors = {
            "gold": ("#FFF9E8", "#D4AF37"),
            "green": ("#F2FBF5", "#5BB98B"),
            "gray": ("#F1F3F6", "#8D99A6"),
        }
        background, border = colors[self._level(entry)]
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {background}; border: 2px solid {border}; border-radius: 8px; }}"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(5)
        name = QLabel(str(entry.get("name") or ""))
        name.setFixedWidth(86)
        name.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 700;")
        layout.addWidget(name)
        count = QLabel(f"×{int(entry.get('count') or 0)}")
        count.setFixedWidth(28)
        count.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: 700;")
        layout.addWidget(count)
        words = QLabel(str(entry.get("words") or ""))
        words.setWordWrap(True)
        words.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 10px;")
        layout.addWidget(words, 1)
        hits = entry.get("guihai_matches") or []
        qiushui_hits = entry.get("qiushui_matches") or []
        if hits or qiushui_hits:
            parts = []
            if hits:
                parts.append(f"归{len(hits)}")
            if qiushui_hits:
                parts.append(f"秋{len(qiushui_hits)}")
            combo = QLabel(" ".join(parts))
            combo.setFixedWidth(48)
            tip = []
            if hits:
                tip.append("归海命中：\n" + "\n".join(hits))
            if qiushui_hits:
                tip.append("秋水命中：\n" + "\n".join(qiushui_hits))
            combo.setToolTip("\n\n".join(tip))
            combo.setStyleSheet("color: #2F7D4F; font-size: 10px; font-weight: 700;")
            layout.addWidget(combo)
        type_name = QLabel(str(entry.get("type_name") or "其他"))
        type_name.setFixedWidth(56)
        type_name.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        layout.addWidget(type_name)
        if hits or qiushui_hits:
            tip = []
            if hits:
                tip.append("归海命中：\n" + "\n".join(hits))
            if qiushui_hits:
                tip.append("秋水命中：\n" + "\n".join(qiushui_hits))
            row.setToolTip("\n\n".join(tip))
        return row
