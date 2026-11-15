"""Dashboard / overview page."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.ratings import DimensionRating, Evaluation
from .theme import BORDER, GOLD, GREEN, MUTED, ORANGE, RED, TEXT, TEXT_SOFT, TIER_COLORS
from .widgets import AvatarLabel, RadarChart, TierBadge, TierBars, rgba


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


class HeroCard(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("HeroCard")
        self.setMinimumHeight(214)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        eyebrow = QLabel("ACCOUNT OVERVIEW")
        eyebrow.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: 700; letter-spacing: 2px;")
        top.addWidget(eyebrow)
        top.addStretch(1)
        self.source_label = QLabel()
        self.source_label.setStyleSheet(
            f"color: {MUTED}; background: #E8F1FB; border: 1px solid {BORDER};"
            "border-radius: 8px; padding: 3px 8px; font-size: 11px;"
        )
        top.addWidget(self.source_label)
        layout.addLayout(top)

        self.nickname = QLabel("未载入账号")
        self.nickname.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        layout.addWidget(self.nickname)

        self.meta = QLabel("UID — · 尚未读取快照")
        self.meta.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        layout.addWidget(self.meta)

        score_row = QHBoxLayout()
        score_row.setSpacing(14)
        self.score = QLabel("—")
        self.score.setStyleSheet(f"color: {TEXT}; font-size: 60px; font-weight: 800;")
        self.score.setAlignment(Qt.AlignBottom)
        score_row.addWidget(self.score)
        grade_box = QVBoxLayout()
        grade_box.setSpacing(0)
        self.grade = QLabel("—")
        self.grade.setStyleSheet(f"color: {GOLD}; font-size: 32px; font-weight: 800;")
        grade_box.addWidget(self.grade)
        self.grade_hint = QLabel("四维综合评分")
        self.grade_hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        grade_box.addWidget(self.grade_hint)
        score_row.addLayout(grade_box)
        score_row.addStretch(1)
        layout.addLayout(score_row)

        self.tip = QLabel("把游戏账号快照拖进来，或点击右上角「提取账号」。")
        self.tip.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        self.tip.setWordWrap(True)
        layout.addWidget(self.tip)

        self.avatar_row = QHBoxLayout()
        self.avatar_row.setSpacing(6)
        layout.addLayout(self.avatar_row)

    def refresh(self, evaluation: Evaluation) -> None:
        account = evaluation.account
        self.source_label.setText(account.source or "本地快照")
        self.nickname.setText(account.nickname)
        captured = account.captured_at.replace("T", " ")[:19] if account.captured_at else "时间未知"
        level = f"Lv.{account.level}" if account.level else "Lv.—"
        self.meta.setText(f"{level}  ·  UID {account.uid}  ·  {captured}  ·  {len(account.dolls)} 人形 / {len(account.fairies)} 妖精 / {len(account.sangvis)} 融合势力 / {len(account.vehicles)} 载具")
        self.score.setText(f"{evaluation.overall_score:.0f}")
        self.grade.setText(evaluation.overall_grade)
        self.grade_hint.setText(f"四维综合 · {grade_hint(evaluation.overall_score)}")
        self.tip.setText(
            "评分按人形 40% / 妖精 20% / 融合势力 20% / 装备 20% 加权；"
            "点击左侧页面查看每个维度的明细。"
        )
        clear_layout(self.avatar_row)
        picked = []
        seen = set()
        for unit in evaluation.doll.top_units:
            if unit.code in seen:
                continue
            seen.add(unit.code)
            picked.append(unit)
            if len(picked) >= 6:
                break
        for unit in picked:
            avatar = AvatarLabel(38, unit.name[:2])
            avatar.set_avatar(unit.avatar_path, unit.name[:2])
            avatar.setToolTip(f"{unit.name} · {unit.tier_label}")
            self.avatar_row.addWidget(avatar)
        self.avatar_row.addStretch(1)


def grade_hint(score: float) -> str:
    if score >= 90:
        return "顶级"
    if score >= 80:
        return "优秀"
    if score >= 70:
        return "良好"
    if score >= 60:
        return "及格"
    return "待补强"


class DimensionCard(QFrame):
    navigate = Signal(str)

    def __init__(self, key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("DimCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(208)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        head = QHBoxLayout()
        self.title = QLabel()
        self.title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 600;")
        head.addWidget(self.title)
        head.addStretch(1)
        self.badge = TierBadge("C")
        head.addWidget(self.badge)
        layout.addLayout(head)

        self.subtitle = QLabel()
        self.subtitle.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(self.subtitle)

        score_row = QHBoxLayout()
        self.score = QLabel("—")
        self.score.setStyleSheet(f"color: {TEXT}; font-size: 30px; font-weight: 700;")
        score_row.addWidget(self.score)
        self.unit = QLabel("/ 100")
        self.unit.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        self.unit.setAlignment(Qt.AlignBottom)
        score_row.addWidget(self.unit)
        score_row.addStretch(1)
        layout.addLayout(score_row)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(5)
        layout.addWidget(self.bar)

        self.bars = TierBars()
        self.bars.setMinimumHeight(96)
        layout.addWidget(self.bars)

        self.summary = QLabel()
        self.summary.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addStretch(1)

    def refresh(self, rating: DimensionRating) -> None:
        self.title.setText(rating.title)
        self.subtitle.setText(rating.subtitle)
        self.badge.set_tier(rating.grade)
        self.score.setText(f"{rating.score:.0f}")
        self.bar.setValue(int(max(0, min(100, rating.score))))
        self.bar.setStyleSheet(
            f"QProgressBar {{ background: #E8F1FB; border: none; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background: {GOLD}; border-radius: 2px; }}"
        )
        if rating.key == "equipment":
            data = [
                ("达标", rating.counts.get("ok", 0), GREEN),
                ("接近", rating.counts.get("warn", 0), ORANGE),
                ("缺口", rating.counts.get("low", 0), RED),
            ]
        else:
            data = [
                (tier, rating.counts.get(tier, 0), TIER_COLORS.get(tier, MUTED))
                for tier in ("SS", "S", "A-", "B", "C", "Sp")
                if tier in rating.counts
            ]
        self.bars.set_data(data)
        self.summary.setText(rating.summary)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.navigate.emit(self.key)
        super().mouseReleaseEvent(event)


class DashboardPage(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 20, 28, 26)
        layout.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(14)
        self.hero = HeroCard()
        top.addWidget(self.hero, 3)
        radar_panel = QFrame()
        radar_panel.setObjectName("Panel")
        radar_layout = QVBoxLayout(radar_panel)
        radar_layout.setContentsMargins(16, 14, 16, 12)
        radar_title = QLabel("四维雷达")
        radar_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        radar_layout.addWidget(radar_title)
        radar_sub = QLabel("人形 / 妖精 / 融合势力 / 装备")
        radar_sub.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        radar_layout.addWidget(radar_sub)
        self.radar = RadarChart()
        radar_layout.addWidget(self.radar, 1)
        top.addWidget(radar_panel, 2)
        layout.addLayout(top)

        dims = QHBoxLayout()
        dims.setSpacing(12)
        self.dim_cards = {}
        for key in ("doll", "fairy", "sangvis", "equipment"):
            card = DimensionCard(key)
            card.navigate.connect(self.navigate)
            dims.addWidget(card, 1)
            self.dim_cards[key] = card
        layout.addLayout(dims)

        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        tips_panel = QFrame()
        tips_panel.setObjectName("Panel")
        tips_layout = QVBoxLayout(tips_panel)
        tips_layout.setContentsMargins(18, 15, 18, 16)
        tips_title = QLabel("下一步建议")
        tips_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        tips_layout.addWidget(tips_title)
        tips_sub = QLabel("按四维评分自动生成，优先补短板")
        tips_sub.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        tips_layout.addWidget(tips_sub)
        self.tips_box = QVBoxLayout()
        self.tips_box.setSpacing(9)
        tips_layout.addLayout(self.tips_box)
        tips_layout.addStretch(1)
        bottom.addWidget(tips_panel, 3)

        gaps_panel = QFrame()
        gaps_panel.setObjectName("Panel")
        gaps_layout = QVBoxLayout(gaps_panel)
        gaps_layout.setContentsMargins(18, 15, 18, 16)
        gaps_title = QLabel("装备缺口")
        gaps_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        gaps_layout.addWidget(gaps_title)
        gaps_sub = QLabel("目标来自「装备需求一图流」")
        gaps_sub.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        gaps_layout.addWidget(gaps_sub)
        self.gaps_box = QVBoxLayout()
        self.gaps_box.setSpacing(9)
        gaps_layout.addLayout(self.gaps_box)
        gaps_layout.addStretch(1)
        bottom.addWidget(gaps_panel, 2)
        layout.addLayout(bottom)
        layout.addStretch(1)

    def refresh(self, evaluation: Evaluation) -> None:
        self.hero.refresh(evaluation)
        self.radar.set_data(
            [
                ("人形", evaluation.doll.score),
                ("妖精", evaluation.fairy.score),
                ("融合", evaluation.sangvis.score),
                ("装备", evaluation.equipment.score),
            ]
        )
        for key, card in self.dim_cards.items():
            card.refresh(getattr(evaluation, key))
        clear_layout(self.tips_box)
        for tip in evaluation.recommendations:
            row = QHBoxLayout()
            row.setSpacing(8)
            bullet = QLabel("•")
            bullet.setStyleSheet(f"color: {GOLD}; font-size: 13px;")
            bullet.setFixedWidth(12)
            row.addWidget(bullet, 0, Qt.AlignTop)
            label = QLabel(tip)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 12px;")
            row.addWidget(label, 1)
            self.tips_box.addLayout(row)

        clear_layout(self.gaps_box)
        for item in evaluation.equipment_gaps[:5]:
            row = QHBoxLayout()
            row.setSpacing(8)
            name = QLabel(item.name)
            name.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
            name.setFixedWidth(52)
            row.addWidget(name)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(item.pct))
            bar.setTextVisible(False)
            bar.setFixedHeight(5)
            color = RED if item.state == "low" else ORANGE if item.state == "warn" else GREEN
            bar.setStyleSheet(
                f"QProgressBar {{ background: #E8F1FB; border: none; border-radius: 2px; }}"
                f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}"
            )
            row.addWidget(bar, 1)
            value = QLabel(f"{item.current}/{item.target}")
            value.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            value.setFixedWidth(44)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(value)
            self.gaps_box.addLayout(row)


class Dashboard(QWidget):
    pass
