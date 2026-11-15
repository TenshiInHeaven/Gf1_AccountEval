"""Four-dimensional account evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field

from .account import AccountView, OwnedUnit
from .equipment import EquipmentTarget
from .tiers import Tier, get_tierlists


def grade_for(score: float) -> str:
    if score >= 90:
        return "SS"
    if score >= 80:
        return "S"
    if score >= 70:
        return "A"
    if score >= 60:
        return "B"
    return "C"


@dataclass
class DimensionRating:
    key: str
    title: str
    subtitle: str
    score: float
    grade: str
    counts: dict[str, int]
    owned: int
    total: int
    summary: str
    top_units: list[OwnedUnit] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class Evaluation:
    account: AccountView
    doll: DimensionRating
    fairy: DimensionRating
    sangvis: DimensionRating
    equipment: DimensionRating
    overall_score: float
    overall_grade: str
    recommendations: list[str]
    equipment_gaps: list[EquipmentTarget]

    def dimensions(self) -> list[DimensionRating]:
        return [self.doll, self.fairy, self.sangvis, self.equipment]


class Evaluator:
    def __init__(self) -> None:
        self.tiers = get_tierlists()

    def evaluate(self, account: AccountView) -> Evaluation:
        doll = self._unit_rating(
            "doll",
            account.dolls,
            title="人形强度",
            subtitle="仓库 / 三体人与常用好手",
            top_n=12,
            breadth_target=260,
            weight_depth=0.7,
        )
        fairy = self._unit_rating(
            "fairy",
            account.fairies,
            title="妖精强度",
            subtitle="空降 / T0-T2 战略妖精",
            top_n=6,
            breadth_target=41,
            weight_depth=0.75,
        )
        sangvis = self._unit_rating(
            "sangvis",
            account.sangvis,
            title="融合势力",
            subtitle="稻草人 / 铁血捕获单位",
            top_n=5,
            breadth_target=40,
            weight_depth=0.75,
        )
        equipment = self._equipment_rating(account)
        overall = (
            doll.score * 0.4
            + fairy.score * 0.2
            + sangvis.score * 0.2
            + equipment.score * 0.2
        )
        recommendations = self._recommendations(doll, fairy, sangvis, equipment)
        return Evaluation(
            account=account,
            doll=doll,
            fairy=fairy,
            sangvis=sangvis,
            equipment=equipment,
            overall_score=overall,
            overall_grade=grade_for(overall),
            recommendations=recommendations,
            equipment_gaps=account.equipment.gaps(6),
        )

    # ------------------------------------------------------------------
    def _unit_rating(
        self,
        kind: str,
        units: list[OwnedUnit],
        *,
        title: str,
        subtitle: str,
        top_n: int,
        breadth_target: int,
        weight_depth: float,
    ) -> DimensionRating:
        tierlist = self.tiers[kind]
        counts = tierlist.tier_counts()
        for unit in units:
            counts[unit.tier_id] = counts.get(unit.tier_id, 0) + 1
        ranked = sorted(units, key=lambda unit: (-unit.tier_score, -unit.level, unit.name))
        top = ranked[:top_n]
        depth = sum(unit.tier_score for unit in top) / len(top) if top else 0.0
        breadth = min(100.0, 100.0 * len(units) / max(1, breadth_target)) if units else 0.0
        score = depth * weight_depth + breadth * (1.0 - weight_depth)
        if not units:
            score = 0.0
        summary = self._unit_summary(kind, counts, units, score)
        return DimensionRating(
            key=kind,
            title=title,
            subtitle=subtitle,
            score=round(score, 1),
            grade=grade_for(score),
            counts=counts,
            owned=len(units),
            total=len(tierlist.entries),
            summary=summary,
            top_units=top,
        )

    def _unit_summary(self, kind: str, counts: dict[str, int], units: list[OwnedUnit], score: float) -> str:
        ss = counts.get("SS", 0)
        s = counts.get("S", 0)
        if not units:
            return "尚未提取到该分类的仓库数据。"
        if kind == "doll":
            return f"已拥有 {len(units)} 个不同人形；SS {ss} 名、S {s} 名。"
        if kind == "fairy":
            return f"已拥有 {len(units)} 种妖精；SS {ss} 种、S {s} 种。"
        return f"已记录 {len(units)} 个融合势力单位；SS {ss} 个、A {counts.get('A', 0)} 个。"

    # ------------------------------------------------------------------
    def _equipment_rating(self, account: AccountView) -> DimensionRating:
        report = account.equipment
        counts = {
            "ok": sum(1 for item in report.all_targets if item.state == "ok"),
            "warn": sum(1 for item in report.all_targets if item.state == "warn"),
            "low": sum(1 for item in report.all_targets if item.state == "low"),
        }
        score = report.score
        summary = (
            f"{report.current_total}/{report.target_total} 件目标储备"
            f"（完成度 {report.completion:.0f}%）；{counts['ok']} 项达标、{counts['low']} 项缺口较大。"
        )
        return DimensionRating(
            key="equipment",
            title="装备储备",
            subtitle="目标个数 vs 当前个数",
            score=round(score, 1),
            grade=grade_for(score),
            counts=counts,
            owned=report.current_total,
            total=report.target_total,
            summary=summary,
            extra={"report": report},
        )

    # ------------------------------------------------------------------
    def _recommendations(
        self,
        doll: DimensionRating,
        fairy: DimensionRating,
        sangvis: DimensionRating,
        equipment: DimensionRating,
    ) -> list[str]:
        tips: list[str] = []
        if doll.counts.get("SS", 0) == 0:
            tips.append("人形缺少 SS 级（三体人）：优先补齐 TPS / 索米 / SCAR 等核心。")
        elif doll.counts.get("SS", 0) < 3:
            tips.append(f"人形 SS 仅 {doll.counts.get('SS', 0)} 名，建议继续补强三体人深度。")
        if doll.counts.get("S", 0) < 8:
            tips.append("S 级常用好手不足 8 名，秃洞编队会吃紧。")
        if fairy.counts.get("SS", 0) == 0:
            tips.append("妖精缺少空降（T0/SS），优先把空降妖精纳入计划。")
        elif fairy.counts.get("S", 0) < 3:
            tips.append("T1 妖精深度偏浅，建议补护盾 / 狙击 / 海滩。")
        if sangvis.counts.get("SS", 0) == 0:
            tips.append("融合势力缺少稻草人（SS），策略位会明显受限。")
        report = equipment.extra["report"]
        for item in report.gaps(4):
            tips.append(f"装备缺口：{item.name} {item.current}/{item.target}（差 {item.gap}）。")
        if not tips:
            tips.append("四维均无明显短板，继续补图鉴与高难特化解即可。")
        return tips[:6]


def get_evaluator() -> Evaluator:
    return Evaluator()
