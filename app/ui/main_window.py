"""Main window and navigation shell."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, QSize, Qt
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import ASSETS_DIR, SAMPLE_ACCOUNT
from ..state import AppState
from .capture_dialog import CaptureDialog
from .codex_page import CodexPage
from .dashboard import DashboardPage
from .equipment_page import EquipmentPage
from .help_dialog import HelpDialog
from .settings_page import SettingsPage
from .theme import BG, BG_SOFT, BORDER, GOLD, MUTED, PANEL, PANEL_2, TEXT, TEXT_SOFT
from .units import DollPage, FairyPage, SangvisPage
from .widgets import AvatarLabel, rgba


class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(f"  {icon}    {label}")
        self.setObjectName("Nav")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)


class MainWindow(QMainWindow):
    PAGES = (
        ("dashboard", "总览", "四维评分与下一步建议", "01"),
        ("dolls", "人形", "仓库人形 / 三体人与常用好手", "02"),
        ("fairies", "妖精", "空降与战略妖精储备", "03"),
        ("sangvis", "融合势力", "铁血捕获单位", "04"),
        ("equipment", "装备", "目标个数 vs 当前个数", "05"),
        ("codex", "图鉴", "全量单位与拥有状态", "06"),
        ("settings", "设置", "数据来源与评分口径", "07"),
    )

    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._page_anim: QPropertyAnimation | None = None
        self.setWindowTitle("GF Account Forge · 少前账号强度工坊")
        icon_path = ASSETS_DIR / "app_icon.png"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1480, 930)
        self.setMinimumSize(1180, 760)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_main(), 1)

        self.state.account_changed.connect(self._on_account_changed)
        self.state.error.connect(self._on_error)
        self.state.notice.connect(self._on_notice)
        self.help_shortcut = QShortcut(QKeySequence("F1"), self)
        self.help_shortcut.activated.connect(self.open_help)
        self._load_initial()
        QTimer.singleShot(0, self._init_nav_indicator)

    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(238)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 22, 16, 18)
        layout.setSpacing(6)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = QLabel("GF")
        mark.setFixedSize(44, 44)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(
            f"QLabel {{ color: {GOLD}; background: #EAF3FF; border: 1px solid {GOLD};"
            "border-radius: 12px; font-size: 18px; font-weight: 800; }"
        )
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        title = QLabel("ACCOUNT FORGE")
        title.setObjectName("BrandTitle")
        brand_text.addWidget(title)
        sub = QLabel("少前账号强度工坊")
        sub.setObjectName("BrandSub")
        brand_text.addWidget(sub)
        brand.addLayout(brand_text)
        brand.addStretch(1)
        layout.addLayout(brand)
        layout.addSpacing(18)

        self.nav_buttons: dict[str, NavButton] = {}
        for key, label, _subtitle, icon in self.PAGES:
            button = NavButton(icon, label)
            button.clicked.connect(lambda checked=False, page=key: self.show_page(page))
            layout.addWidget(button)
            self.nav_buttons[key] = button
        self.nav_indicator = QFrame(sidebar)
        self.nav_indicator.setFixedWidth(3)
        self.nav_indicator.setStyleSheet(f"background: {GOLD}; border-radius: 1px;")
        self.nav_indicator.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.nav_indicator.raise_()
        self.nav_indicator_anim: QPropertyAnimation | None = None
        self.nav_indicator_ready = False
        layout.addSpacing(10)
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {BORDER};")
        layout.addWidget(separator)
        layout.addSpacing(10)

        account_card = QFrame()
        account_card.setStyleSheet(
            f"QFrame {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; }}"
        )
        account_layout = QVBoxLayout(account_card)
        account_layout.setContentsMargins(12, 10, 12, 10)
        account_layout.setSpacing(4)
        top = QHBoxLayout()
        self.side_avatar = AvatarLabel(30, "GF")
        top.addWidget(self.side_avatar)
        names = QVBoxLayout()
        names.setSpacing(0)
        self.side_name = QLabel("未载入账号")
        self.side_name.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 600;")
        names.addWidget(self.side_name)
        self.side_uid = QLabel("—")
        self.side_uid.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        names.addWidget(self.side_uid)
        top.addLayout(names, 1)
        account_layout.addLayout(top)
        self.side_meta = QLabel("等待快照")
        self.side_meta.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self.side_meta.setWordWrap(True)
        account_layout.addWidget(self.side_meta)
        layout.addWidget(account_card)

        layout.addStretch(1)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        version = QLabel("v0.1 · local-first")
        version.setStyleSheet(f"color: #8A9CB3; font-size: 10px;")
        layout.addWidget(version)
        return sidebar

    def _build_main(self) -> QWidget:
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(f"QFrame {{ background: {BG_SOFT}; border-bottom: 1px solid {BORDER}; }}")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 16, 28, 16)
        header_layout.setSpacing(12)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.page_title = QLabel("总览")
        self.page_title.setObjectName("PageTitle")
        titles.addWidget(self.page_title)
        self.page_subtitle = QLabel("四维评分与下一步建议")
        self.page_subtitle.setObjectName("PageSub")
        titles.addWidget(self.page_subtitle)
        header_layout.addLayout(titles, 1)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setObjectName("Ghost")
        self.refresh_button.clicked.connect(self._refresh_current)
        header_layout.addWidget(self.refresh_button)
        self.import_button = QPushButton("导入快照")
        self.import_button.setObjectName("Ghost")
        self.import_button.clicked.connect(self.open_capture)
        header_layout.addWidget(self.import_button)
        self.capture_button = QPushButton("提取账号")
        self.capture_button.setObjectName("Primary")
        self.capture_button.clicked.connect(self.open_capture)
        header_layout.addWidget(self.capture_button)
        self.help_button = QPushButton("帮助")
        self.help_button.setObjectName("Ghost")
        self.help_button.setToolTip("操作帮助：正常流程 / Android 抓包 / PWA（F1）")
        self.help_button.clicked.connect(self.open_help)
        header_layout.addWidget(self.help_button)
        layout.addWidget(header)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.dashboard.navigate.connect(self.show_page)
        self.dolls = DollPage()
        self.fairies = FairyPage()
        self.sangvis = SangvisPage()
        self.equipment = EquipmentPage()
        self.codex = CodexPage()
        self.settings = SettingsPage(self.state)
        self.pages = {
            "dashboard": self.dashboard,
            "dolls": self.dolls,
            "fairies": self.fairies,
            "sangvis": self.sangvis,
            "equipment": self.equipment,
            "codex": self.codex,
            "settings": self.settings,
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)
        return main

    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        if key not in self.pages:
            return
        target = self.pages[key]
        if self.stack.currentWidget() is not target:
            if self._page_anim is not None:
                self._page_anim.stop()
                self._page_anim = None
            for page in self.pages.values():
                page.setGraphicsEffect(None)
            effect = QGraphicsOpacityEffect(target)
            effect.setOpacity(0.0)
            target.setGraphicsEffect(effect)
            self.stack.setCurrentWidget(target)
            animation = QPropertyAnimation(effect, b"opacity", self)
            animation.setDuration(260)
            animation.setStartValue(0.12)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            animation.finished.connect(lambda: target.setGraphicsEffect(None))
            animation.finished.connect(self._clear_page_animation)
            animation.start()
            self._page_anim = animation
        for name, button in self.nav_buttons.items():
            button.setChecked(name == key)
        self._move_nav_indicator(key)
        for name, label, subtitle, _icon in self.PAGES:
            if name == key:
                self.page_title.setText(label)
                self.page_subtitle.setText(subtitle)
                break

    def _init_nav_indicator(self) -> None:
        self.nav_indicator_ready = True
        current = next(
            (name for name, button in self.nav_buttons.items() if button.isChecked()),
            "dashboard",
        )
        self._move_nav_indicator(current, animate=False)

    def _move_nav_indicator(self, key: str, animate: bool = True) -> None:
        if not getattr(self, "nav_indicator_ready", False):
            return
        button = self.nav_buttons.get(key)
        if button is None:
            return
        target = QRect(
            button.geometry().left() + 5,
            button.geometry().top() + 8,
            3,
            max(8, button.height() - 16),
        )
        if not animate or self.nav_indicator.geometry() == target:
            self.nav_indicator.setGeometry(target)
            return
        if self.nav_indicator_anim is not None:
            self.nav_indicator_anim.stop()
        animation = QPropertyAnimation(self.nav_indicator, b"geometry", self)
        animation.setDuration(220)
        animation.setStartValue(self.nav_indicator.geometry())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()
        self.nav_indicator_anim = animation

    def open_capture(self) -> None:
        dialog = CaptureDialog(self.state, self)
        dialog.exec()

    def open_help(self) -> None:
        dialog = HelpDialog(self)
        dialog.exec()

    def _clear_page_animation(self) -> None:
        self._page_anim = None

    def _load_initial(self) -> None:
        last = self.state.last_path()
        if last and self.state.load_path(last, announce=False):
            self.show_page("dashboard")
            self.status_label.setText("已载入上次快照")
            return
        if self.state.load_sample(announce=False):
            self.show_page("dashboard")
            self.status_label.setText("示例数据 · 点击「提取账号」读取游戏")
            return
        self.status_label.setText("未载入账号")

    def _on_account_changed(self, evaluation) -> None:
        account = evaluation.account
        self.side_name.setText(account.nickname)
        level = f"Lv.{account.level}" if account.level else "Lv.—"
        self.side_uid.setText(f"UID {account.uid} · {level}")
        self.side_meta.setText(
            f"{len(account.dolls)} 人形 · {len(account.fairies)} 妖精 · "
            f"{len(account.sangvis)} 融合势力"
        )
        self.side_avatar.set_avatar(None, account.nickname[:2] if account.nickname else "GF")
        self.dashboard.refresh(evaluation)
        self.dolls.refresh(evaluation)
        self.fairies.refresh(evaluation)
        self.sangvis.refresh(evaluation)
        self.equipment.refresh(evaluation)
        self.codex.refresh(evaluation)
        self.settings.refresh(evaluation)
        self.status_label.setText(f"评分 {evaluation.overall_score:.1f} · {evaluation.overall_grade}")

    def _on_error(self, message: str) -> None:
        self.status_label.setText("发生错误")
        QMessageBox.critical(self, "操作失败", message)

    def _on_notice(self, message: str) -> None:
        self.status_label.setText(message)

    def _refresh_current(self) -> None:
        if self.state.evaluation:
            self._on_account_changed(self.state.evaluation)
