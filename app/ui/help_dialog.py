"""In-app user guide dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ..core.paths import HELP_FILE
from .theme import BORDER, GOLD, PANEL, TEXT, TEXT_SOFT


class HelpDialog(QDialog):
    """Render HELP.md without leaving the desktop app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用帮助 · Gf1_AccountEval")
        self.resize(980, 780)
        self.setMinimumSize(720, 560)
        self.setStyleSheet(f"QDialog {{ background: {PANEL}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet(
            f"QTextBrowser {{ background: #FFFFFF; color: {TEXT_SOFT};"
            f" border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        browser.document().setDocumentMargin(18)
        browser.document().setDefaultStyleSheet(
            f"""
            body {{ color: {TEXT_SOFT}; font-size: 13px; }}
            h1 {{ color: {TEXT}; font-size: 24px; margin: 4px 0 12px; }}
            h2 {{ color: {TEXT}; font-size: 19px; margin: 22px 0 8px; }}
            h3 {{ color: {TEXT}; font-size: 15px; margin: 16px 0 6px; }}
            h4 {{ color: {TEXT}; font-size: 13px; margin: 12px 0 4px; }}
            p, li {{ color: {TEXT_SOFT}; font-size: 13px; }}
            code {{ background: #EEF5FF; color: #1D4F91; padding: 1px 4px; }}
            pre {{ background: #F4F8FD; color: #22384F; padding: 10px;
                   border: 1px solid {BORDER}; border-radius: 6px; }}
            a {{ color: #1D6FD1; }}
            blockquote {{ color: {TEXT_SOFT}; border-left: 3px solid {GOLD};
                          margin: 8px 0; padding: 4px 12px; background: #FBFDFF; }}
            table {{ border-collapse: collapse; }}
            th, td {{ border: 1px solid {BORDER}; padding: 5px 8px; }}
            th {{ background: #EEF5FF; color: {TEXT}; }}
            """
        )

        if HELP_FILE.is_file():
            browser.setMarkdown(HELP_FILE.read_text(encoding="utf-8"))
        else:
            browser.setPlainText(
                "帮助文档缺失：HELP.md\n\n"
                "请确认项目根目录下存在 HELP.md，或查看 README.md / USAGE.md。"
            )
        browser.verticalScrollBar().setValue(0)
        layout.addWidget(browser, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        hint = QPushButton("F1 可随时打开本帮助")
        hint.setObjectName("Ghost")
        hint.setFlat(True)
        hint.setEnabled(False)
        hint.setStyleSheet(f"QPushButton {{ color: {TEXT_SOFT}; border: none; }}")
        footer.addWidget(hint)
        footer.addStretch(1)
        close_button = QPushButton("关闭")
        close_button.setObjectName("Primary")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        layout.addLayout(footer)
