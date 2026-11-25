"""In-app user guide dialog with tabs and a collapsible table of contents."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import HELP_FILE
from .theme import BORDER, GOLD, PANEL, PANEL_2, TEXT, TEXT_SOFT


@dataclass
class HelpNode:
    title: str
    level: int
    body: str = ""
    children: list["HelpNode"] = field(default_factory=list)

    def render(self) -> str:
        parts = [f"{'#' * self.level} {self.title}"]
        if self.body.strip():
            parts.append(self.body.strip())
        for child in self.children:
            parts.append(child.render())
        return "\n\n".join(parts)


TAB_LABELS = ("PC 使用", "Android 抓取", "常见问题", "数据与隐私", "相关文件")


def _clean_title(title: str) -> str:
    return re.sub(r"^[一二三四五六七八九十]+、\s*", "", title).strip()


def parse_help(text: str) -> list[HelpNode]:
    root = HelpNode("", 0)
    stack = [root]
    current: HelpNode | None = None
    for line in text.splitlines():
        match = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if match:
            level = len(match.group(1))
            while len(stack) > 1 and stack[-1].level >= level:
                stack.pop()
            node = HelpNode(match.group(2).strip(), level)
            stack[-1].children.append(node)
            stack.append(node)
            current = node
            continue
        if current is not None:
            current.body += line + "\n"
    # The document starts with H1, then the H2 tabs.
    h1 = root.children[0] if root.children else root
    return [node for node in h1.children if node.level == 2]


class HelpTab(QWidget):
    """One tab: collapsible TOC on the left, rendered section on the right."""

    def __init__(self, section: HelpNode, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setMinimumWidth(200)
        self.tree.setMaximumWidth(300)
        self.tree.setStyleSheet(
            f"QTreeWidget {{ background: {PANEL_2}; color: {TEXT_SOFT};"
            f" border: 1px solid {BORDER}; border-radius: 8px; padding: 6px; }}"
            f"QTreeWidget::item {{ padding: 6px 4px; border-radius: 5px; }}"
            f"QTreeWidget::item:selected {{ background: #E7F1FF; color: #1D4F91; }}"
        )
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet(
            f"QTextBrowser {{ background: #FFFFFF; color: {TEXT_SOFT};"
            f" border: 1px solid {BORDER}; border-radius: 8px; }}"
        )
        self.browser.document().setDocumentMargin(16)
        self.browser.document().setDefaultStyleSheet(
            f"""
            body {{ color: {TEXT_SOFT}; font-size: 13px; }}
            h1 {{ color: {TEXT}; font-size: 24px; margin: 4px 0 12px; }}
            h2 {{ color: {TEXT}; font-size: 20px; margin: 18px 0 8px; }}
            h3 {{ color: {TEXT}; font-size: 16px; margin: 14px 0 6px; }}
            h4 {{ color: {TEXT}; font-size: 14px; margin: 12px 0 4px; }}
            h5 {{ color: {TEXT}; font-size: 13px; margin: 10px 0 4px; }}
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

        root_item = QTreeWidgetItem([_clean_title(section.title) or "本页"])
        root_item.setData(0, Qt.UserRole, section)
        root_item.setToolTip(0, section.title)
        self.tree.addTopLevelItem(root_item)
        for child in section.children:
            self._add_item(root_item, child)
        root_item.setExpanded(True)
        self.tree.setCurrentItem(root_item)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemActivated.connect(self._on_item_clicked)
        self._select_section(section)

        splitter.addWidget(self.tree)
        splitter.addWidget(self.browser)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([230, 720])
        layout.addWidget(splitter, 1)

    def _add_item(self, parent: QTreeWidgetItem, node: HelpNode) -> None:
        item = QTreeWidgetItem([_clean_title(node.title) or node.title])
        item.setData(0, Qt.UserRole, node)
        item.setToolTip(0, node.title)
        parent.addChild(item)
        for child in node.children:
            self._add_item(item, child)
        if node.children:
            item.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        node = item.data(0, Qt.UserRole)
        if isinstance(node, HelpNode):
            self._select_section(node)

    def _select_section(self, node: HelpNode) -> None:
        self.browser.setMarkdown(node.render())
        self.browser.verticalScrollBar().setValue(0)


class HelpDialog(QDialog):
    """Tabbed help window with a collapsible section tree."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用帮助 · Gf1_AccountEval")
        self.resize(1080, 800)
        self.setMinimumSize(820, 600)
        self.setStyleSheet(f"QDialog {{ background: {PANEL}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("使用帮助")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        titles.addWidget(title)
        subtitle = QLabel("左侧目录可折叠，点击跳转；F1 可随时打开")
        subtitle.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 11px;")
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px;"
            f" background: {PANEL}; top: -1px; }}"
            f"QTabBar::tab {{ background: transparent; color: {TEXT_SOFT};"
            f" padding: 8px 18px; border: none; border-bottom: 2px solid transparent; }}"
            f"QTabBar::tab:selected {{ color: #1D4F91; border-bottom: 2px solid {GOLD};"
            f" font-weight: 600; }}"
            f"QTabBar::tab:hover {{ color: {TEXT}; }}"
        )
        sections = []
        if HELP_FILE.is_file():
            sections = parse_help(HELP_FILE.read_text(encoding="utf-8"))
        if not sections:
            empty = QTextBrowser()
            empty.setPlainText(
                "帮助文档缺失：docs/HELP.md\n\n请确认项目 docs 目录下存在 HELP.md，或查看 README.md / docs/USAGE.md。"
            )
            self.tabs.addTab(empty, "帮助")
        else:
            for index, section in enumerate(sections):
                label = TAB_LABELS[index] if index < len(TAB_LABELS) else _clean_title(section.title)
                self.tabs.addTab(HelpTab(section), label)
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        hint = QLabel("提示：左侧目录支持展开 / 收起，点击子项可跳到对应步骤。")
        hint.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 10px;")
        footer.addWidget(hint)
        footer.addStretch(1)
        close_button = QPushButton("关闭")
        close_button.setObjectName("Primary")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        layout.addLayout(footer)
