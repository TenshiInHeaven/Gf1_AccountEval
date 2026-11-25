"""Serve the PWA locally and expose the latest account snapshot.

Usage:
    python web/serve.py
    python web/serve.py --host 0.0.0.0 --port 8770
    python web/serve.py --snapshot-dir ..\\snapshots
"""
from __future__ import annotations

import argparse
import http.server
import json
import socket
import socketserver
import webbrowser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
DEFAULT_SNAPSHOT_DIR = ROOT.parent / "snapshots"


def latest_index(snapshot_dir: Path) -> Path | None:
    candidates = sorted(
        snapshot_dir.glob("index_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def snapshot_index(account_path: Path) -> Path | None:
    """``account_android_20261121_195839.json`` -> ``index_20261121_195839.json``."""
    name = account_path.name.replace("account_android_", "index_").replace("account_", "index_")
    candidate = account_path.parent / name
    return candidate if candidate.is_file() else None


def merged_snapshot(account_path: Path) -> dict:
    payload = json.loads(account_path.read_text(encoding="utf-8"))
    meta = payload.setdefault("meta", {})
    index_path = snapshot_index(account_path)
    if index_path is None:
        candidate = latest_index(account_path.parent)
        if candidate is not None:
            index = json.loads(candidate.read_text(encoding="utf-8"))
            index_uid = str((index.get("user_info") or {}).get("user_id") or "")
            if not index_uid or index_uid == str(meta.get("uid") or ""):
                index_path = candidate
    if index_path is not None:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        rows = index.get("vehicle_component_with_user_info")
        if rows:
            payload["vehicle_component_with_user_info"] = rows
        meta.setdefault("component_source", index_path.name)
        if index_path.stat().st_mtime < account_path.stat().st_mtime:
            meta["component_stale"] = True
    return payload


def latest_account(snapshot_dir: Path) -> Path | None:
    candidates = sorted(
        snapshot_dir.glob("account_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".webp": "image/webp",
        ".webmanifest": "application/manifest+json",
    }
    snapshot_dir = DEFAULT_SNAPSHOT_DIR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ------------------------------------------------------------------
    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 400) -> None:
        self._json({"ok": False, "error": message}, status)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/health":
            self._json({"ok": True, "service": "gf-account-forge", "snapshot_dir": str(self.snapshot_dir)})
            return
        if path == "/api/snapshots":
            rows = []
            for item in sorted(self.snapshot_dir.glob("account_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                stat = item.stat()
                rows.append({"name": item.name, "mtime": stat.st_mtime, "size": stat.st_size})
            self._json({"ok": True, "snapshots": rows[:50]})
            return
        if path == "/api/latest":
            latest = latest_account(self.snapshot_dir)
            if latest is None:
                self._error("snapshots 目录下没有 account_*.json", 404)
                return
            try:
                self._json(merged_snapshot(latest))
            except Exception as exc:  # pragma: no cover - defensive
                self._error(f"读取快照失败：{exc}", 500)
            return
        if path.startswith("/api/snapshot/"):
            name = path[len("/api/snapshot/"):]
            target = (self.snapshot_dir / name).resolve()
            if self.snapshot_dir.resolve() not in target.parents or not target.is_file():
                self._error("快照不存在", 404)
                return
            try:
                self._json(merged_snapshot(target))
            except Exception as exc:  # pragma: no cover
                self._error(f"读取快照失败：{exc}", 500)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f"[web] {self.address_string()} {fmt % args}")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_SNAPSHOT_DIR))
    parser.add_argument("--open", action="store_true", help="打开默认浏览器")
    args = parser.parse_args()
    Handler.snapshot_dir = Path(args.snapshot_dir).resolve()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"GF Account Forge PWA: {url}")
    print(f"snapshots: {Handler.snapshot_dir}")
    print(f"latest API: {url}api/latest")
    if args.host == "0.0.0.0":
        print(f"Android / LAN: http://{local_ip()}:{args.port}/")
        print("手机安装 PWA 需要 HTTPS 或 localhost；局域网 HTTP 只能预览，不能完整安装。")
    with Server((args.host, args.port), Handler) as httpd:
        if args.open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
