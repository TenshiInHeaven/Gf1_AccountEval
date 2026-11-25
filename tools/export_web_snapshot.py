"""Merge the latest account snapshot with its vehicle-component index.

The PWA only needs one JSON file.  The Qt app stores roster data in
``snapshots/account_*.json`` and vehicle components in ``snapshots/index_*.json``;
this tool (and ``web/serve.py /api/latest``) merges them.

    python tools/export_web_snapshot.py
    python tools/export_web_snapshot.py --account snapshots/account_android_xxx.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "snapshots"


def snapshot_index(account_path: Path) -> Path | None:
    name = account_path.name.replace("account_android_", "index_").replace("account_", "index_")
    candidate = account_path.parent / name
    return candidate if candidate.is_file() else None


def latest_index(folder: Path) -> Path | None:
    candidates = sorted(folder.glob("index_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def merged(account_path: Path) -> dict:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", help="account_*.json path; default: latest")
    parser.add_argument("--out", default=str(ROOT / "exports" / "web_snapshot.json"))
    args = parser.parse_args()
    if args.account:
        account_path = Path(args.account)
    else:
        candidates = sorted(SNAPSHOTS.glob("account_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise SystemExit("snapshots/ 下没有 account_*.json")
        account_path = candidates[0]
    payload = merged(account_path)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    components = payload.get("vehicle_component_with_user_info") or {}
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
    print(f"account: {account_path.name} · components: {len(components)} · meta: {payload.get('meta')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
