from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from app.capture.android_proxy import AndroidCaptureError, build_snapshot  # noqa: E402


class AndroidProxyConversionTests(unittest.TestCase):
    def test_index_payload_to_snapshot(self):
        payload = {
            "user_info": {
                "uid": "558472",
                "nickname": "测试指挥官",
                "level": 209,
                "maxGun": 540,
                "maxSangvisGun": 100,
                "maxFairy": 90,
                "maxEquip": 720,
            },
            "gun_with_user_info": [
                {
                    "id": 2763127,
                    "gun_id": 2,
                    "level": 100,
                    "exp": 3263300,
                    "favor": 100,
                    "team_id": 1,
                    "skin_id": 0,
                    "number": 1,
                    "mod": 3,
                }
            ],
            "fairy_with_user_info": [
                {
                    "id": 10001,
                    "fairy_id": 1,
                    "level": 90,
                    "quality_level": 5,
                    "main_skill_level": 10,
                    "team_id": 1,
                    "equip_id": 0,
                }
            ],
            "equip_with_user_info": [
                {"id": 20001, "info_id": 4, "own_number": 5, "equip_level": 10}
            ],
            "sangvis_with_user_info": [
                {
                    "info_id": 1001,
                    "level": 92,
                    "advance": 5,
                    "resolution_level": 0,
                    "skin": 1,
                }
            ],
        }
        snapshot = build_snapshot(payload, project_root=ROOT)
        self.assertEqual(snapshot["meta"]["uid"], "558472")
        self.assertEqual(snapshot["meta"]["nickname"], "测试指挥官")
        self.assertEqual(snapshot["meta"]["level"], 209)
        self.assertEqual(snapshot["dolls"][0]["code"], "M1911")
        self.assertEqual(snapshot["fairies"][0]["code"], "fighting")
        self.assertEqual(snapshot["sangvis"][0]["code"], "Scarecrow")
        self.assertEqual(snapshot["equipment"][0]["own_number"], 5)

    def test_targettrain_only_payload_is_rejected(self):
        with self.assertRaises(AndroidCaptureError):
            build_snapshot(
                {"targettrain_collect_user_info": [{"enemy_team_id": 1, "order_id": 1}]},
                project_root=ROOT,
            )

    def test_encrypted_index_flow_is_captured(self):
        try:
            from gflzirc import gf_authcode
        except ImportError:
            self.skipTest("gflzirc not installed (optional Android capture dependency)")
        from android_proxy_capture import Recorder

        payload = {
            "user_info": {"uid": "42", "nickname": "抓包测试", "level": 1},
            "gun_with_user_info": [{"id": 1, "gun_id": 2, "level": 10}],
        }
        body = "#" + gf_authcode(json.dumps(payload), "ENCODE", "yundoudou")

        class Response:
            def get_text(self, strict=False):
                return body

        class Request:
            pretty_url = "https://example.invalid/index.php/1000/Index/index"

        class Flow:
            request = Request()
            response = Response()

        with tempfile.TemporaryDirectory() as tmp:
            rec = Recorder(Path(tmp))
            rec.response(Flow())
            self.assertTrue(rec.done)
            files = list(Path(tmp).glob("account_android_*.json"))
            self.assertEqual(len(files), 1)
            snapshot = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(snapshot["meta"]["uid"], "42")
            self.assertEqual(snapshot["dolls"][0]["code"], "M1911")


if __name__ == "__main__":
    unittest.main()
