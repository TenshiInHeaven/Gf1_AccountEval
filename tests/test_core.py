from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.capture.android import AndroidBridge, AndroidError, SNAPSHOT_CANDIDATES
from app.capture.live import parse_capture
from app.core.account import AccountLoader
from app.core.codex import get_codex
from app.core.equipment import get_equipment_engine
from app.core.normalize import normalize_name, slugify, type_label
from app.core.paths import SAMPLE_ACCOUNT
from app.core.ratings import Evaluator, grade_for
from app.core.ratings_io import export_bundle, validate_bundle
from app.core.tiers import get_tierlists


class NormalizeTests(unittest.TestCase):
    def test_name_variants(self):
        self.assertEqual(normalize_name("Px4 风暴"), normalize_name("Px4风暴"))
        self.assertEqual(normalize_name("M4 SOPMOD II"), normalize_name("M4SOPMODII"))
        self.assertEqual(normalize_name("维尔德MkⅡ"), normalize_name("维尔德MkII"))
        self.assertEqual(slugify("M4 SOPMOD II"), "M4_SOPMOD_II")

    def test_type_labels(self):
        self.assertEqual(type_label(4), "AR")
        self.assertEqual(type_label(6), "SG")


class CodexAndTierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex = get_codex()
        cls.tiers = get_tierlists()

    def test_codex_sizes(self):
        self.assertGreater(len(self.codex.dolls), 500)
        self.assertEqual(len(self.codex.fairies), 50)
        self.assertGreaterEqual(len(self.codex.sangvis), 50)

    def test_tier_resolution(self):
        self.assertEqual(self.tiers["doll"].tier_for(code="KP31", name="索米").id, "SS")
        self.assertEqual(self.tiers["fairy"].tier_for(code="airborne", name="空降妖精").id, "SS")
        self.assertEqual(self.tiers["sangvis"].tier_for(code="Scarecrow", name="稻草人").id, "SS")
        self.assertEqual(self.tiers["sangvis"].tier_for(code="Architect", name="建筑师").id, "B")

    def test_grade_thresholds(self):
        self.assertEqual(grade_for(95), "SS")
        self.assertEqual(grade_for(85), "S")
        self.assertEqual(grade_for(75), "A")
        self.assertEqual(grade_for(65), "B")
        self.assertEqual(grade_for(10), "C")


class SampleEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.account = AccountLoader().load(SAMPLE_ACCOUNT)
        cls.evaluation = Evaluator().evaluate(cls.account)

    def test_sample_kind_counts(self):
        self.assertEqual(len(self.account.dolls), 342)
        self.assertEqual(len(self.account.fairies), 38)
        self.assertEqual(len(self.account.sangvis), 10)

    def test_mod3_merges_with_prototype(self):
        payload = {
            "meta": {"uid": "1", "nickname": "test", "level": 1},
            "dolls": [
                {"uid": 1, "code": "M4A1", "level": 100},
                {"uid": 2, "code": "M4A1Mod", "level": 120, "mod": 3},
            ],
            "fairies": [],
            "equipment": [],
            "sangvis": [],
        }
        view = AccountLoader().from_payload(payload)
        m4a1 = next(unit for unit in view.dolls if unit.code == "M4A1")
        self.assertEqual(m4a1.count, 2)
        self.assertEqual(m4a1.level, 120)
        self.assertEqual(
            [copy["source_name"] for copy in m4a1.copies],
            ["M4A1（三改）", "M4A1"],
        )

    def test_fairy_copy_breakdown(self):
        airborne = next(unit for unit in self.account.fairies if unit.code == "airborne")
        self.assertEqual(airborne.count, 9)
        self.assertEqual(len(airborne.copies), 9)
        self.assertEqual(
            {quality: sum(1 for copy in airborne.copies if copy["quality"] == quality) for quality in (5, 3, 1)},
            {5: 2, 3: 1, 1: 6},
        )
        self.assertEqual(airborne.quality, 5)

    def test_dimensions_present(self):
        self.assertEqual(len(self.evaluation.dimensions()), 4)
        self.assertIn(self.evaluation.overall_grade, {"SS", "S", "A", "B", "C"})
        self.assertGreater(self.evaluation.doll.score, 0)
        self.assertGreater(self.evaluation.equipment.score, 0)

    def test_equipment_targets(self):
        report = self.account.equipment
        self.assertEqual(len(report.all_targets), 27)
        self.assertEqual(report.target_total, 361)
        by_name = report.by_name()
        self.assertEqual(by_name["光喵"].target, 27)
        self.assertEqual(by_name["高速"].target, 25)
        self.assertEqual(by_name["T骨"].target, 16)
        self.assertGreater(by_name["光喵"].current, 0)
        self.assertEqual(by_name["高穿（500穿）"].current, 0)

    def test_high_penetration_matches_500_penetration(self):
        report = get_equipment_engine().evaluate([{"info_id": 98}, {"info_id": 51}])
        high = next(item for item in report.all_targets if item.id == "ap_high")
        self.assertEqual(high.current, 1)


class AndroidBridgeTests(unittest.TestCase):
    def test_missing_adb_is_reported(self):
        bridge = AndroidBridge(adb_path=Path("Z:/definitely-missing/adb.exe"))
        self.assertFalse(bridge.available)
        with self.assertRaises(AndroidError):
            bridge.devices()

    def test_snapshot_contract(self):
        self.assertTrue(any("gf_account_snapshot.json" in path for path in SNAPSHOT_CANDIDATES))


class TierDataTests(unittest.TestCase):
    def test_sangvis_a_minus_and_image_aliases(self):
        tiers = get_tierlists()
        sangvis = tiers["sangvis"]
        self.assertIn("A-", {tier.id for tier in sangvis.tiers})
        self.assertEqual(sangvis.tier_for(name="钢狮").id, "A-")
        self.assertEqual(sangvis.tier_for(name="猎豹").id, "A-")
        self.assertEqual(sangvis.tier_for(name="EX狙").id, "A-")
        self.assertEqual(sangvis.tier_for(name="黑雷").id, "A-")
        self.assertEqual(sangvis.tier_for(name="万圣魔女").id, "A-")

    def test_carcano_a_minus_crown(self):
        dolls = get_tierlists()["doll"]
        self.assertEqual(dolls.tier_for(name="卡尔卡诺M91/38").id, "A-")
        self.assertTrue(dolls.is_crown(name="卡尔卡诺M91/38"))

    def test_ratings_bundle_contains_recommendation(self):
        bundle = export_bundle()
        validate_bundle(bundle)
        self.assertEqual(set(bundle["kinds"]), {"doll", "fairy", "sangvis"})
        doll = bundle["kinds"]["doll"]
        tps = next(item for item in doll["entries"] if item["name"] == "TPS")
        self.assertEqual(tps["recommend"], "gold")

    def test_frame_overrides(self):
        dolls = get_tierlists()["doll"]
        self.assertEqual(dolls.frame_for(name="NTW-20"), "A-")
        self.assertEqual(dolls.frame_for(name="TEC-9"), "A-")
        self.assertEqual(dolls.frame_for(name="MG3"), "A-")
        self.assertEqual(dolls.frame_for(name="佩克拉"), "A-")
        self.assertEqual(dolls.frame_for(name="AK15"), "A-")
        self.assertEqual(dolls.frame_for(name="M200"), "A-")
        self.assertEqual(dolls.frame_for(name="QBZ191"), "A-")
        self.assertEqual(dolls.frame_for(name="SPAS-12"), "S")
        self.assertEqual(dolls.frame_for(name="KLIN"), "Sp")
        self.assertTrue(dolls.is_recommended(name="TPS"))
        self.assertFalse(dolls.is_recommended(name="NTW-20"))
        self.assertEqual(dolls.recommend_level(name="TPS"), "gold")
        self.assertEqual(dolls.recommend_level(name="MG4"), "green")
        self.assertEqual(dolls.recommend_level(name="NTW-20"), "blue")
        self.assertEqual(dolls.recommend_level(name="卡尔卡诺M91/38"), "blue")
        self.assertEqual(dolls.recommend_level(name="KLIN"), "gray")
        sangvis = get_tierlists()["sangvis"]
        self.assertEqual(sangvis.frame_for(name="稻草人"), "SS")


class LiveParserTests(unittest.TestCase):
    def test_parse_sections(self):
        text = (
            "@@META\n"
            "userId\tname\tlevel\tmaxGun\tmaxSangvisGun\tmaxFairy\tmaxEquip\n"
            "123\t测试\t120\t500\t100\t60\t700\n"
            "@@ROSTER\n"
            "uid\tcode\tlevel\texp\tfavor\tteamId\tskinId\tlocation\tnumber\tmod\n"
            "1\tM4A1\t120\t1\t2\t1\t0\t0\t5\t3\n"
            "@@FAIRIES\n"
            "id\tcode\tlevel\texp\tqualityLevel\tmainSkillLevel\tmod\tmodExp\tteamId\tequipId\tisCollect\n"
            "1\tairborne_3\t100\t1\t5\t10\t0\t0\t0\t0\tfalse\n"
            "@@EQUIPMENT\n"
            "id\tgunId\tinfoId\townNumber\tequip_level\tequip_exp\n"
            "1\t2\t32\t0\t10\t1\n"
            "@@SANGVIS\n"
            "infoId\tcode\tlevel\tadvance\tresolutionLevel\tsign\tskin\tbreakThroughLevel\tchip1\tchip2\n"
            "1001\tScarecrow\t90\t4\t3\t1\t0\t0\t0\t0\n"
            "@@VEHICLES\n"
            "id\tinfoid\texp\tlife\n"
            "1\t1\t100\t4000\n"
        )
        payload = parse_capture(text)
        self.assertEqual(payload["meta"]["uid"], "123")
        self.assertEqual(len(payload["dolls"]), 1)
        self.assertEqual(len(payload["fairies"]), 1)
        self.assertEqual(len(payload["equipment"]), 1)
        self.assertEqual(len(payload["sangvis"]), 1)
        self.assertEqual(len(payload["vehicles"]), 1)


if __name__ == "__main__":
    unittest.main()
