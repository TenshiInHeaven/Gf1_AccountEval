"""Reusable widgets: flow layout, avatars, cards, charts."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import BORDER, FRAME_GOLD, GOLD, MUTED, PANEL_2, TEXT, TIER_COLORS, TIER_TEXT_COLORS


def rgba(hex_color: str, alpha: int) -> str:
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


class FlowLayout(QLayout):
    """A responsive left-to-right wrapping layout (Qt example, adapted)."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, h_spacing: int = 12, v_spacing: int = 12):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0
        for item in self._items:
            widget = item.widget()
            if widget is None or widget.isHidden():
                continue
            space_x = self._h_spacing
            space_y = self._v_spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y() + margins.bottom()


@lru_cache(maxsize=1024)
def _load_pixmap(path: str, size: int) -> QPixmap:
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)


class AvatarLabel(QWidget):
    def __init__(self, size: int = 84, letter: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._size = size
        self._letter = letter
        self._pixmap: QPixmap | None = None
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_avatar(self, path: Path | None, letter: str = "") -> None:
        self._letter = letter or self._letter
        if path and path.is_file():
            self._pixmap = _load_pixmap(str(path), self._size)
        else:
            self._pixmap = None
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        clip = QPainterPath()
        clip.addRoundedRect(rect, self._size * 0.22, self._size * 0.22)
        painter.setClipPath(clip)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#EAF3FF"))
        gradient.setColorAt(1, QColor("#D9E9FB"))
        painter.fillPath(clip, gradient)
        if self._pixmap and not self._pixmap.isNull():
            painter.drawPixmap(rect.toRect(), self._pixmap)
        else:
            painter.setPen(QColor(GOLD))
            font = QFont("Microsoft YaHei UI", max(12, int(self._size * 0.28)), QFont.Bold)
            painter.setFont(font)
            text = (self._letter or "?")[:2]
            painter.drawText(rect, Qt.AlignCenter, text)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.drawRoundedRect(rect, self._size * 0.22, self._size * 0.22)


class TierBadge(QLabel):
    def __init__(self, tier: str = "C", parent: QWidget | None = None):
        super().__init__(parent)
        self.set_tier(tier)

    def set_tier(self, tier: str) -> None:
        color = TIER_COLORS.get(tier, "#6F8299")
        text_color = TIER_TEXT_COLORS.get(tier, "#FFFFFF")
        self.setText(tier)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(22)
        self.setMinimumWidth(34)
        if tier == "SS":
            background = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                " stop:0 #F8E7A6, stop:0.55 #E2C04A, stop:1 #C99B1F)"
            )
            border = "#B08A1E"
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(16)
            effect.setOffset(0, 0)
            effect.setColor(QColor(212, 175, 55, 220))
            self.setGraphicsEffect(effect)
        else:
            background = rgba(color, 235)
            border = rgba(color, 255) if tier != "B" else "#C9D6E5"
            self.setGraphicsEffect(None)
        self.setStyleSheet(
            f"QLabel {{ color: {text_color}; background: {background};"
            f" border: 1px solid {border}; border-radius: 6px;"
            f" font-size: 13px; font-weight: 800; padding: 0 6px; }}"
        )


class UnitCard(QFrame):
    clicked = Signal(object)

    def __init__(
        self,
        *,
        name: str,
        subtitle: str,
        tier: str,
        avatar: Path | None,
        owned: bool = True,
        footer: str = "",
        letter: str = "",
        crown: bool = False,
        frame_color: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("SoftCard")
        self.setFixedSize(164, 218)
        self.setCursor(Qt.PointingHandCursor)
        self._payload = None
        frame = FRAME_GOLD if crown else (frame_color or BORDER)
        border_width = 2 if (crown or frame_color) else 1
        background = "#FFF9E8" if crown else PANEL_2
        self.setStyleSheet(
            f"QFrame#SoftCard {{ background: {background};"
            f" border: {border_width}px solid {frame}; border-radius: 14px; }}"
            f"QFrame#SoftCard:hover {{ border: 2px solid {frame}; background: #F0F7FF; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(6)

        self.avatar = AvatarLabel(84, letter or name[:2])
        self.avatar.set_avatar(avatar, name[:2])
        layout.addWidget(self.avatar, 0, Qt.AlignHCenter)

        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFixedWidth(140)
        self.name_label.setStyleSheet(
            f"color: {TEXT if owned else MUTED}; font-size: 13px; font-weight: 600;"
        )
        metrics = QFontMetrics(self.name_label.font())
        self.name_label.setText(metrics.elidedText(name, Qt.ElideRight, 136))
        self.name_label.setToolTip(name)
        layout.addWidget(self.name_label, 0, Qt.AlignHCenter)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        self.subtitle_label.setFixedWidth(140)
        layout.addWidget(self.subtitle_label, 0, Qt.AlignHCenter)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        bottom.addStretch(1)
        self.badge = TierBadge(tier)
        if crown:
            self.badge.setText(f"♛ {tier}")
            self.badge.setToolTip("A- 皇冠卡")
        bottom.addWidget(self.badge)
        bottom.addStretch(1)
        layout.addLayout(bottom)

        self.footer_label = QLabel(footer)
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(self.footer_label)
        if not owned:
            self.setStyleSheet(
                self.styleSheet()
                + f"QFrame#SoftCard {{ background: #F8FBFF; }}"
            )

    def set_payload(self, payload) -> None:
        self._payload = payload

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._payload)
        super().mouseReleaseEvent(event)


class RadarChart(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._data: list[tuple[str, float]] = []
        self.setMinimumSize(300, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, data: list[tuple[str, float]]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event):  # noqa: N802
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        center = QPoint(int(width / 2), int(height / 2) + 4)
        radius = min(width, height) * 0.32
        count = len(self._data)
        import math

        def point(index: int, ratio: float) -> QPoint:
            angle = -math.pi / 2 + 2 * math.pi * index / count
            return QPoint(
                int(center.x() + math.cos(angle) * radius * ratio),
                int(center.y() + math.sin(angle) * radius * ratio),
            )

        for level in (0.25, 0.5, 0.75, 1.0):
            polygon = QPolygonF([point(i, level) for i in range(count)])
            painter.setPen(QPen(QColor("#D6E4F5"), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(polygon)
        for i in range(count):
            painter.setPen(QPen(QColor("#D6E4F5"), 1))
            painter.drawLine(center, point(i, 1.0))

        values = [max(0.0, min(100.0, score)) / 100.0 for _, score in self._data]
        polygon = QPolygonF([point(i, values[i]) for i in range(count)])
        fill = QColor(GOLD)
        fill.setAlpha(45)
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(GOLD), 2))
        painter.drawPolygon(polygon)
        painter.setBrush(QColor(GOLD))
        for i in range(count):
            painter.drawEllipse(point(i, values[i]), 4, 4)

        font = QFont("Microsoft YaHei UI", 11)
        font.setBold(True)
        painter.setFont(font)
        for i, (label, score) in enumerate(self._data):
            pos = point(i, 1.22)
            text = f"{label}  {score:.0f}"
            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(text)
            rect = QRect(pos.x() - text_width // 2 - 4, pos.y() - 9, text_width + 8, 18)
            painter.setPen(QColor(MUTED))
            painter.drawText(rect, Qt.AlignCenter, text)


class TierBars(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._data: list[tuple[str, int, str]] = []
        self.setMinimumHeight(118)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_data(self, data: list[tuple[str, int, str]]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event):  # noqa: N802
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        max_value = max((count for _, count, _ in self._data), default=1)
        row_height = self.height() / max(1, len(self._data))
        label_width = 34
        count_width = 38
        for index, (label, count, color) in enumerate(self._data):
            y = index * row_height
            painter.setPen(QColor(MUTED))
            font = QFont("Microsoft YaHei UI", 10)
            painter.setFont(font)
            painter.drawText(QRect(0, int(y), label_width, int(row_height)), Qt.AlignVCenter | Qt.AlignLeft, label)
            bar_x = label_width + 2
            bar_width = max(1, self.width() - label_width - count_width - 4)
            bar_rect = QRectF(bar_x, y + row_height * 0.32, bar_width, max(3.0, row_height * 0.34))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#E8F1FB"))
            painter.drawRoundedRect(bar_rect, 3, 3)
            if count > 0:
                fill = QRectF(bar_rect)
                fill.setWidth(max(3.0, bar_rect.width() * count / max_value))
                painter.setBrush(QColor(color))
                painter.drawRoundedRect(fill, 3, 3)
            painter.setPen(QColor(TEXT))
            painter.drawText(
                QRect(self.width() - count_width, int(y), count_width, int(row_height)),
                Qt.AlignVCenter | Qt.AlignRight,
                str(count),
            )


class ProgressLine(QWidget):
    def __init__(self, label: str, value_text: str, pct: float, color: str = GOLD, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.label = QLabel(label)
        self.label.setStyleSheet(f"color: {TEXT}; font-size: 13px;")
        self.value = QLabel(value_text)
        self.value.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600;")
        top.addWidget(self.label)
        top.addStretch(1)
        top.addWidget(self.value)
        layout.addLayout(top)
        self.bar = QFrame()
        self.bar.setFixedHeight(5)
        self.bar.setStyleSheet(f"QFrame {{ background: #E8F1FB; border-radius: 2px; }}")
        layout.addWidget(self.bar)
        self.fill = QFrame(self.bar)
        self.fill.setStyleSheet(f"QFrame {{ background: {color}; border-radius: 2px; }}")
        self.fill.setGeometry(0, 0, 0, 5)
        self._pct = max(0.0, min(100.0, pct))

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.fill.setGeometry(0, 0, int(self.bar.width() * self._pct / 100), self.bar.height())
