"""Full Guihai word-combo catalog page."""
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

from ..core import scheme_catalog
from ..core.vehicle_components import build_inventory, index_path_for_account
from .theme import GOLD, MUTED, TEXT


class SchemePage(QWidget):
    """All 183 Guihai combos, annotated with what the account already owns."""

    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.summary = scheme_catalog.catalog_summary()
        self.entries = scheme_catalog.catalog_entries()
        self.inventory: list[dict] = []
        self.matches: dict[str, dict] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 14)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("HeroCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 14, 22, 14)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("归海方案全表")
        title.setStyleSheet(f"color: {TEXT}; font-size: 25px; font-weight: 800;")
        title_box.addWidget(title)
        sub = QLabel(
            f"{self.summary['source']} · {self.summary['weapons']} 件组件 / "
            f"{self.summary['main_rows']} 条主词条方案 / {self.summary['entries']} 条词条组合。"
            " 绿底 = 仓库里有组件能凑出这条组合。"
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
        self.group_combo = QComboBox()
        self.group_combo.addItem("全部组", "")
        for group in self.summary["groups"]:
            self.group_combo.addItem(group, group)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        filters.addWidget(self.group_combo)

        self.weapon_combo = QComboBox()
        self.weapon_combo.addItem("全部组件", "")
        self.weapon_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.weapon_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItem("全部状态", "all")
        self.status_combo.addItem("已拥有", "owned")
        self.status_combo.addItem("缺口", "missing")
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.status_combo)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索组件 / 主词条 / 词条")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filters)
        filters.addWidget(self.search_edit, 1)
        root.addLayout(filters)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["组", "组件", "主词条", "词条组合", "状态", "仓库词条"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 8px; }"
            "QHeaderView::section { background: #F4F7FB; color: #5C6B7A; border: none;"
            " padding: 6px 8px; font-weight: 700; }"
            "QTableWidget::item { padding: 4px 6px; }"
        )
        root.addWidget(self.table, 1)

        self.footer = QLabel(
            "数据来源：机动装甲武器.png（归海临渊 2025/11/16）。秋水Ameth 的组件表只到 9 件，"
            "老吴仙人 9 件；两套都在「组件」页按方案筛选。"
        )
        self.footer.setWordWrap(True)
        self.footer.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        root.addWidget(self.footer)

        self.refresh()

    def _on_group_changed(self, *_args) -> None:
        group = str(self.group_combo.currentData() or "")
        self.weapon_combo.blockSignals(True)
        self.weapon_combo.clear()
        self.weapon_combo.addItem("全部组件", "")
        names = []
        for entry in self.entries:
            if group and entry["group"] != group:
                continue
            if entry["weapon"] not in names:
                names.append(entry["weapon"])
        for name in names:
            self.weapon_combo.addItem(name, name)
        self.weapon_combo.blockSignals(False)
        self._apply_filters()

    def refresh(self, _evaluation=None) -> None:
        self.inventory = build_inventory(index_path_for_account(self.state))
        self.matches = scheme_catalog.match_inventory(self.inventory, self.entries)
        self._apply_filters()

    def _apply_filters(self, *_args) -> None:
        group = str(self.group_combo.currentData() or "")
        weapon = str(self.weapon_combo.currentData() or "")
        status = str(self.status_combo.currentData() or "all")
        needle = self.search_edit.text().strip()
        rows = []
        for entry in self.entries:
            if group and entry["group"] != group:
                continue
            if weapon and entry["weapon"] != weapon:
                continue
            owned = entry["id"] in self.matches
            if status == "owned" and not owned:
                continue
            if status == "missing" and owned:
                continue
            if needle and needle not in (entry["weapon"] + entry["label"]):
                continue
            rows.append((entry, owned))
        self._fill_table(rows)
        owned_rows = sum(1 for entry in self.entries if entry["id"] in self.matches)
        owned_weapons = {
            entry["weapon"]
            for entry in self.entries
            if entry["id"] in self.matches
        }
        self.count_label.setText(
            f"显示 {len(rows)} / {len(self.entries)} 条\n"
            f"已拥有 {owned_rows} 条 · 覆盖 {len(owned_weapons)}/{self.summary['weapons']} 件"
        )

    def _fill_table(self, rows: list[tuple[dict, bool]]) -> None:
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))
        palette_ok = QColor("#F2FBF5")
        palette_no = QColor("#FFFFFF")
        for row, (entry, owned) in enumerate(rows):
            info = self.matches.get(entry["id"]) or {}
            values = [
                entry["group"],
                entry["weapon"],
                entry["main"] or "—",
                entry["label"],
                f"×{int(info.get('count') or 0)}" if owned else "缺失",
                "；".join(dict.fromkeys(info.get("sources") or [])) if owned else "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setBackground(palette_ok if owned else palette_no)
                if column == 4:
                    item.setForeground(QColor("#2F7D4F" if owned else "#9AA8B6"))
                if column == 5 and value:
                    item.setToolTip(str(value))
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 26)
        self.table.setUpdatesEnabled(True)
