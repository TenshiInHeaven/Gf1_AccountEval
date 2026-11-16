"""Visual language for the Qt app (bright white / blue)."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

BG = "#F3F8FE"
BG_SOFT = "#FFFFFF"
PANEL = "#FFFFFF"
PANEL_2 = "#F6FAFF"
PANEL_3 = "#EAF3FF"
BORDER = "#D6E4F5"
BORDER_SOFT = "#E6EFF9"
TEXT = "#15263B"
TEXT_SOFT = "#334A63"
MUTED = "#5F7590"
# Kept under the old name for compatibility across widgets; now the blue accent.
GOLD = "#2474E5"
GOLD_DARK = "#1B5FCC"
ORANGE = "#DF8A2E"
RED = "#D9534F"
GREEN = "#2E9E6B"
BLUE = "#2474E5"
PURPLE = "#6D5BD0"

TIER_COLORS = {
    "SS": "#1D4ED8",
    "S": "#2F80ED",
    "A-": "#4A86C7",
    "A": "#4A86C7",
    "B": "#2E9E8F",
    "C": "#6F8299",
    "Sp": "#6D5BD0",
}

# Card frames requested by tier.  ``GOLD`` above is the app's blue accent;
# keep a real metallic gold here so SS / crown cards do not become blue.
FRAME_GOLD = "#D4AF37"
FRAME_GREEN = GREEN
FRAME_BLUE = BLUE
FRAME_WHITE = "#FFFFFF"
FRAME_PURPLE = PURPLE
FRAME_COLORS = {
    "SS": FRAME_GOLD,
    "S": FRAME_GREEN,
    "A-": FRAME_BLUE,
    "A": FRAME_BLUE,
    "B": FRAME_WHITE,
    "C": FRAME_WHITE,
    "Sp": FRAME_PURPLE,
}

FONT_FAMILY = "Microsoft YaHei UI"


def _load_fonts() -> str:
    """Load a CJK-capable font explicitly.

    Qt 6.12 no longer ships fonts; on a bare/offscreen platform the font
    database can be empty even on Windows.  Loading the system Microsoft YaHei
    files makes screenshots and packaged builds render Chinese reliably.
    """
    candidates = (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    )
    for path in candidates:
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            for family in families:
                if family in {"Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "Segoe UI"}:
                    return family
    families = QFontDatabase.families()
    return families[0] if families else FONT_FAMILY


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    family = _load_fonts()
    font = QFont(family, 12)
    app.setFont(font)
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(PANEL))
    palette.setColor(QPalette.AlternateBase, QColor(PANEL_2))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(PANEL_2))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(BLUE))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ToolTipBase, QColor(PANEL))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET.replace(FONT_FAMILY, family))


STYLESHEET = f"""
* {{
    font-family: "{FONT_FAMILY}", "Segoe UI", sans-serif;
    outline: none;
}}
QMainWindow, QWidget#Root {{
    background: {BG};
}}
QWidget#Sidebar {{
    background: {BG_SOFT};
    border-right: 1px solid {BORDER_SOFT};
}}
QFrame#Panel, QFrame#HeroCard, QFrame#DimCard, QFrame#SoftCard {{
    background: {PANEL};
    border: 1px solid {BORDER_SOFT};
    border-radius: 16px;
}}
QFrame#HeroCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #FFFFFF, stop:0.55 #F2F8FF, stop:1 #EAF4FF);
    border: 1px solid {BORDER};
}}
QFrame#SoftCard {{
    background: {PANEL_2};
    border-radius: 12px;
}}
QLabel {{
    color: {TEXT};
    background: transparent;
}}
QLabel#BrandMark {{
    color: {GOLD};
    background: #EAF3FF;
    border: 1px solid #B9D6F7;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 800;
}}
QLabel#BrandTitle {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#BrandSub {{
    color: {MUTED};
    font-size: 12px;
}}
QLabel#PageTitle {{
    color: {TEXT};
    font-size: 26px;
    font-weight: 700;
}}
QLabel#PageSub {{
    color: {MUTED};
    font-size: 13px;
}}
QLabel#H2 {{
    color: {TEXT};
    font-size: 17px;
    font-weight: 600;
}}
QLabel#H3 {{
    color: {TEXT_SOFT};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#Muted {{
    color: {MUTED};
    font-size: 13px;
}}
QLabel#Tiny {{
    color: {MUTED};
    font-size: 11px;
}}
QLabel#Score {{
    color: {TEXT};
    font-size: 44px;
    font-weight: 800;
}}
QLabel#ScoreSmall {{
    color: {TEXT};
    font-size: 28px;
    font-weight: 700;
}}
QLabel#Grade {{
    color: {GOLD};
    font-size: 24px;
    font-weight: 800;
}}
QLabel#Accent {{
    color: {GOLD};
}}
QLabel#Green {{
    color: {GREEN};
}}
QLabel#Red {{
    color: {RED};
}}
QPushButton {{
    border: none;
    background: transparent;
    color: {TEXT_SOFT};
}}
QPushButton#Nav {{
    text-align: left;
    padding: 12px 16px;
    border-radius: 10px;
    background: transparent;
    font-size: 14px;
    color: {MUTED};
}}
QPushButton#Nav:hover {{
    background: #F0F7FF;
    color: {TEXT};
}}
QPushButton#Nav:checked {{
    background: transparent;
    color: #0F4C9C;
    border-left: none;
}}
QPushButton#Primary {{
    background: {GOLD};
    color: #FFFFFF;
    font-weight: 700;
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 14px;
}}
QPushButton#Primary:hover {{
    background: #3B8DF2;
}}
QPushButton#Primary:pressed {{
    background: {GOLD_DARK};
}}
QPushButton#Ghost {{
    background: {PANEL_2};
    color: {TEXT_SOFT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 9px 16px;
    font-size: 14px;
}}
QPushButton#Ghost:hover {{
    background: {PANEL_3};
    color: {TEXT};
    border-color: #B9D6F7;
}}
QPushButton#Chip {{
    background: transparent;
    color: {MUTED};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 6px 12px;
    font-size: 13px;
}}
QPushButton#Chip:hover {{
    color: {TEXT};
    border-color: #B9D6F7;
    background: #F5FAFF;
}}
QPushButton#Chip:checked {{
    background: #D8E9FF;
    color: #0F4C9C;
    border-color: #8FB8EA;
}}
QLineEdit {{
    background: #FBFDFF;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 9px 12px;
    selection-background-color: {GOLD};
    selection-color: #FFFFFF;
}}
QLineEdit:focus {{
    border-color: #8FB8EA;
    background: #FFFFFF;
}}
QComboBox {{
    background: #FBFDFF;
    color: {TEXT_SOFT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px 12px;
    min-width: 90px;
}}
QComboBox:hover {{
    border-color: #B9D6F7;
}}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: #E7F1FF;
    selection-color: {TEXT};
    padding: 4px;
}}
QCheckBox {{
    color: {MUTED};
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #B9CFE8;
    background: #FFFFFF;
}}
QCheckBox::indicator:checked {{
    background: {GOLD};
    border-color: {GOLD};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #C6D9EE;
    border-radius: 4px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A8C5E3;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QProgressBar {{
    background: #E8F1FB;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 3px;
    background: {GOLD};
}}
QToolTip {{
    background: #FFFFFF;
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px 8px;
    border-radius: 6px;
}}
QDialog {{
    background: {BG};
}}
"""
