"""Unified codex page."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.codex import get_codex
from ..core.ratings import Evaluation
from .theme import BORDER, GOLD, MUTED, PANEL_2, TEXT
from .units import DollPage, FairyPage, SangvisPage


class CodexPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.codex = get_codex()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 0)
        root.setSpacing(12)

        intro = QFrame()
        intro.setObjectName("Panel")
        intro_layout = QHBoxLayout(intro)
        intro_layout.setContentsMargins(18, 14, 18, 14)
        intro_layout.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(3)
        title = QLabel("全量图鉴")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        left.addWidget(title)
        sub = QLabel("不依赖仓库快照：所有人形 / 妖精 / 融合势力，含未拥有单位。")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        left.addWidget(sub)
        intro_layout.addLayout(left, 1)
        self.count_labels = {}
        for kind, label in (("doll", "人形"), ("fairy", "妖精"), ("sangvis", "融合势力")):
            box = QFrame()
            box.setStyleSheet(f"QFrame {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 10px; }}")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(12, 7, 12, 7)
            box_layout.setSpacing(0)
            value = QLabel()
            value.setStyleSheet(f"color: {GOLD}; font-size: 19px; font-weight: 700;")
            value.setAlignment(Qt.AlignCenter)
            box_layout.addWidget(value)
            name = QLabel(label)
            name.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            name.setAlignment(Qt.AlignCenter)
            box_layout.addWidget(name)
            self.count_labels[kind] = value
            intro_layout.addWidget(box)
        root.addWidget(intro)

        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.tab_buttons = []
        for index, (label, cls) in enumerate(
            (("人形", DollPage), ("妖精", FairyPage), ("融合势力", SangvisPage))
        ):
            button = QPushButton(label)
            button.setObjectName("Chip")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumWidth(88)
            button.clicked.connect(lambda checked=False, i=index: self._switch(i))
            self.group.addButton(button)
            tabs.addWidget(button)
            self.tab_buttons.append(button)
        tabs.addStretch(1)
        root.addLayout(tabs)

        self.stack = QStackedWidget()
        self.pages = []
        for index, cls in enumerate((DollPage, FairyPage, SangvisPage)):
            page = cls()
            page.set_owned_only(False)
            page.layout().setContentsMargins(0, 0, 0, 0)
            self.pages.append(page)
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)
        self.tab_buttons[0].setChecked(True)
        self._switch(0)

    def _switch(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.tab_buttons):
            button.setChecked(i == index)

    def refresh(self, evaluation: Evaluation) -> None:
        counts = {
            "doll": sum(
                1
                for item in self.codex.dolls
                if self.codex.is_deployable("doll", item)
                and not self.codex.is_mod_variant("doll", item.code)
            ),
            "fairy": sum(1 for item in self.codex.fairies if self.codex.is_deployable("fairy", item)),
            "sangvis": sum(1 for item in self.codex.sangvis if self.codex.is_deployable("sangvis", item)),
        }
        owned = {
            "doll": len(evaluation.account.dolls),
            "fairy": len(evaluation.account.fairies),
            "sangvis": len(evaluation.account.sangvis),
        }
        for kind in counts:
            self.count_labels[kind].setText(f"{owned[kind]}/{counts[kind]}")
        for page in self.pages:
            page.refresh(evaluation)
