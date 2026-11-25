"""Full component codex: every component, affix pool and attachment pool."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import DATA_DIR, read_json
from ..core.vehicle_components import build_inventory, index_path_for_account
from .theme import GOLD, MUTED, TEXT


class ComponentCodexPage(QWidget):
    """Local, account-independent 141-component codex."""

    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.payload = read_json(DATA_DIR / "component_codex.json", {}) or {}
        self.entries = list(self.payload.get("components") or [])
        self.inventory: list[dict] = []
        self.owned: dict[str, int] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("Panel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        header_layout.setSpacing(14)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("组件图鉴")
        title.setStyleSheet(f"color: {TEXT}; font-size: 20px; font-weight: 700;")
        title_box.addWidget(title)
        sub = QLabel(
            f"全量 {len(self.entries)} 件组件 · {len(self.payload.get('roll_types') or {})} 类词条池 · "
            "包含词条池 / 配件技能池 / 主技能；不依赖账号快照。"
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        title_box.addWidget(sub)
        header_layout.addLayout(title_box, 1)
        self.count_label = QLabel()
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_label.setStyleSheet(f"color: {GOLD}; font-size: 12px; font-weight: 700;")
        header_layout.addWidget(self.count_label)
        root.addWidget(header)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索组件 / 词条 / 配件")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filters)
        filters.addWidget(self.search_edit, 1)
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部类型", "")
        for type_id, name in (self.payload.get("types") or {}).items():
            self.type_combo.addItem(str(name), str(type_id))
        self.type_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.type_combo)
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部状态", "all")
        self.status_combo.addItem("已拥有", "owned")
        self.status_combo.addItem("未拥有", "missing")
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.status_combo)
        root.addLayout(filters)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["组件", "类型", "星级", "词条池", "配件 / 技能", "主技能", "方案", "拥有"]
        )
        self._setup_table(self.table)
        header_view = self.table.horizontalHeader()
        for column in (0, 1, 2, 6, 7):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.Stretch)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        footer = QLabel(
            "数据来源：游戏 STC 5216/5218/5219/5223 + 组件文本表，已落库为 app/data/component_codex.json；"
            "芯片类组件若没有技能组，配件列显示 —。"
        )
        footer.setWordWrap(True)
        footer.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        root.addWidget(footer)

        self.refresh()

    @staticmethod
    def _setup_table(table: QTableWidget) -> None:
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(
            "QTableWidget { background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 8px; }"
            "QHeaderView::section { background: #F4F7FB; color: #5C6B7A; border: none;"
            " padding: 6px 8px; font-weight: 700; }"
            "QTableWidget::item { padding: 4px 6px; }"
        )

    def refresh(self, _evaluation=None) -> None:
        index_path = index_path_for_account(self.state) if self.state is not None else None
        self.inventory = build_inventory(index_path) if index_path is not None else []
        owned: dict[str, int] = {}
        for entry in self.inventory:
            name = str(entry.get("name") or "")
            owned[name] = owned.get(name, 0) + int(entry.get("count") or 0)
        self.owned = owned
        self._apply_filters()

    def _apply_filters(self, *_args) -> None:
        needle = self.search_edit.text().strip().lower()
        type_id = str(self.type_combo.currentData() or "")
        status = str(self.status_combo.currentData() or "all")
        rows = []
        for entry in self.entries:
            name = str(entry.get("name") or "")
            owned = self.owned.get(name, 0)
            if type_id and str(entry.get("type")) != type_id:
                continue
            if status == "owned" and not owned:
                continue
            if status == "missing" and owned:
                continue
            haystack = " ".join(
                [
                    name,
                    str(entry.get("type_name") or ""),
                    str(entry.get("main_skill") or ""),
                    " ".join(str(stat.get("name") or "") for stat in entry.get("stats") or []),
                    " ".join(str(att.get("name") or "") for att in entry.get("attachments") or []),
                ]
            ).lower()
            if needle and needle not in haystack:
                continue
            rows.append((entry, owned))

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))
        for row, (entry, owned) in enumerate(rows):
            stats = " / ".join(str(stat.get("name") or "") for stat in entry.get("stats") or []) or "—"
            attachments = [str(att.get("name") or "") for att in entry.get("attachments") or []]
            attachment_text = " / ".join(attachments[:6]) + (f" 等 {len(attachments)} 项" if len(attachments) > 6 else "")
            if not attachment_text:
                attachment_text = "—"
            schemes = []
            for scheme in entry.get("schemes") or []:
                schemes.append({"guihai": "归海", "qiushui": "秋水", "laowu": "老吴"}.get(scheme, scheme))
            values = [
                str(entry.get("name") or ""),
                str(entry.get("type_name") or ""),
                "★" * max(0, min(5, int(entry.get("rank") or 0))),
                stats,
                attachment_text,
                str(entry.get("main_skill") or "—"),
                " / ".join(schemes) or "—",
                f"×{owned}" if owned else "未拥有",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 7:
                    item.setForeground(QColor("#2F7D4F" if owned else "#9AA8B6"))
                if column in (3, 4):
                    item.setToolTip(str(value))
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 26)
        self.table.setUpdatesEnabled(True)
        owned_names = sum(1 for entry in self.entries if self.owned.get(str(entry.get("name") or "")))
        self.count_label.setText(f"显示 {len(rows)} / {len(self.entries)} 件\n已拥有 {owned_names} 件")
