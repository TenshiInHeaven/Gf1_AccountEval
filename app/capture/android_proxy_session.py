"""One-click Android emulator proxy capture.

The flow is intentionally close to targetForge:
detect ADB/device, start the local capture proxy, configure the emulator
(``adb reverse`` + optional bridge forwards + global proxy), restart the game,
and wait for a fresh login.  Only the CN revival profile needs the local
18765/18766 bridge; other regions use the normal proxy path.
"""
from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from ..core.paths import PROJECT_ROOT
from .android import AndroidBridge, AndroidError

PYTHON = sys.executable
PROXY_TOOL = PROJECT_ROOT / "tools" / "android_proxy_capture.py"
CA_FILE = PROJECT_ROOT / ".cache" / "android_mitm" / "ca" / "ca.crt"


@dataclass(frozen=True)
class AndroidRegion:
    key: str
    label: str
    packages: tuple[str, ...]
    bridge: bool = False
    needs_ca: bool = True
    fresh_login: bool = False
    note: str = ""


REGIONS: dict[str, AndroidRegion] = {
    "tw": AndroidRegion(
        "tw", "台服", ("tw.txwy.and.snqx",), note="正常 HTTPS 登录"
    ),
    "jp": AndroidRegion(
        "jp", "日服", ("com.sunborn.girlsfrontline.jp",), note="正常 HTTPS 登录"
    ),
    "en": AndroidRegion(
        "en",
        "美服",
        ("com.sunborn.girlsfrontline.en", "com.sunborn.girlsfrontline"),
        note="正常 HTTPS 登录",
    ),
    "cn_revival": AndroidRegion(
        "cn_revival",
        "国服复活版",
        ("com.sunborn.girlsfrontline.pt",),
        bridge=True,
        needs_ca=False,
        fresh_login=True,
        note="额外使用 18765/18766 本地桥接，必须全新登录",
    ),
}


def region(key: str) -> AndroidRegion:
    return REGIONS.get(key, REGIONS["cn_revival"])


def region_for_package(package: str | None) -> str | None:
    """Map an installed package to the most specific capture profile."""
    value = str(package or "").strip()
    if not value:
        return None
    for key, profile in REGIONS.items():
        if value in profile.packages:
            return key
    return None


def available_port(start: int = 18080) -> int:
    for port in range(start, start + 80):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise AndroidError("找不到可用的本地代理端口")


def candidate_packages(
    bridge: AndroidBridge, serial: str, region_key: str
) -> list[str]:
    installed = bridge.installed_packages(serial)
    profile = region(region_key)
    return [item for item in profile.packages if item in installed]


def _run(
    adb_path: Path, serial: str, *args: str, timeout: int = 25
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(adb_path), "-s", serial, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


class AndroidProxyWorker(QThread):
    """Run the proxy and configure/restore the emulator off the UI thread."""

    log = Signal(str)
    snapshot = Signal(object, str)
    failed = Signal(str)

    def __init__(
        self,
        bridge: AndroidBridge,
        serial: str,
        package: str,
        region_key: str,
        port: int,
        timeout: int = 240,
        parent=None,
    ):
        super().__init__(parent)
        self.bridge = bridge
        self.serial = serial
        self.package = package
        self.region = region(region_key)
        self.port = port
        self.timeout = timeout
        self._stopped = threading.Event()
        self._process: subprocess.Popen | None = None
        self._installed_ca = False
        self._reverse = False
        self._forwards: list[int] = []

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._stopped.set()
        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def _adb(self, *args: str, timeout: int = 25) -> subprocess.CompletedProcess:
        self.log.emit(f"adb {' '.join(args)}")
        return _run(self.bridge.adb_path, self.serial, *args, timeout=timeout)

    def _install_ca(self, ca_file: Path) -> None:
        if not self.region.needs_ca:
            self.log.emit("国服复活版走 HTTP API，跳过系统 CA")
            return
        if not ca_file.is_file():
            self.log.emit("CA 尚未生成，跳过系统 CA")
            return
        try:
            from cryptography import x509
        except ImportError:
            self.log.emit("缺少 cryptography，CA 未自动安装；请手动安装 Download 里的 CA")
            return
        try:
            cert = x509.load_pem_x509_certificate(ca_file.read_bytes())
            digest = hashlib.md5(cert.subject.public_bytes()).digest()
            name = f"{int.from_bytes(digest[:4], 'little'):08x}.0"
            self._adb("root", timeout=20)
            self._adb("wait-for-device", timeout=20)
            cmds = [
                "umount /system/etc/security/cacerts >/dev/null 2>&1 || true",
                "rm -rf /data/local/tmp/gf_cacerts; cp -a /system/etc/security/cacerts /data/local/tmp/gf_cacerts",
            ]
            for command in cmds:
                self._adb("shell", command, timeout=25)
            pushed = self._adb(
                "push", str(ca_file), f"/data/local/tmp/gf_cacerts/{name}", timeout=30
            )
            if pushed.returncode != 0:
                raise AndroidError((pushed.stderr or pushed.stdout).strip())
            self._adb(
                "shell",
                f"chmod 644 /data/local/tmp/gf_cacerts/{name}; "
                f"chown root:root /data/local/tmp/gf_cacerts/{name}; "
                f"chcon u:object_r:system_security_cacerts_file:s0 /data/local/tmp/gf_cacerts/{name}",
                timeout=20,
            )
            mounted = self._adb(
                "shell",
                "mount -o bind /data/local/tmp/gf_cacerts /system/etc/security/cacerts",
                timeout=20,
            )
            if mounted.returncode != 0:
                raise AndroidError((mounted.stderr or mounted.stdout).strip())
            self._installed_ca = True
            self.log.emit(f"系统 CA 已安装：{name}")
        except Exception as exc:  # noqa: BLE001
            self.log.emit(f"CA 自动安装失败：{exc}；可手动安装 Download 里的 CA")

    def _setup(self, ca_file: Path) -> None:
        self._install_ca(ca_file)
        try:
            self._adb("reverse", "--remove", f"tcp:{self.port}", timeout=10)
        except Exception:
            pass
        result = self._adb("reverse", f"tcp:{self.port}", f"tcp:{self.port}")
        if result.returncode != 0:
            raise AndroidError((result.stderr or result.stdout).strip() or "adb reverse 失败")
        self._reverse = True
        if self.region.bridge:
            for port in (18765, 18766):
                try:
                    self._adb("forward", "--remove", f"tcp:{port}", timeout=10)
                except Exception:
                    pass
                result = self._adb("forward", f"tcp:{port}", f"tcp:{port}")
                if result.returncode == 0:
                    self._forwards.append(port)
                else:
                    self.log.emit(f"桥接端口 {port} forward 失败：{(result.stderr or '').strip()}")
        result = self._adb(
            "shell",
            "settings",
            "put",
            "global",
            "http_proxy",
            f"127.0.0.1:{self.port}",
        )
        if result.returncode != 0:
            raise AndroidError((result.stderr or result.stdout).strip() or "设置代理失败")
        self.log.emit("模拟器代理已指向本机抓包端口")
        self._adb("shell", "am", "force-stop", self.package)
        launched = self._adb(
            "shell",
            "monkey",
            "-p",
            self.package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
            timeout=25,
        )
        if launched.returncode != 0:
            raise AndroidError((launched.stderr or launched.stdout).strip() or "启动游戏失败")
        if self.region.fresh_login:
            self.log.emit(
                "游戏已启动；请在游戏中退出登录 / 切换账号，再重新输入账密"
            )
        else:
            self.log.emit("游戏已重启；等待客户端重新登录并抓取 Index")

    def _restore(self) -> None:
        try:
            self._adb("shell", "settings", "put", "global", "http_proxy", ":0", timeout=10)
        except Exception:
            pass
        if self._reverse:
            try:
                self._adb("reverse", "--remove", f"tcp:{self.port}", timeout=10)
            except Exception:
                pass
        for port in self._forwards:
            try:
                self._adb("forward", "--remove", f"tcp:{port}", timeout=10)
            except Exception:
                pass
        if self._installed_ca:
            try:
                self._adb("shell", "umount /system/etc/security/cacerts >/dev/null 2>&1 || true", timeout=10)
                self._adb("shell", "rm -rf /data/local/tmp/gf_cacerts", timeout=10)
            except Exception:
                pass
        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        self._process = None

    def _pump(self, process: subprocess.Popen, output: queue.Queue[str | None]) -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                output.put(line.rstrip("\r\n"))
        finally:
            output.put(None)

    def run(self) -> None:  # noqa: PLR0915
        if not PROXY_TOOL.is_file():
            self.failed.emit(f"缺少抓包工具：{PROXY_TOOL}")
            return
        command = [
            PYTHON,
            str(PROXY_TOOL),
            "--port",
            str(self.port),
            "--host",
            "127.0.0.1",
            "--keep-running",
            "--push-ca",
            "--out-dir",
            str(PROJECT_ROOT / "snapshots"),
        ]
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        output: queue.Queue[str | None] = queue.Queue()
        try:
            self.log.emit(f"启动本地抓包代理：127.0.0.1:{self.port}")
            self._process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            threading.Thread(
                target=self._pump, args=(self._process, output), daemon=True
            ).start()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not CA_FILE.is_file() and not self._stopped.is_set():
                time.sleep(0.2)
            self._setup(CA_FILE)
            self.log.emit("抓包运行中：等待出现 [KEY] 和 [SNAP]…")
            deadline = time.monotonic() + self.timeout
            snapshot_path: Path | None = None
            while time.monotonic() < deadline and not self._stopped.is_set():
                try:
                    line = output.get(timeout=1.0)
                except queue.Empty:
                    continue
                if line is None:
                    break
                self.log.emit(line)
                match = re.search(r"\[SNAP\]\s*已写入\s+(.+\.json)", line)
                if match:
                    snapshot_path = Path(match.group(1).strip())
                    break
            if self._stopped.is_set():
                self.failed.emit("抓包已取消")
                return
            if snapshot_path is None:
                self.failed.emit(
                    "未捕获账号快照。请确认抓包期间在游戏中退出登录/切换账号并重新登录。"
                )
                return
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            self.snapshot.emit(payload, str(snapshot_path))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self._restore()
