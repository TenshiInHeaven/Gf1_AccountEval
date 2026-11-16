from __future__ import annotations

import unittest
from pathlib import Path

from app.capture.android_proxy_session import REGIONS, available_port
from app.ui.help_dialog import parse_help


class AndroidProxySessionTests(unittest.TestCase):
    def test_region_profiles(self):
        self.assertTrue(REGIONS["tw"].packages)
        self.assertFalse(REGIONS["tw"].bridge)
        self.assertFalse(REGIONS["tw"].fresh_login)
        self.assertTrue(REGIONS["cn_revival"].bridge)
        self.assertTrue(REGIONS["cn_revival"].fresh_login)
        self.assertFalse(REGIONS["cn_revival"].needs_ca)

    def test_free_port(self):
        port = available_port(18080)
        self.assertGreaterEqual(port, 18080)
        self.assertLess(port, 18160)


class HelpDocumentTests(unittest.TestCase):
    def test_help_has_expected_tabs(self):
        text = (Path(__file__).resolve().parents[1] / "HELP.md").read_text(encoding="utf-8")
        sections = parse_help(text)
        titles = [section.title for section in sections]
        self.assertEqual(len(sections), 5)
        self.assertIn("一、正常使用流程（PC）", titles)
        self.assertIn("二、安卓端流程", titles)
        android = next(section for section in sections if "安卓" in section.title)
        self.assertTrue(android.children)
        self.assertTrue(any("2.2" in child.title for child in android.children))


if __name__ == "__main__":
    unittest.main()
