"""Serve the PWA locally.

Usage:
    python web/serve.py
    python web/serve.py --host 0.0.0.0 --port 8770
"""
from __future__ import annotations

import argparse
import http.server
import socket
import socketserver
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".webp": "image/webp",
        ".webmanifest": "application/manifest+json",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        # Dev-friendly: let the service worker update immediately.  Offline
        # caching is still handled by sw.js.
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
    parser.add_argument("--open", action="store_true", help="打开默认浏览器")
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"GF Account Forge PWA: {url}")
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
