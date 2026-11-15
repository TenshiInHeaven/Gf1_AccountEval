"""GF Account Forge entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .core.paths import ASSETS_DIR
from .state import AppState
from .ui.main_window import MainWindow
from .ui.theme import apply_theme


def main() -> int:
    # Qt 6.12 no longer ships fonts; point it at the Windows font directory so
    # the font database is populated before QApplication starts.
    if sys.platform == "win32":
        windows_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        if windows_fonts.is_dir():
            os.environ.setdefault("QT_QPA_FONTDIR", str(windows_fonts))

    QCoreApplication.setOrganizationName("GFForge")
    QCoreApplication.setApplicationName("GF Account Forge")
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("GF Account Forge")
    apply_theme(app)
    icon_path = ASSETS_DIR / "app_icon.png"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    state = AppState()
    window = MainWindow(state)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
