"""Android emulator one-click proxy capture dialog."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..capture.android import AndroidBridge, AndroidDevice, AndroidError
from ..capture.android_proxy_session import (
    REGIONS,
    AndroidProxyWorker,
    available_port,
    candidate_packages,
    region,
)
from ..state import AppState
from .theme import BORDER, GOLD, MUTED, PANEL, PANEL_2, TEXT


class AndroidProxyDialog(QDialog):
    def __init__(
        self,
        state: AppState,
        bridge: AndroidBridge,
        device: AndroidDevice | None = None,
        package: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.state = state
        self.bridge = bridge
        self.device = device
        self.package = package
        self.worker: AndroidProxyWorker | None = None
        self.port = available_port()
        self.setWindowTitle("Android 模拟器抓包")
        self.setMinimumSize(760, 660)
        self.resize(820, 720)
        self.setStyleSheet(f"QDialog {{ background: {PANEL}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(10)

        title = QLabel("Android 模拟器一键抓包")
        title.setStyleSheet(f"color: {TEXT}; font-size: 23px; font-weight: 700;")
        layout.addWidget(title)
        sub = QLabel(
            "自动检测 ADB/模拟器，自动选择端口并配置代理；开始后请在游戏里重新登录。"
        )
        sub.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        device_card = QFrame()
        device_card.setObjectName("Panel")
        device_layout = QHBoxLayout(device_card)
        device_layout.setContentsMargins(14, 10, 14, 10)
        device_layout.setSpacing(10)
        self.device_label = QLabel("未检测设备")
        self.device_label.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        device_layout.addWidget(self.device_label, 1)
        self.detect_button = QPushButton("重新检测")
        self.detect_button.setObjectName("Ghost")
        self.detect_button.clicked.connect(self._detect)
        device_layout.addWidget(self.detect_button)
        layout.addWidget(device_card)

        options = QFrame()
        options.setObjectName("Panel")
        options_layout = QVBoxLayout(options)
        options_layout.setContentsMargins(14, 12, 14, 12)
        options_layout.setSpacing(7)
        row = QHBoxLayout()
        row.addWidget(QLabel("区服"))
        self.region_combo = QComboBox()
        for key, profile in REGIONS.items():
            self.region_combo.addItem(profile.label, key)
        self.region_combo.currentIndexChanged.connect(self._on_region_changed)
        row.addWidget(self.region_combo, 1)
        row.addSpacing(16)
        row.addWidget(QLabel("包名"))
        self.package_combo = QComboBox()
        self.package_combo.setMinimumWidth(320)
        row.addWidget(self.package_combo, 2)
        options_layout.addLayout(row)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("本地端口"))
        self.port_label = QLabel(str(self.port))
        self.port_label.setStyleSheet(f"color: {TEXT}; font-weight: 600;")
        port_row.addWidget(self.port_label)
        self.port_button = QPushButton("自动换端口")
        self.port_button.setObjectName("Ghost")
        self.port_button.clicked.connect(self._pick_port)
        port_row.addWidget(self.port_button)
        port_row.addStretch(1)
        self.profile_note = QLabel()
        self.profile_note.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self.profile_note.setWordWrap(True)
        port_row.addWidget(self.profile_note, 2)
        options_layout.addLayout(port_row)
        layout.addWidget(options)

        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet(
            f"color: #7A4A00; background: #FFF8E6; border: 1px solid #F0D48A;"
            " border-radius: 8px; padding: 8px 10px; font-size: 11px;"
        )
        layout.addWidget(self.notice)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(170)
        self.log_box.setStyleSheet(
            f"QTextEdit {{ background: #F8FBFF; color: {MUTED};"
            f" border: 1px solid {BORDER}; border-radius: 8px; padding: 8px;"
            " font-size: 11px; }"
        )
        layout.addWidget(self.log_box, 1)

        actions = QHBoxLayout()
        self.start_button = QPushButton("开始抓包")
        self.start_button.setObjectName("Primary")
        self.start_button.clicked.connect(self._start)
        actions.addWidget(self.start_button)
        self.stop_button = QPushButton("停止并恢复")
        self.stop_button.setObjectName("Ghost")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop)
        actions.addWidget(self.stop_button)
        actions.addStretch(1)
        close = QPushButton("关闭")
        close.setObjectName("Ghost")
        close.clicked.connect(self.reject)
        actions.addWidget(close)
        layout.addLayout(actions)

        self._detect()
        self._on_region_changed()

    # ------------------------------------------------------------------
    def _append(self, message: str) -> None:
        self.log_box.append(message)

    def _detect(self) -> None:
        self.device = None
        self.device_label.setText("正在检测 ADB / 模拟器…")
        if not self.bridge.available:
            self.device_label.setText("未找到 adb.exe")
            self._append("未找到 adb；请安装 Platform Tools，或使用 MuMu/LDPlayer 自带的 adb。")
            return
        try:
            devices = [item for item in self.bridge.devices() if item.state == "device"]
        except AndroidError as exc:
            self.device_label.setText("ADB 调用失败")
            self._append(str(exc))
            return
        if not devices:
            self.device_label.setText("未检测到设备")
            self._append("请先启动模拟器，并确认 ADB 调试已开启。")
            return
        self.device = devices[0]
        self.device_label.setText(f"已检测：{self.device.label}")
        try:
            installed = self.bridge.installed_packages(self.device.serial)
            for index, (key, profile) in enumerate(REGIONS.items()):
                if any(item in installed for item in profile.packages):
                    self.region_combo.setCurrentIndex(index)
                    break
        except AndroidError:
            pass
        self._refresh_packages()
        self._append(f"ADB：{self.bridge.adb_path}")
        self._append(f"设备：{self.device.label}")

    def _on_region_changed(self, _index: int = 0) -> None:
        self._refresh_packages()
        self.port = available_port()
        self.port_label.setText(str(self.port))
        key = self.region_combo.currentData()
        profile = region(str(key))
        self.profile_note.setText(profile.note)
        if profile.bridge:
            self.notice.setText(
                "国服复活版：会额外转发 18765/18766 本地桥接。开始后必须在游戏里"
                "「退出登录 / 切换账号」并重新输入账密；只重启客户端抓不到 sign。"
            )
        else:
            self.notice.setText(
                "开始后重启游戏即可，和 PC 国服流程一样；不需要退出登录。"
                "客户端重启后会重新走登录并抓取 Index。"
            )

    def _refresh_packages(self) -> None:
        self.package_combo.clear()
        if not self.device:
            return
        key = str(self.region_combo.currentData() or "cn_revival")
        try:
            packages = candidate_packages(self.bridge, self.device.serial, key)
        except AndroidError as exc:
            self._append(f"读取包名失败：{exc}")
            packages = []
        for item in packages:
            self.package_combo.addItem(item, item)
        if self.package and self.package in packages:
            self.package_combo.setCurrentIndex(packages.index(self.package))
        elif packages:
            self.package = packages[0]

    def _pick_port(self) -> None:
        self.port = available_port()
        self.port_label.setText(str(self.port))

    def _start(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if not self.device:
            QMessageBox.warning(self, "没有设备", "请先检测到 Android 模拟器。")
            return
        package = self.package_combo.currentData()
        if not package:
            QMessageBox.warning(self, "没有游戏包名", "当前区服没有检测到对应包名。")
            return
        self.package = str(package)
        self.log_box.clear()
        self.start_button.setEnabled(False)
        self.detect_button.setEnabled(False)
        self.region_combo.setEnabled(False)
        self.package_combo.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.worker = AndroidProxyWorker(
            self.bridge,
            self.device.serial,
            self.package,
            str(self.region_combo.currentData()),
            self.port,
            parent=self,
        )
        self.worker.log.connect(self._append)
        self.worker.snapshot.connect(self._on_snapshot)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _stop(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self._append("正在停止并恢复模拟器…")
            self.worker.stop()
            self.stop_button.setEnabled(False)

    def _on_snapshot(self, payload: dict, path: str) -> None:
        self._append(f"[SNAP] {path}")
        if self.state.load_payload(payload, source_path=Path(path)):
            self.accept()

    def _on_failed(self, message: str) -> None:
        self._append(f"[失败] {message}")
        QMessageBox.warning(self, "抓包失败", message)

    def _on_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.detect_button.setEnabled(True)
        self.region_combo.setEnabled(True)
        self.package_combo.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):  # noqa: N802
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(12000):
                QMessageBox.information(
                    self,
                    "正在恢复模拟器",
                    "抓包线程仍在清理代理/端口，请稍等几秒再关闭。",
                )
                event.ignore()
                return
        super().closeEvent(event)
