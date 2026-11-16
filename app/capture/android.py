"""ADB bridge for Android emulators / devices.

This module deliberately stays at the ADB level: it can detect a device,
launch the game package and pull an **explicitly exported** JSON snapshot.
It does not read another app's memory.  In-process extraction on Android would
need root/Frida and is intentionally not part of the default path.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

PACKAGE_CANDIDATES = (
    "com.sunborn.girlsfrontline.cn",
    "com.sunborn.girlsfrontline",
    "com.sunborn.girlsfrontline.en",
    "com.sunborn.girlsfrontline.jp",
    "com.sunborn.girlsfrontline.pt",
    "com.sunborn.girlsfrontline.kr",
    "tw.txwy.and.snqx",
)

PACKAGE_LABELS = {
    "com.sunborn.girlsfrontline.cn": "国服",
    "com.sunborn.girlsfrontline": "国际服",
    "com.sunborn.girlsfrontline.en": "美服",
    "com.sunborn.girlsfrontline.jp": "日服",
    "com.sunborn.girlsfrontline.pt": "国服复活版 / 日服壳",
    "com.sunborn.girlsfrontline.kr": "韩服",
    "tw.txwy.and.snqx": "台服",
}

SNAPSHOT_CANDIDATES = (
    "/sdcard/Download/gf_account_snapshot.json",
    "/sdcard/gf_account_snapshot.json",
    "/sdcard/Android/data/{package}/files/gf_account_snapshot.json",
)

COMMON_ADB_PATHS = (
    r"D:\Program Files\Netease\MuMu\nx_device\15.0\shell\adb.exe",
    r"C:\Program Files\Netease\MuMu\nx_device\15.0\shell\adb.exe",
    r"C:\LDPlayer\LDPlayer9\adb.exe",
    r"D:\LDPlayer\LDPlayer9\adb.exe",
    r"C:\LDPlayer\LDPlayer4.0\adb.exe",
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    r"C:\Program Files\BlueStacks\HD-Adb.exe",
    r"C:\Program Files\Nox\bin\adb.exe",
    r"D:\Program Files\Nox\bin\adb.exe",
    r"C:\Program Files (x86)\Nox\bin\adb.exe",
)


class AndroidError(RuntimeError):
    pass


@dataclass
class AndroidDevice:
    serial: str
    state: str = "device"
    model: str = ""

    @property
    def label(self) -> str:
        return f"{self.serial} · {self.model}" if self.model else self.serial


class AndroidBridge:
    def __init__(self, adb_path: str | Path | None = None):
        self.adb_path = Path(adb_path) if adb_path else self.find_adb()

    # ------------------------------------------------------------------
    @staticmethod
    def find_adb() -> Path | None:
        found = shutil.which("adb")
        if found:
            return Path(found)
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        sdk = local / "Android" / "Sdk" / "platform-tools" / "adb.exe"
        candidates = [sdk, *(Path(path) for path in COMMON_ADB_PATHS)]
        for path in candidates:
            if path.is_file():
                return path
        # MuMu's version directory changes between releases; search it.
        for root in (
            Path(r"D:\Program Files\Netease\MuMu\nx_device"),
            Path(r"C:\Program Files\Netease\MuMu\nx_device"),
            Path(r"D:\Program Files\Netease\MuMuPlayer-12.0"),
            Path(r"C:\Program Files\Netease\MuMuPlayer-12.0"),
        ):
            if not root.is_dir():
                continue
            for path in root.glob("*/shell/adb.exe"):
                if path.is_file():
                    return path
        return None

    @property
    def available(self) -> bool:
        return bool(self.adb_path and self.adb_path.is_file())

    # ------------------------------------------------------------------
    def _run(self, *args: str, timeout: int = 12) -> subprocess.CompletedProcess:
        if not self.available:
            raise AndroidError("未找到 adb.exe；请安装 Android SDK Platform Tools 或使用自带 adb 的模拟器。")
        command = [str(self.adb_path), *args]
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AndroidError(f"ADB 调用失败：{exc}") from exc

    def devices(self) -> list[AndroidDevice]:
        result = self._run("devices", "-l")
        if result.returncode != 0:
            raise AndroidError(result.stderr.strip() or "adb devices 失败")
        devices = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            model = ""
            for part in parts[2:]:
                if part.startswith("model:"):
                    model = part.split(":", 1)[1].replace("_", " ")
            devices.append(AndroidDevice(serial=serial, state=state, model=model))
        return devices

    def installed_packages(self, serial: str) -> set[str]:
        result = self._run("-s", serial, "shell", "pm", "list", "packages")
        if result.returncode != 0:
            return set()
        packages = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                packages.add(line.split(":", 1)[1])
        return packages

    def detect_package(self, serial: str) -> str | None:
        packages = self.installed_packages(serial)
        for package in PACKAGE_CANDIDATES:
            if package in packages:
                return package
        return None

    def launch_game(self, serial: str, package: str | None = None) -> str:
        package = package or self.detect_package(serial)
        if not package:
            raise AndroidError("设备上没有找到少女前线包名。")
        result = self._run(
            "-s",
            serial,
            "shell",
            "monkey",
            "-p",
            package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        )
        if result.returncode != 0:
            raise AndroidError(result.stderr.strip() or "启动游戏失败")
        return f"{PACKAGE_LABELS.get(package, package)} · {package}"

    def is_package_running(self, serial: str, package: str) -> bool:
        """Return whether the package has a PID.

        This is a normal ADB process query; it does not read process memory.
        """
        result = self._run("-s", serial, "shell", "pidof", package, timeout=5)
        return result.returncode == 0 and bool(result.stdout.strip())

    def foreground_package(self, serial: str) -> str | None:
        """Best-effort foreground app lookup via dumpsys (no root/memory read)."""
        try:
            result = self._run(
                "-s", serial, "shell", "dumpsys", "activity", "activities", timeout=8
            )
        except AndroidError:
            return None
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if "mResumedActivity" not in line and "mCurrentFocus" not in line:
                continue
            match = re.search(r"([A-Za-z0-9_.]+)/\.?[A-Za-z0-9_.$]+", line)
            if match:
                return match.group(1)
        return None

    def pull_snapshot(self, serial: str, package: str | None = None) -> dict:
        package = package or self.detect_package(serial)
        candidates = [
            path.format(package=package or "") for path in SNAPSHOT_CANDIDATES
        ]
        with TemporaryDirectory(prefix="gf_android_") as tmp:
            local = Path(tmp) / "snapshot.json"
            for remote in candidates:
                result = self._run("-s", serial, "pull", remote, str(local), timeout=20)
                if result.returncode != 0 or not local.is_file() or local.stat().st_size == 0:
                    continue
                try:
                    payload = json.loads(local.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(payload, dict):
                    continue
                return payload
        raise AndroidError(
            "设备上没有找到快照 JSON。请先把 gf_account_snapshot.json 导出到 "
            "/sdcard/Download/ 后再拉取。"
        )

    def pull_snapshot_to(self, serial: str, target: Path, package: str | None = None) -> dict:
        payload = self.pull_snapshot(serial, package)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        return payload

    @property
    def security_note(self) -> str:
        return (
            "ADB 的 devices / pm list packages / pidof 属于普通调试命令；"
            "读取游戏内存或账号数据需要 root + Frida，可能触发反外挂/安全软件，"
            "本桥接默认只启动游戏并拉取你显式导出的快照。"
        )
