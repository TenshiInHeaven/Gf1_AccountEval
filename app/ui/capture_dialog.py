"""Capture dialog: live XLua extraction or JSON snapshot import."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..capture.android import AndroidBridge, AndroidError, PACKAGE_LABELS
from ..capture.live import CaptureError, capture, find_game_pid
from ..core.paths import PROJECT_ROOT
from ..state import AppState
from .android_proxy_dialog import AndroidProxyDialog
from .theme import BORDER, GOLD, GREEN, MUTED, PANEL, PANEL_2, RED, TEXT


class CaptureWorker(QThread):
    finished_ok = Signal(object, str)
    failed = Signal(str)
    log = Signal(str)

    def __init__(self, pid: int | None = None, parent=None):
        super().__init__(parent)
        self.pid = pid

    def run(self) -> None:
        try:
            self.log.emit("正在附身游戏进程…")
            payload, raw = capture(self.pid)
            counts = {key: len(payload.get(key) or []) for key in ("dolls", "fairies", "equipment", "sangvis")}
            self.log.emit(
                f"读取完成：人形 {counts['dolls']} · 妖精 {counts['fairies']} · "
                f"装备 {counts['equipment']} · 融合势力 {counts['sangvis']}"
            )
            self.finished_ok.emit(payload, raw)
        except CaptureError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - UI safety
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class CaptureDialog(QDialog):
    def __init__(self, state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self.worker: CaptureWorker | None = None
        self.android = AndroidBridge()
        self.android_device = None
        self.android_package: str | None = None
        self.setWindowTitle("提取账号")
        self.setFixedSize(720, 840)
        self.setStyleSheet(f"QDialog {{ background: {PANEL}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 20)
        root.setSpacing(12)

        title = QLabel("提取账号配置")
        title.setStyleSheet(f"color: {TEXT}; font-size: 24px; font-weight: 700;")
        root.addWidget(title)
        sub = QLabel("账号数据在服务器上；可通过 PC 的 XLua 只读读取，或从 Android 模拟器拉取显式导出的快照。")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        live = QFrame()
        live.setObjectName("Panel")
        live_layout = QVBoxLayout(live)
        live_layout.setContentsMargins(18, 15, 18, 15)
        live_layout.setSpacing(8)
        live_head = QHBoxLayout()
        live_title = QLabel("方式 A · 从运行中的游戏提取")
        live_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        live_head.addWidget(live_title)
        live_head.addStretch(1)
        self.pid_label = QLabel()
        self.pid_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        live_head.addWidget(self.pid_label)
        live_layout.addLayout(live_head)
        live_note = QLabel("需要游戏已登录并进入主界面。会读取：仓库人形、妖精、装备、融合势力。")
        live_note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        live_note.setWordWrap(True)
        live_layout.addWidget(live_note)
        live_actions = QHBoxLayout()
        self.live_button = QPushButton("开始提取")
        self.live_button.setObjectName("Primary")
        self.live_button.clicked.connect(self._start_live)
        live_actions.addWidget(self.live_button)
        self.detect_button = QPushButton("检测游戏")
        self.detect_button.setObjectName("Ghost")
        self.detect_button.clicked.connect(self._detect)
        live_actions.addWidget(self.detect_button)
        live_actions.addStretch(1)
        live_layout.addLayout(live_actions)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(120)
        self.log_box.setStyleSheet(
            f"QTextEdit {{ background: #F8FBFF; color: {MUTED}; border: 1px solid {BORDER};"
            "border-radius: 8px; padding: 8px; font-size: 12px; }"
        )
        live_layout.addWidget(self.log_box)
        root.addWidget(live)

        import_card = QFrame()
        import_card.setObjectName("Panel")
        import_layout = QHBoxLayout(import_card)
        import_layout.setContentsMargins(18, 15, 18, 15)
        import_layout.setSpacing(12)
        import_text = QVBoxLayout()
        import_title = QLabel("方式 B · 导入快照 JSON")
        import_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        import_text.addWidget(import_title)
        import_note = QLabel("适合保存过的账号快照，或在另一台机器上提取后带回。")
        import_note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        import_text.addWidget(import_note)
        import_layout.addLayout(import_text, 1)
        import_button = QPushButton("选择文件…")
        import_button.setObjectName("Ghost")
        import_button.clicked.connect(self._import_file)
        import_layout.addWidget(import_button)
        root.addWidget(import_card)

        android_card = QFrame()
        android_card.setObjectName("Panel")
        android_layout = QVBoxLayout(android_card)
        android_layout.setContentsMargins(18, 14, 18, 14)
        android_layout.setSpacing(7)
        android_head = QHBoxLayout()
        android_title = QLabel("方式 C · Android 模拟器 / 设备")
        android_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 600;")
        android_head.addWidget(android_title)
        android_head.addStretch(1)
        self.android_status = QLabel("未检测")
        self.android_status.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        android_head.addWidget(self.android_status)
        android_layout.addLayout(android_head)
        android_note = QLabel(
            "一键检测 ADB / 模拟器，自动选择端口并配置代理；区服支持台服、日服、"
            "美服、国服复活版。开始后需要退出登录/切换账号并重新登录。"
        )
        android_note.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        android_note.setWordWrap(True)
        android_layout.addWidget(android_note)
        android_actions = QHBoxLayout()
        self.android_proxy = QPushButton("一键抓包")
        self.android_proxy.setObjectName("Primary")
        self.android_proxy.clicked.connect(self._open_android_proxy)
        android_actions.addWidget(self.android_proxy)
        self.android_detect = QPushButton("检测设备")
        self.android_detect.setObjectName("Ghost")
        self.android_detect.clicked.connect(self._detect_android)
        android_actions.addWidget(self.android_detect)
        self.android_launch = QPushButton("启动游戏")
        self.android_launch.setObjectName("Ghost")
        self.android_launch.clicked.connect(self._launch_android)
        android_actions.addWidget(self.android_launch)
        self.android_pull = QPushButton("从设备导入快照")
        self.android_pull.setObjectName("Ghost")
        self.android_pull.clicked.connect(self._pull_android)
        android_actions.addWidget(self.android_pull)
        android_actions.addStretch(1)
        android_layout.addLayout(android_actions)
        self.android_security = QLabel(self.android.security_note)
        self.android_security.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self.android_security.setWordWrap(True)
        android_layout.addWidget(self.android_security)
        root.addWidget(android_card)

        sample_card = QFrame()
        sample_card.setObjectName("Panel")
        sample_layout = QHBoxLayout(sample_card)
        sample_layout.setContentsMargins(18, 12, 18, 12)
        sample_title = QLabel("没有账号？先用内置示例数据体验四维评分。")
        sample_title.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        sample_layout.addWidget(sample_title, 1)
        sample_button = QPushButton("载入示例")
        sample_button.setObjectName("Chip")
        sample_button.clicked.connect(self._load_sample)
        sample_layout.addWidget(sample_button)
        root.addWidget(sample_card)
        root.addStretch(1)

        close = QPushButton("关闭")
        close.setObjectName("Ghost")
        close.clicked.connect(self.reject)
        root.addWidget(close, 0, Qt.AlignRight)
        self._detect(silent=True)
        self._detect_android(silent=True)

    # ------------------------------------------------------------------
    def _append(self, text: str) -> None:
        self.log_box.append(text)

    def _detect(self, silent: bool = False) -> None:
        try:
            pid = find_game_pid()
        except CaptureError as exc:
            self.pid_label.setText("Frida 不可用")
            if not silent:
                self._append(str(exc))
            return
        if pid:
            self.pid_label.setText(f"已检测到进程 PID {pid}")
        else:
            self.pid_label.setText("未检测到 GrilsFrontLine.exe")
            if not silent:
                self._append("请先启动游戏并登录，再点击「检测游戏」。")

    # ------------------------------------------------------------------
    def _detect_android(self, silent: bool = False) -> None:
        self.android = AndroidBridge()
        self.android_device = None
        self.android_package = None
        self.android_launch.setEnabled(False)
        self.android_pull.setEnabled(False)
        if not self.android.available:
            self.android_status.setText("未找到 adb")
            if not silent:
                self._append("未找到 adb.exe；请安装 Platform Tools，或使用自带 adb 的模拟器。")
            return
        try:
            devices = [device for device in self.android.devices() if device.state == "device"]
        except AndroidError as exc:
            self.android_status.setText("ADB 调用失败")
            if not silent:
                self._append(str(exc))
            return
        if not devices:
            self.android_status.setText("未检测到设备")
            if not silent:
                self._append("未检测到 Android 设备；请先启动模拟器并确认 ADB 已开启。")
            return
        self.android_device = devices[0]
        try:
            self.android_package = self.android.detect_package(self.android_device.serial)
        except AndroidError:
            self.android_package = None
        package_text = (
            f"{PACKAGE_LABELS.get(self.android_package, self.android_package)}"
            if self.android_package
            else "未找到少前包名"
        )
        self.android_status.setText(f"{self.android_device.label} · {package_text}")
        self.android_launch.setEnabled(bool(self.android_package))
        self.android_pull.setEnabled(True)
        if not silent:
            self._append(
                f"Android 设备：{self.android_device.label}；包名：{self.android_package or '未找到'}"
            )

    def _open_android_proxy(self) -> None:
        if not self.android_device:
            self._detect_android()
        if not self.android_device:
            QMessageBox.warning(
                self, "没有设备", "请先启动模拟器并点击「检测设备」。"
            )
            return
        dialog = AndroidProxyDialog(
            self.state,
            self.android,
            self.android_device,
            self.android_package,
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.accept()

    def _launch_android(self) -> None:
        if not self.android_device:
            self._detect_android()
        if not self.android_device:
            return
        try:
            label = self.android.launch_game(self.android_device.serial, self.android_package)
            self._append(f"已在 Android 启动：{label}")
        except AndroidError as exc:
            self._append(f"Android 启动失败：{exc}")
            QMessageBox.warning(self, "Android 启动失败", str(exc))

    def _pull_android(self) -> None:
        if not self.android_device:
            self._detect_android()
        if not self.android_device:
            return
        try:
            payload = self.android.pull_snapshot(self.android_device.serial, self.android_package)
        except AndroidError as exc:
            self._append(f"Android 拉取失败：{exc}")
            QMessageBox.warning(self, "Android 拉取失败", str(exc))
            return
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = PROJECT_ROOT / "snapshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"account_android_{stamp}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        self._append(f"Android 快照已保存：{out_path}")
        if self.state.load_payload(payload, source_path=out_path):
            self.accept()

    def _start_live(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.live_button.setEnabled(False)
        self.live_button.setText("提取中…")
        self.log_box.clear()
        self.worker = CaptureWorker()
        self.worker.log.connect(self._append)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.start()

    def _on_failed(self, message: str) -> None:
        self.live_button.setEnabled(True)
        self.live_button.setText("重试提取")
        self._append(f"失败：{message}")
        QMessageBox.warning(self, "提取失败", message)

    def _on_finished(self, payload: dict, raw: str) -> None:
        self.live_button.setEnabled(True)
        self.live_button.setText("重新提取")
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = PROJECT_ROOT / "snapshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"account_{stamp}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        self._append(f"快照已保存：{out_path}")
        if self.state.load_payload(payload, source_path=out_path):
            self.accept()

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择账号快照", str(PROJECT_ROOT), "JSON 快照 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        if self.state.load_path(Path(path)):
            self.state.save_last_path(Path(path))
            self.accept()

    def _load_sample(self) -> None:
        if self.state.load_sample():
            self.accept()

    def closeEvent(self, event):  # noqa: N802
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "正在提取", "请等待当前提取完成后再关闭窗口。")
            event.ignore()
            return
        super().closeEvent(event)
