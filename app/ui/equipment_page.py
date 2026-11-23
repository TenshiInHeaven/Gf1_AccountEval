"""Equipment target page."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.equipment import EquipmentCategory, EquipmentEngine, EquipmentReport, EquipmentTarget, get_equipment_engine
from ..core.paths import DATA_DIR, read_json
from ..core.ratings import Evaluation, grade_for
from .dashboard import clear_layout
from .theme import BORDER, GOLD, GREEN, MUTED, ORANGE, RED, TEXT, TEXT_SOFT
from .widgets import ProgressLine, TierBadge


def state_color(target: EquipmentTarget) -> str:
    return {"ok": GREEN, "warn": ORANGE, "low": RED}.get(target.state, MUTED)


class EquipmentPage(QWidget):
    def __init__(self, state=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.evaluation: Evaluation | None = None
        self.raw_rows: list[dict] = []
        self.activities = (read_json(DATA_DIR / "equipment_activities.json", {}) or {}).get("activities") or []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)
        canvas = QWidget()
        scroll.setWidget(canvas)
        self.layout = QVBoxLayout(canvas)
        self.layout.setContentsMargins(28, 20, 28, 26)
        self.layout.setSpacing(14)

        self.summary = QFrame()
        self.summary.setObjectName("HeroCard")
        summary_layout = QHBoxLayout(self.summary)
        summary_layout.setContentsMargins(24, 18, 24, 18)
        summary_layout.setSpacing(20)
        left = QVBoxLayout()
        left.setSpacing(3)
        eyebrow = QLabel("EQUIPMENT RESERVE")
        eyebrow.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: 700; letter-spacing: 2px;")
        left.addWidget(eyebrow)
        self.title = QLabel("装备储备")
        self.title.setStyleSheet(f"color: {TEXT}; font-size: 24px; font-weight: 700;")
        left.addWidget(self.title)
        self.subtitle = QLabel("按「装备需求一图流」比较目标个数与当前个数")
        self.subtitle.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        left.addWidget(self.subtitle)
        activity_row = QHBoxLayout()
        activity_row.setSpacing(6)
        activity_label = QLabel("评价范围")
        activity_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        activity_row.addWidget(activity_label)
        self.activity_combo = QComboBox()
        self.activity_combo.addItem("全量最大（所有活动取并集）", "")
        for activity in self.activities:
            suffix = "" if activity.get("available", True) else "（无数据）"
            self.activity_combo.addItem(str(activity.get("name") or activity.get("id")) + suffix, activity.get("id"))
        self.activity_combo.currentIndexChanged.connect(self._update_activity)
        activity_row.addWidget(self.activity_combo)
        activity_row.addStretch(1)
        left.addLayout(activity_row)
        self.rules_button = QPushButton("调整对应规则")
        self.rules_button.setObjectName("Ghost")
        self.rules_button.clicked.connect(self._open_rules)
        left.addWidget(self.rules_button, 0, Qt.AlignLeft)
        left.addStretch(1)
        summary_layout.addLayout(left, 3)

        score_box = QVBoxLayout()
        score_box.setSpacing(0)
        score_box.setAlignment(Qt.AlignCenter)
        self.score = QLabel("—")
        self.score.setStyleSheet(f"color: {TEXT}; font-size: 46px; font-weight: 800;")
        self.score.setAlignment(Qt.AlignCenter)
        score_box.addWidget(self.score)
        self.hint = QLabel("目标完成度")
        self.hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        self.hint.setAlignment(Qt.AlignCenter)
        score_box.addWidget(self.hint)
        summary_layout.addLayout(score_box, 1)

        self.grade_box = QVBoxLayout()
        self.grade_box.setSpacing(2)
        self.grade_box.setAlignment(Qt.AlignCenter)
        self.grade = TierBadge("C")
        self.grade.setFixedSize(56, 30)
        self.grade.setStyleSheet(
            self.grade.styleSheet().replace("font-size: 13px", "font-size: 18px")
        )
        self.grade_box.addWidget(self.grade, 0, Qt.AlignCenter)
        self.grade_hint = QLabel("装备评级")
        self.grade_hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        self.grade_hint.setAlignment(Qt.AlignCenter)
        self.grade_box.addWidget(self.grade_hint)
        summary_layout.addLayout(self.grade_box, 1)
        self.layout.addWidget(self.summary)

        self.categories_box = QHBoxLayout()
        self.categories_box.setSpacing(12)
        self.layout.addLayout(self.categories_box)

        self.sections = QVBoxLayout()
        self.sections.setSpacing(14)
        self.layout.addLayout(self.sections)
        self.layout.addStretch(1)

    def _open_rules(self) -> None:
        if self.state is None:
            return
        from .equipment_rules_dialog import EquipmentRulesDialog

        EquipmentRulesDialog(self.state, self).exec()

    def refresh(self, evaluation: Evaluation) -> None:
        self.evaluation = evaluation
        payload = self.state.export_payload() if self.state is not None else None
        self.raw_rows = list((payload or {}).get("equipment") or [])
        self._update_activity()

    def _update_activity(self) -> None:
        if self.evaluation is None:
            return
        report: EquipmentReport = self.evaluation.equipment.extra["report"]
        grade = self.evaluation.equipment.grade
        activity_id = str(self.activity_combo.currentData() or "")
        if activity_id:
            activity = next(
                (item for item in self.activities if item.get("id") == activity_id),
                None,
            )
            counts = dict((activity or {}).get("counts") or {})
            report = get_equipment_engine().evaluate(self.raw_rows, counts)
            grade = grade_for(report.score)
            if activity is not None and not activity.get("available", True):
                grade = "C"
                self.subtitle.setText("该活动没有可读取的配置表数据")
            else:
                self.subtitle.setText(
                    f"{activity.get('name') if activity else activity_id} · "
                    f"{report.current_total}/{report.target_total} 件 · "
                    f"完成度 {report.completion:.0f}%"
                )
        else:
            self.subtitle.setText(
                f"{report.current_total}/{report.target_total} 件 · 完成度 {report.completion:.0f}% · "
                f"{sum(1 for item in report.all_targets if item.state == 'ok')}/{len(report.all_targets)} 项达标"
            )
        self._show_report(report, grade)

    def _show_report(self, report: EquipmentReport, grade: str) -> None:
        self.score.setText(f"{report.score:.0f}")
        self.grade.set_tier(grade)
        if str(self.activity_combo.currentData() or ""):
            # Activity subtitle is set by _update_activity.
            pass
        else:
            self.subtitle.setText(
                f"{report.current_total}/{report.target_total} 件 · 完成度 {report.completion:.0f}% · "
                f"{sum(1 for item in report.all_targets if item.state == 'ok')}/{len(report.all_targets)} 项达标"
            )
        clear_layout(self.categories_box)
        for category in report.categories:
            card = QFrame()
            card.setObjectName("Panel")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(5)
            top = QHBoxLayout()
            name = QLabel(category.name)
            name.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 600;")
            top.addWidget(name)
            top.addStretch(1)
            pct = QLabel(f"{category.completion:.0f}%")
            color = GREEN if category.completion >= 100 else ORANGE if category.completion >= 70 else RED
            pct.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 700;")
            top.addWidget(pct)
            card_layout.addLayout(top)
            value = QLabel(f"{category.current_total} / {category.target_total} 目标")
            value.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            card_layout.addWidget(value)
            line = ProgressLine(category.name, "", category.completion, color)
            line.label.hide()
            line.value.hide()
            card_layout.addWidget(line)
            self.categories_box.addWidget(card, 1)

        clear_layout(self.sections)
        for category in report.categories:
            section = QFrame()
            section.setObjectName("Panel")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(18, 14, 18, 16)
            section_layout.setSpacing(10)
            head = QHBoxLayout()
            title = QLabel(f"{category.name} · {category.current_total}/{category.target_total}")
            title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
            head.addWidget(title)
            head.addStretch(1)
            weight = QLabel(f"权重 {int(category.weight * 100)}%")
            weight.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            head.addWidget(weight)
            section_layout.addLayout(head)
            for target in category.targets:
                row = QHBoxLayout()
                row.setSpacing(10)
                name = QLabel(target.name)
                name.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 12px;")
                name.setFixedWidth(64)
                row.addWidget(name)
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(int(target.pct))
                bar.setTextVisible(False)
                bar.setFixedHeight(6)
                color = state_color(target)
                bar.setStyleSheet(
                    f"QProgressBar {{ background: #E8F1FB; border: none; border-radius: 3px; }}"
                    f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}"
                )
                row.addWidget(bar, 1)
                value = QLabel(f"{target.current} / {target.target}")
                value.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
                value.setFixedWidth(58)
                value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row.addWidget(value)
                gap = QLabel(f"差 {target.gap}" if target.gap else "达标")
                gap.setStyleSheet(f"color: {MUTED if target.gap else GREEN}; font-size: 11px;")
                gap.setFixedWidth(42)
                gap.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row.addWidget(gap)
                section_layout.addLayout(row)
            self.sections.addWidget(section)
