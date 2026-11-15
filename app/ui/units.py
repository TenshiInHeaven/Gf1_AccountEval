"""Unit grid pages for T-Dolls, fairies and Sangvis units."""
from __future__ import annotations

import html
from collections import defaultdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..core.account import AccountView, OwnedUnit
from ..core.codex import CodexItem, get_codex
from ..core.normalize import type_label
from ..core.ratings import Evaluation
from ..core.tiers import get_tierlists
from .animations import fade_in
from .theme import BORDER, GOLD, MUTED, PANEL, TEXT, TEXT_SOFT, TIER_COLORS
from .widgets import AvatarLabel, FlowLayout, TierBadge, UnitCard


def clear_flow(layout: FlowLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _copy_detail_html(unit: OwnedUnit, kind: str, note: str) -> str:
    """Render per-copy configuration for the detail dialog.

    Fairy quality is intentionally shown as a breakdown instead of "max
    quality × total copies" — a player can own several 5★ copies plus many
    1★ copies of the same fairy.
    """
    if not unit.copies:
        return (
            f"<div style='color:#5F7590;font-size:12px'>快照中没有逐条复制记录；"
            f"仅知道共 {unit.count} 份。</div>"
        )
    parts = [
        f"<div style='font-size:14px;font-weight:700;color:#15263B'>"
        f"共 {unit.count} 份 · 最高配置 Lv.{unit.level}</div>"
    ]
    if kind == "fairy":
        groups: dict[int, list[dict]] = defaultdict(list)
        for copy in unit.copies:
            groups[int(copy.get("quality") or 0)].append(copy)
        parts.append(
            "<div style='color:#5F7590;font-size:12px;margin-top:2px'>"
            "品质分布：" + " · ".join(
                f"{quality}★ × {len(items)}"
                for quality, items in sorted(groups.items(), reverse=True)
            ) + "</div>"
        )
        for quality, items in sorted(groups.items(), reverse=True):
            parts.append(
                f"<div style='margin-top:10px;color:#1D4ED8;font-weight:700;font-size:13px'>"
                f"{quality}★ × {len(items)}</div>"
            )
            for copy in items:
                meta = [
                    f"Lv.{copy.get('level', 0)}",
                    f"技能 {copy.get('skill_level', 0)}",
                ]
                if copy.get("mod"):
                    meta.append(f"改造 {copy['mod']}")
                if copy.get("equip_id"):
                    meta.append(f"装备 {copy['equip_id']}")
                if copy.get("team_id"):
                    meta.append(f"编队 {copy['team_id']}")
                parts.append(
                    "<div style='color:#334A63;font-size:12px;margin-left:8px'>"
                    + " · ".join(meta)
                    + f" <span style='color:#8A9CB3'>#{copy.get('id', '')}</span></div>"
                )
    elif kind == "doll":
        for copy in unit.copies:
            meta = [
                f"Lv.{copy.get('level', 0)}",
                f"改造 {copy.get('mod', 0)}",
                f"好感 {copy.get('favor', 0)}",
            ]
            if copy.get("team_id"):
                meta.append(f"编队 {copy['team_id']}")
            if copy.get("skin_id"):
                meta.append(f"皮肤 {copy['skin_id']}")
            parts.append(
                "<div style='color:#334A63;font-size:12px;margin-top:6px'>"
                + " · ".join(meta)
                + f" <span style='color:#8A9CB3'>#{copy.get('uid', '')}</span></div>"
            )
    else:
        for copy in unit.copies:
            meta = [
                f"Lv.{copy.get('level', 0)}",
                f"扩编 {copy.get('advance', 0)}",
                f"解析 {copy.get('resolution_level', 0)}",
            ]
            if copy.get("team_id"):
                meta.append(f"编队 {copy['team_id']}")
            parts.append(
                "<div style='color:#334A63;font-size:12px;margin-top:6px'>"
                + " · ".join(meta)
                + f" <span style='color:#8A9CB3'>#{copy.get('info_id', '')}</span></div>"
            )
    parts.append(
        f"<div style='color:#5F7590;font-size:11px;margin-top:14px'>"
        f"数据来源：{html.escape(note)}</div>"
    )
    return "".join(parts)


class UnitDetailDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("单位详情")
        self.setFixedSize(640, 680)
        self.setStyleSheet(f"QDialog {{ background: {PANEL}; }}")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(12)
        top = QHBoxLayout()
        top.setSpacing(18)
        self.avatar = AvatarLabel(112, "?")
        top.addWidget(self.avatar)
        info = QVBoxLayout()
        info.setSpacing(5)
        self.name = QLabel()
        self.name.setStyleSheet(f"color: {TEXT}; font-size: 26px; font-weight: 700;")
        info.addWidget(self.name)
        self.code = QLabel()
        self.code.setStyleSheet(f"color: {MUTED}; font-size: 14px;")
        info.addWidget(self.code)
        tier_row = QHBoxLayout()
        self.badge = TierBadge("C")
        tier_row.addWidget(self.badge)
        self.tier_hint = QLabel()
        self.tier_hint.setStyleSheet(f"color: {MUTED}; font-size: 14px;")
        tier_row.addWidget(self.tier_hint)
        tier_row.addStretch(1)
        info.addLayout(tier_row)
        info.addStretch(1)
        top.addLayout(info, 1)
        outer.addLayout(top)

        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(False)
        self.detail.setStyleSheet(
            f"QTextBrowser {{ background: #FBFDFF; color: {TEXT_SOFT};"
            f" border: 1px solid {BORDER}; border-radius: 10px;"
            " padding: 8px 10px; font-size: 14px; }"
        )
        outer.addWidget(self.detail, 1)
        close = QPushButton("关闭")
        close.setObjectName("Ghost")
        close.clicked.connect(self.accept)
        outer.addWidget(close, 0, Qt.AlignRight)

    def show_unit(self, name: str, code: str, tier: str, tier_hint: str, avatar, detail_html: str) -> None:
        self.name.setText(name)
        self.code.setText(code)
        self.badge.set_tier(tier)
        self.tier_hint.setText(tier_hint)
        self.avatar.set_avatar(avatar, name[:2])
        self.detail.setHtml(detail_html)


class UnitPage(QWidget):
    def __init__(self, kind: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind = kind
        self.codex = get_codex()
        self.tiers = get_tierlists()[kind]
        self.account: AccountView | None = None
        self._tier_filters: set[str] = set()
        self._updating_filters = False
        self._type_filter = 0
        self._limit = 120
        self._cards: list[UnitCard] = []
        self._grid_anim = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QFrame()
        toolbar.setStyleSheet(f"QFrame {{ background: transparent; border-bottom: 1px solid {BORDER}; }}")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(28, 12, 28, 12)
        toolbar_layout.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索名称 / 代号…")
        self.search.setFixedWidth(220)
        self.search.textChanged.connect(self._on_filter_changed)
        toolbar_layout.addWidget(self.search)

        self.tier_group = QButtonGroup(self)
        self.tier_group.setExclusive(False)
        self.tier_buttons = {}
        for tier in ["全部"] + [t.id for t in self.tiers.ordered()]:
            button = QPushButton(tier)
            button.setObjectName("Chip")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            if tier == "全部":
                button.setChecked(True)
            button.toggled.connect(
                lambda checked, value=tier: self._toggle_tier(value, checked)
            )
            self.tier_group.addButton(button)
            self.tier_buttons[tier] = button
            toolbar_layout.addWidget(button)

        self.type_combo = QComboBox()
        self.type_combo.addItem("全部类型", 0)
        for type_id, label in ((1, "HG 手枪"), (2, "SMG 冲锋枪"), (3, "RF 步枪"), (4, "AR 突击步枪"), (5, "MG 机枪"), (6, "SG 霰弹枪")):
            self.type_combo.addItem(label, type_id)
        self.type_combo.currentIndexChanged.connect(self._on_filter_changed)
        if kind == "doll":
            toolbar_layout.addWidget(self.type_combo)
        else:
            self.type_combo.hide()

        toolbar_layout.addStretch(1)
        self.owned_toggle = QPushButton("只看已拥有")
        self.owned_toggle.setObjectName("Chip")
        self.owned_toggle.setCheckable(True)
        self.owned_toggle.setChecked(True)
        self.owned_toggle.setCursor(Qt.PointingHandCursor)
        self.owned_toggle.clicked.connect(self._on_filter_changed)
        toolbar_layout.addWidget(self.owned_toggle)
        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        toolbar_layout.addWidget(self.count_label)
        root.addWidget(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll, 1)
        self.canvas = QWidget()
        scroll.setWidget(self.canvas)
        outer = QVBoxLayout(self.canvas)
        outer.setContentsMargins(28, 18, 28, 22)
        outer.setSpacing(12)
        self.flow = FlowLayout(h_spacing=12, v_spacing=12)
        outer.addLayout(self.flow)
        self.more = QPushButton("加载更多")
        self.more.setObjectName("Ghost")
        self.more.clicked.connect(self._load_more)
        outer.addWidget(self.more, 0, Qt.AlignHCenter)
        outer.addStretch(1)

    # ------------------------------------------------------------------
    def refresh(self, evaluation: Evaluation) -> None:
        self.account = evaluation.account
        self._render()

    def set_owned_only(self, enabled: bool) -> None:
        self.owned_toggle.setChecked(enabled)
        self._render()

    def _toggle_tier(self, tier: str, checked: bool) -> None:
        """Multi-select tier chips; ``全部`` is a shortcut for an empty set."""
        if self._updating_filters:
            return
        self._updating_filters = True
        try:
            if tier == "全部":
                if checked:
                    for name, button in self.tier_buttons.items():
                        if name != "全部" and button.isChecked():
                            button.setChecked(False)
                    self._tier_filters.clear()
                else:
                    # Never allow a state with no selected chip.
                    self.tier_buttons["全部"].setChecked(True)
                    self._tier_filters.clear()
            else:
                if checked:
                    self.tier_buttons["全部"].setChecked(False)
                    self._tier_filters.add(tier)
                else:
                    self._tier_filters.discard(tier)
                    if not self._tier_filters:
                        self.tier_buttons["全部"].setChecked(True)
        finally:
            self._updating_filters = False
        self._limit = 120
        self._render()

    def _on_filter_changed(self, *args) -> None:
        self._limit = 120
        self._render()

    def _owned_map(self) -> dict[str, OwnedUnit]:
        if not self.account:
            return {}
        return {unit.code: unit for unit in self.account.units(self.kind)}

    def _all_items(self) -> list[tuple[CodexItem, OwnedUnit | None]]:
        owned = self._owned_map()
        result: list[tuple[CodexItem, OwnedUnit | None]] = []
        for item in self.codex.by_kind[self.kind]:
            result.append((item, owned.get(item.code)))
        # Include owned codes that are not in the codex (rare NPC / event units).
        known = {item.code for item in self.codex.by_kind[self.kind]}
        for code, unit in owned.items():
            if code not in known and unit.item is not None:
                result.append((unit.item, unit))
        return result

    def _render(self) -> None:
        clear_flow(self.flow)
        self._cards.clear()
        if not self.account:
            self.count_label.setText("尚未载入账号")
            self.more.hide()
            return
        query = self.search.text().strip().lower()
        only_owned = self.owned_toggle.isChecked()
        type_filter = int(self.type_combo.currentData() or 0)
        rows: list[tuple[CodexItem, OwnedUnit | None]] = []
        for item, owned in self._all_items():
            if only_owned and owned is None:
                continue
            if self._tier_filters:
                tier = self.tiers.tier_for(code=item.code, name=item.name)
                if tier.id not in self._tier_filters:
                    continue
            if type_filter and item.type != type_filter:
                continue
            if query and query not in item.name.lower() and query not in item.code.lower():
                continue
            rows.append((item, owned))
        rows.sort(key=lambda pair: (
            0 if pair[1] else 1,
            -self.tiers.tier_for(code=pair[0].code, name=pair[0].name).score,
            -int(pair[1].level if pair[1] else 0),
            pair[0].name,
        ))
        total = len(rows)
        shown = rows[: self._limit]
        tier_text = " + ".join(sorted(self._tier_filters)) if self._tier_filters else "全部"
        self.count_label.setText(f"{total} 条 · {tier_text} · 显示 {len(shown)}")
        for item, owned in shown:
            tier = self.tiers.tier_for(code=item.code, name=item.name)
            if self.kind == "doll":
                subtitle = f"{type_label(item.type)} · {item.code}"
                footer = f"Lv.{owned.level} · 复制 {owned.count}" if owned else "未拥有 · 图鉴"
            elif self.kind == "fairy":
                subtitle = f"妖精 · {item.code}"
                if owned:
                    footer = (
                        f"共 {owned.count} 只 · 最高 {owned.quality}★"
                        if owned.count > 1
                        else f"Lv.{owned.level} · {owned.quality}★"
                    )
                else:
                    footer = "未拥有 · 图鉴"
            else:
                subtitle = f"融合势力 · {item.code}"
                footer = f"Lv.{owned.level} · 解析 {owned.resolution_level}" if owned else "未拥有 · 图鉴"
            card = UnitCard(
                name=item.name,
                subtitle=subtitle,
                tier=tier.label,
                avatar=item.avatar_path,
                owned=owned is not None,
                footer=footer,
                letter=item.name[:2],
            )
            card.set_payload((item, owned))
            card.clicked.connect(self._open_detail)
            self.flow.addWidget(card)
            self._cards.append(card)
        self.more.setVisible(total > len(shown))
        if total > len(shown):
            self.more.setText(f"加载更多（剩余 {total - len(shown)}）")
        else:
            self.more.hide()
        if self._grid_anim is not None:
            self._grid_anim.stop()
            self._grid_anim = None
        self.canvas.setGraphicsEffect(None)
        self._grid_anim = fade_in(self.canvas, 140, 0.45)
        self._grid_anim.finished.connect(self._clear_grid_animation)

    def _clear_grid_animation(self) -> None:
        self._grid_anim = None

    def _load_more(self) -> None:
        self._limit += 120
        self._render()

    def _open_detail(self, payload) -> None:
        if not payload:
            return
        item, owned = payload
        tier = self.tiers.tier_for(code=item.code, name=item.name)
        if owned:
            detail = _copy_detail_html(owned, self.kind, "账号快照逐条记录")
        else:
            detail = (
                "<div style='color:#5F7590;font-size:12px;line-height:1.6'>"
                "图鉴单位，当前账号尚未拥有。"
                f"<br><br>{html.escape(self.tiers.note)}</div>"
            )
        dialog = UnitDetailDialog(self)
        dialog.show_unit(item.name, item.code, tier.label, f"{self.tiers.title} · {tier.name}", item.avatar_path, detail)
        dialog.exec()


class DollPage(UnitPage):
    def __init__(self, parent: QWidget | None = None):
        super().__init__("doll", parent)


class FairyPage(UnitPage):
    def __init__(self, parent: QWidget | None = None):
        super().__init__("fairy", parent)


class SangvisPage(UnitPage):
    def __init__(self, parent: QWidget | None = None):
        super().__init__("sangvis", parent)
