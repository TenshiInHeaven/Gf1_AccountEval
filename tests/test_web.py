from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def load_serve():
    spec = importlib.util.spec_from_file_location("gf_web_serve", WEB / "serve.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["gf_web_serve"] = module
    spec.loader.exec_module(module)
    return module


class WebAssetsTests(unittest.TestCase):
    def test_static_shell(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        for tab in ("components", "schemes", "codex", "settings"):
            self.assertIn(f'data-tab="{tab}"', index)
        self.assertIn("modules.js", index)
        self.assertTrue((WEB / "modules.js").is_file())
        self.assertTrue((WEB / "manifest.webmanifest").is_file())
        self.assertTrue((WEB / "sw.js").is_file())

    def test_built_data_counts(self):
        guihai = json.loads((WEB / "data" / "guihai_weapons.json").read_text(encoding="utf-8"))
        rows = 0
        for group in guihai["groups"]:
            for weapon in group["weapons"]:
                if weapon.get("mains"):
                    rows += sum(len(main.get("combos") or []) for main in weapon["mains"])
                else:
                    rows += len(weapon.get("combos") or [])
        self.assertEqual(rows, 183)

        qiushui = json.loads((WEB / "data" / "qiushui_components.json").read_text(encoding="utf-8"))
        tables = [table for activity in qiushui["activities"] for table in activity["tables"]]
        self.assertEqual(len(qiushui["activities"]), 8)
        self.assertEqual(len(tables), 21)
        self.assertEqual(sum(len(table["components"]) for table in tables), 189)

        components = json.loads((WEB / "data" / "components.json").read_text(encoding="utf-8"))
        self.assertEqual(len(components["components"]), 33)

        codex = json.loads((WEB / "data" / "component_codex.json").read_text(encoding="utf-8"))
        self.assertEqual(len(codex["components"]), 141)
        self.assertEqual(len(codex["roll_types"]), 17)
        self.assertTrue(any(item["attachments"] for item in codex["components"]))

    def test_core_manifest_covers_data(self):
        core = json.loads((WEB / "data" / "core.json").read_text(encoding="utf-8"))
        data_files = sorted(path.relative_to(WEB).as_posix() for path in (WEB / "data").rglob("*.json"))
        for name in data_files:
            if Path(name).name in ("core.json", "build_info.json"):
                continue
            self.assertIn(f"./{name}", core)
        self.assertIn("./app.js", core)
        self.assertIn("./modules.js", core)

    def test_serve_merges_components(self):
        serve = load_serve()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            account = folder / "account_20260101_000000.json"
            account.write_text(
                json.dumps({"meta": {"uid": "1", "nickname": "t"}, "dolls": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            index = folder / "index_20260101_000000.json"
            index.write_text(
                json.dumps(
                    {
                        "user_info": {"user_id": "1"},
                        "vehicle_component_with_user_info": {"a": {"component_id": "1001"}},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            payload = serve.merged_snapshot(account)
            self.assertIn("vehicle_component_with_user_info", payload)
            self.assertEqual(payload["meta"]["component_source"], "index_20260101_000000.json")
            self.assertEqual(serve.latest_account(folder), account)

    def test_serve_rejects_other_uid_index(self):
        serve = load_serve()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            account = folder / "account_20260101_000000.json"
            account.write_text(json.dumps({"meta": {"uid": "1"}}), encoding="utf-8")
            index = folder / "index_20260102_000000.json"
            index.write_text(
                json.dumps({"user_info": {"user_id": "2"}, "vehicle_component_with_user_info": {"a": {}}}),
                encoding="utf-8",
            )
            payload = serve.merged_snapshot(account)
            self.assertNotIn("vehicle_component_with_user_info", payload)


if __name__ == "__main__":
    unittest.main()
