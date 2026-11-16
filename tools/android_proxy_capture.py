"""Capture a full Android account from the HTTPS ``Index/index`` response.

This is the proxy/MITM route described in ``build_private_server.md``:

    Android emulator
      -> Wi-Fi HTTP proxy (this tool, mitmproxy)
      -> decrypt S2C authcode
      -> save Index/index JSON
      -> convert to account_snapshot.json

It does **not** need root, Frida or process memory.  It needs the emulator to
trust the local CA and to be restarted/re-logged after the proxy is enabled.

Unsupported: 国服复活版 / PC 继承客户端.  Their sign is supplied inside the
process (`libgfcompat` / `pc_session_ciphertext`), not in the login HTTP flow;
the proxy can capture the encrypted Index but cannot decrypt it.

Install optional dependencies:

    build.bat --with-android

Run:

    python tools/android_proxy_capture.py --port 18080

Then set the emulator Wi-Fi proxy to the printed LAN IP:port, install the CA,
restart the game and log in.  The tool stops after a usable Index payload is
converted.  The resulting snapshot can be imported in the desktop app.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.capture.android_proxy import AndroidCaptureError, build_snapshot  # noqa: E402
from app.capture.android import AndroidBridge  # noqa: E402

STATIC_KEY = "yundoudou"
SUPPORT_NOTICE = (
    "不支持国服复活版 / PC 继承客户端："
    "其 sign 不在登录 HTTP 流程中返回，代理只能抓到加密 Index。"
)
CACHE = ROOT / ".cache" / "android_mitm"
DEFAULT_PORT = 18080


def _stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        value = sock.getsockname()[0]
        sock.close()
        return value
    except OSError:
        return "127.0.0.1"


def ensure_ca() -> Path:
    """Create/reuse a local CA and mitmproxy's expected confdir files."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    ca_dir = CACHE / "ca"
    confdir = CACHE / "confdir"
    ca_dir.mkdir(parents=True, exist_ok=True)
    confdir.mkdir(parents=True, exist_ok=True)
    cert_path = ca_dir / "ca.crt"
    key_path = ca_dir / "ca.key"
    if not cert_path.is_file() or not key_path.is_file():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "Gf1 AccountEval Android CA"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Gf1_AccountEval"),
            ]
        )
        now = dt.datetime.now(dt.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
    (confdir / "mitmproxy-ca.pem").write_bytes(key_path.read_bytes() + cert_path.read_bytes())
    (confdir / "mitmproxy-ca-cert.pem").write_bytes(cert_path.read_bytes())
    return cert_path


def decode_any(text: str, sign: str | None, static_key: str = STATIC_KEY) -> str | None:
    try:
        from gflzirc import gf_authcode
    except ImportError as exc:
        raise RuntimeError(
            "需要 gflzirc 才能解密 Index/index；请运行 build.bat --with-android"
        ) from exc
    for key in (static_key, sign):
        if not key:
            continue
        try:
            decoded = gf_authcode(text, "DECODE", key)
        except Exception:
            continue
        if not decoded:
            continue
        decoded = decoded.strip()
        if decoded.startswith(("{", "[")):
            return decoded
    return None


def _push_ca(ca_path: Path) -> None:
    bridge = AndroidBridge()
    devices = [item for item in bridge.devices() if item.state == "device"]
    if not devices:
        print("[CA] 没有检测到 ADB 设备；请手动把 CA 传到模拟器：")
        print(f"     {ca_path}")
        return
    serial = devices[0].serial
    remote = "/sdcard/Download/gf1_android_ca.crt"
    result = bridge._run("-s", serial, "push", str(ca_path), remote, timeout=20)
    if result.returncode == 0:
        print(f"[CA] 已推送到 {remote}")
        print("     在模拟器 设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书 中安装。")
    else:
        print(f"[CA] 推送失败：{result.stderr.strip()}")


def convert_index(path: Path, out_dir: Path) -> Path:
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshot = build_snapshot(payload, project_root=ROOT)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"account_android_{_stamp()}.json"
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[SNAP] 已写入 {out_path}")
    print(
        "[SNAP] "
        f"UID {snapshot['meta'].get('uid') or '—'} · "
        f"Lv.{snapshot['meta'].get('level') or '—'} · "
        f"{len(snapshot['dolls'])} 人形 / {len(snapshot['fairies'])} 妖精 / "
        f"{len(snapshot['sangvis'])} 融合势力 / {len(snapshot['equipment'])} 装备"
    )
    return out_path


def convert_raw(path: Path, out_dir: Path, sign: str | None = None, static_key: str = STATIC_KEY) -> Path:
    """Decode a saved ``#...`` Index response with a known session sign."""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"#([A-Za-z0-9+/=]+)", text)
    if not match:
        raise SystemExit(f"未找到 # 加密包：{path}")
    decoded = decode_any(match.group(1), sign, static_key)
    if not decoded:
        raise SystemExit(
            "解密失败：需要当前登录的 sign（每次登录会变化），"
            "用 --sign 传入；不能使用旧 cn_creds 的 sign。"
        )
    payload = json.loads(decoded)
    tmp = out_dir / f"index_decoded_{_stamp()}.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[INDEX] 解密成功，已写 {tmp}")
    return convert_index(tmp, out_dir)


class Recorder:
    def __init__(
        self,
        out_dir: Path,
        stop_after_index: bool = True,
        static_key: str = STATIC_KEY,
        initial_sign: str | None = None,
    ):
        self.out_dir = out_dir
        self.stop_after_index = stop_after_index
        self.static_key = static_key
        self.sign: str | None = initial_sign
        self.done = False
        self.packets = 0

    def _save(self, name: str, payload: Any) -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    def _scan(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        uid = payload.get("uid")
        sign = payload.get("sign")
        if uid and sign and str(sign) != self.sign:
            self.sign = str(sign)
            print(f"[KEY] uid={uid} sign 已获取", flush=True)

    def request(self, flow) -> None:
        try:
            url = str(flow.request.pretty_url)
            if "/index.php" not in url and "127.0.0.1:1876" not in url:
                return
            body = flow.request.get_text(strict=False) or ""
            print(
                f"[REQ] {getattr(flow.request, 'method', '')} {url} "
                f"len={len(body)} prefix={body[:160]!r}",
                flush=True,
            )
            raw_dir = self.out_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            self.req_count = getattr(self, "req_count", 0) + 1
            (raw_dir / f"req_{_stamp()}_{self.req_count:03d}.txt").write_text(
                f"# {url}\n{body[:200_000]}", encoding="utf-8", errors="replace"
            )
            # GFL requests carry encrypted JSON in outdatacode/signcode.  This
            # is where targetForge gets uid/sign when the login packet is not
            # a response body.
            fields = parse_qs(body)
            for field in ("outdatacode", "signcode"):
                for raw in fields.get(field) or []:
                    decoded = decode_any(unquote(raw), self.sign, self.static_key)
                    if not decoded:
                        continue
                    print(f"[C2S] {url}\n     {decoded[:300]}", flush=True)
                    try:
                        self._scan(json.loads(decoded))
                    except ValueError:
                        pass
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] 读取请求失败：{type(exc).__name__}: {exc}", flush=True)

    def response(self, flow) -> None:
        try:
            url = str(flow.request.pretty_url)
            text = flow.response.get_text(strict=False) or ""
            stripped = text.strip()
            if "/index.php" in url or "127.0.0.1:1876" in url:
                print(
                    f"[API] {getattr(flow.request, 'method', '')} {url} "
                    f"status={getattr(flow.response, 'status_code', 0)} len={len(text)} "
                    f"prefix={stripped[:32]!r}",
                    flush=True,
                )
                # Keep the raw response while bringing up a new region/client.
                # Index/index itself is saved separately once it decodes.
                if len(text) > 80:
                    raw_dir = self.out_dir / "raw"
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    self.raw_count = getattr(self, "raw_count", 0) + 1
                    (raw_dir / f"api_{_stamp()}_{self.raw_count:03d}.txt").write_text(
                        text[:2_000_000], encoding="utf-8", errors="replace"
                    )
            if stripped.startswith(("{", "[")):
                payload = json.loads(stripped)
            else:
                if "#" not in text:
                    return
                match = re.search(r"#([A-Za-z0-9+/=]+)", text)
                if not match:
                    return
                decoded = decode_any(match.group(1), self.sign, self.static_key)
                if not decoded:
                    print("[WARN] # 包解密失败（key/sign 可能变化）", flush=True)
                    return
                payload = json.loads(decoded)
            self.packets += 1
            self._scan(payload)
            if "Index/index" not in url:
                return
            print(f"[INDEX] 收到 Index/index，{len(decoded)} chars", flush=True)
            raw_path = self._save(f"index_{_stamp()}.json", payload)
            print(f"[INDEX] 原始响应：{raw_path}", flush=True)
            try:
                snapshot = build_snapshot(payload, project_root=ROOT)
            except AndroidCaptureError as exc:
                print(f"[WARN] 本次 Index 不含完整仓库，继续等待：{exc}", flush=True)
                return
            out_path = self.out_dir / f"account_android_{_stamp()}.json"
            out_path.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            print(f"[SNAP] 已写入 {out_path}", flush=True)
            print(
                "[SNAP] "
                f"UID {snapshot['meta'].get('uid') or '—'} · Lv.{snapshot['meta'].get('level') or '—'} · "
                f"{len(snapshot['dolls'])} 人形 / {len(snapshot['fairies'])} 妖精 / "
                f"{len(snapshot['sangvis'])} 融合势力 / {len(snapshot['equipment'])} 装备",
                flush=True,
            )
            if self.stop_after_index:
                self.done = True
        except Exception as exc:  # noqa: BLE001 - proxy addon must not crash
            print(f"[WARN] 解析响应失败：{type(exc).__name__}: {exc}", flush=True)


async def run_proxy(args) -> int:
    try:
        from mitmproxy import options
        from mitmproxy.tools.dump import DumpMaster
    except ImportError as exc:
        raise SystemExit(
            "缺少 mitmproxy；请运行 build.bat --with-android "
            "或 pip install -r requirements-android.txt"
        ) from exc

    ca_path = ensure_ca()
    out_dir = Path(args.out_dir).resolve()
    recorder = Recorder(
        out_dir,
        stop_after_index=not args.keep_running,
        static_key=args.static_key,
        initial_sign=args.sign,
    )
    opts = options.Options(
        listen_host=args.host,
        listen_port=args.port,
        confdir=str(ca_path.parent.parent / "confdir"),
        ssl_insecure=True,
    )
    master = DumpMaster(opts)
    master.addons.add(recorder)

    print("=" * 62)
    print("Gf1_AccountEval · Android 抓包")
    print("=" * 62)
    print(f"支持范围 : 正常登录并返回 uid/sign 的客户端")
    print(f"不支持   : 国服复活版 / PC 继承（sign 不在登录流程中返回）")
    print(f"代理端口 : {args.host}:{args.port}")
    print(f"模拟器代理: {_lan_ip()}:{args.port}")
    print(f"CA 证书  : {ca_path}")
    print("步骤：")
    print("  1. 模拟器 Wi-Fi 代理指向上面的 IP:端口（不要用 127.0.0.1）")
    print("  2. 安装 CA 证书（或重新运行时加 --push-ca，把证书推到 Download）")
    print("  3. 完全退出并重启游戏，重新登录到主界面")
    print("  4. 等本窗口出现 [SNAP]；按 Ctrl+C 停止")
    print("=" * 62, flush=True)
    if args.push_ca:
        _push_ca(ca_path)

    task = asyncio.create_task(master.run())
    started = time.monotonic()
    try:
        while not recorder.done and not task.done():
            if args.timeout and time.monotonic() - started >= args.timeout:
                print("[INFO] 抓包超时，停止代理。", flush=True)
                break
            await asyncio.sleep(0.4)
        if recorder.done:
            await asyncio.sleep(1.5)
        if not task.done():
            master.shutdown()
        await task
    except (KeyboardInterrupt, asyncio.CancelledError):
        master.shutdown()
        await asyncio.gather(task, return_exceptions=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--out-dir", default=str(ROOT / "snapshots"))
    parser.add_argument("--timeout", type=int, default=0, help="超时秒数；0 表示不超时")
    parser.add_argument("--static-key", default=STATIC_KEY, help="旧登录/明文包密钥，默认 yundoudou")
    parser.add_argument("--sign", help="当前登录 sign；有它时可直接解密 Index")
    parser.add_argument("--keep-running", action="store_true", help="抓到后不自动停止")
    parser.add_argument("--push-ca", action="store_true", help="通过 adb 推送 CA 到 Download")
    parser.add_argument("--from-index", type=Path, help="离线转换已保存的 Index JSON")
    parser.add_argument("--from-raw", type=Path, help="用 --sign 解密已保存的 # Index 原始响应")
    args = parser.parse_args()
    if not (1024 <= args.port <= 65535):
        parser.error("port 必须在 1024..65535")
    if args.from_raw:
        convert_raw(
            args.from_raw.resolve(),
            Path(args.out_dir).resolve(),
            sign=args.sign,
            static_key=args.static_key,
        )
        return 0
    if args.from_index:
        convert_index(args.from_index.resolve(), Path(args.out_dir).resolve())
        return 0
    try:
        return asyncio.run(run_proxy(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
