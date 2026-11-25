"""Scheme catalog pages: 归海 combos and 秋水 per-activity component tables."""
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import qiushui_catalog, scheme_catalog
from ..core.vehicle_components import build_inventory, index_path_for_account
from .theme import GOLD, MUTED, TEXT


class GuihaiPanel(QWidget):
    """All 183 Guihai combos, annotated with what the account already owns."""

    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.summary = scheme_catalog.catalog_summary()
        self.entries = scheme_catalog.catalog_entries()
        self.inventory: list[dict] = []
        self.matches: dict[str, dict] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 8)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("HeroCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 14, 22, 14)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("归海临渊的一图流")
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
        self._setup_table(self.table)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        self.footer = QLabel(
            "数据来源：机动装甲武器.png（归海临渊 2025/11/16）。秋水Ameth 的组件表按积分关卡分散在"
            " 8 个活动 / 21 张表里，见「秋水各关卡」标签页。"
        )
        self.footer.setWordWrap(True)
        self.footer.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        root.addWidget(self.footer)

        self.refresh()

    @staticmethod
    def _setup_table(table: QTableWidget) -> None:
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setStyleSheet(
            "QTableWidget { background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 8px; }"
            "QHeaderView::section { background: #F4F7FB; color: #5C6B7A; border: none;"
            " padding: 6px 8px; font-weight: 700; }"
            "QTableWidget::item { padding: 4px 6px; }"
        )

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
        owned_weapons = {entry["weapon"] for entry in self.entries if entry["id"] in self.matches}
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


class QiushuiPanel(QWidget):
    """Every 秋水 per-activity table (tank / mecha) with owned status."""

    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.summary = qiushui_catalog.summary()
        self.entries = qiushui_catalog.table_entries(include_reference=True)
        self.inventory: list[dict] = []
        self.matches: dict[str, dict] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 8)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("HeroCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 14, 22, 14)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("秋水Ameth · 各积分关卡组件")
        title.setStyleSheet(f"color: {TEXT}; font-size: 25px; font-weight: 800;")
        title_box.addWidget(title)
        sub = QLabel(
            f"{self.summary['source']} · {self.summary['activities']} 个活动 / "
            f"{self.summary['tables']} 张表 / {self.summary['rows']} 条组件需求 / "
            f"{self.summary['components']} 件组件。每张表固定 9 件（4 芯片 + 5 其他）。"
            " 绿底 = 仓库可满足。"
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
        self.activity_combo = QComboBox()
        self.activity_combo.addItem("全部活动", "")
        for activity in qiushui_catalog.activities():
            self.activity_combo.addItem(str(activity.get("name") or ""), str(activity.get("id") or ""))
        self.activity_combo.addItem("图1 总表（旧版参考）", "reference")
        self.activity_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.activity_combo)

        self.side_combo = QComboBox()
        self.side_combo.addItem("全部类型", "")
        for side in self.summary["sides"]:
            self.side_combo.addItem(side, side)
        self.side_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.side_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItem("全部状态", "all")
        self.status_combo.addItem("已拥有", "owned")
        self.status_combo.addItem("缺口", "missing")
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.status_combo)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索活动 / 组件 / 词条")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filters)
        filters.addWidget(self.search_edit, 1)
        root.addLayout(filters)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["活动", "表", "组件", "属性词条1", "属性词条2", "任意词条", "状态", "仓库词条"]
        )
        GuihaiPanel._setup_table(self.table)
        header_view = self.table.horizontalHeader()
        for column in range(7):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(7, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        self.footer = QLabel(
            "数据来源：秋水Ameth 排行关卡表格合集（腾讯文档）。每张表按「主战坦克 / 战术人型机甲」分页；"
            "匹配要求组件名 + 属性词条1 + 属性词条2，任意词条为推荐项。图1 总表作为旧版参考单独列出。"
        )
        self.footer.setWordWrap(True)
        self.footer.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        root.addWidget(self.footer)

        self.refresh()

    def refresh(self, _evaluation=None) -> None:
        self.inventory = build_inventory(index_path_for_account(self.state))
        self.matches = qiushui_catalog.match_inventory(self.inventory, include_reference=True)
        self._apply_filters()

    def _label_for(self, entry: dict) -> str:
        if entry["reference"]:
            return "参考"
        return f"{entry['side']}·{entry['variant']}"

    def _apply_filters(self, *_args) -> None:
        activity = str(self.activity_combo.currentData() or "")
        side = str(self.side_combo.currentData() or "")
        status = str(self.status_combo.currentData() or "all")
        needle = self.search_edit.text().strip()
        rows = []
        for entry in self.entries:
            if activity == "reference":
                if not entry["reference"]:
                    continue
            else:
                if entry["reference"]:
                    continue
                if activity and entry["activity_id"] != activity:
                    continue
            if side and entry["side"] != side:
                continue
            owned = entry["id"] in self.matches
            if status == "owned" and not owned:
                continue
            if status == "missing" and owned:
                continue
            haystack = f"{entry['activity']}{entry['name']}{entry['stat1']}{entry['stat2']}{entry['optional']}"
            if needle and needle not in haystack:
                continue
            rows.append((entry, owned))
        self._fill_table(rows)
        normal = [entry for entry in self.entries if not entry["reference"]]
        owned_rows = sum(1 for entry in normal if entry["id"] in self.matches)
        owned_components = {entry["name"] for entry in normal if entry["id"] in self.matches}
        self.count_label.setText(
            f"显示 {len(rows)} 条\n"
            f"已拥有 {owned_rows}/{len(normal)} 条 · 覆盖 {len(owned_components)}/{self.summary['components']} 件"
        )

    def _fill_table(self, rows: list[tuple[dict, bool]]) -> None:
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))
        palette_ok = QColor("#F2FBF5")
        palette_no = QColor("#FFFFFF")
        for row, (entry, owned) in enumerate(rows):
            info = self.matches.get(entry["id"]) or {}
            values = [
                entry["activity"],
                self._label_for(entry),
                entry["name"],
                entry["stat1"],
                entry["stat2"],
                entry["optional"] or "—",
                f"×{int(info.get('count') or 0)}" if owned else "缺失",
                "；".join(dict.fromkeys(info.get("sources") or [])) if owned else "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setBackground(palette_ok if owned else palette_no)
                if column == 6:
                    item.setForeground(QColor("#2F7D4F" if owned else "#9AA8B6"))
                if column == 7 and value:
                    item.setToolTip(str(value))
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 26)
        self.table.setUpdatesEnabled(True)


class SchemePage(QWidget):
    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 10, 20, 8)
        root.setSpacing(8)
        self.tabs = QTabWidget()
        self.guihai = GuihaiPanel(state)
        self.qiushui = QiushuiPanel(state)
        self.tabs.addTab(self.guihai, "归海一图流")
        self.tabs.addTab(self.qiushui, "秋水各积分关卡")
        root.addWidget(self.tabs, 1)

    def refresh(self, evaluation=None) -> None:
        self.guihai.refresh(evaluation)
        self.qiushui.refresh(evaluation)
