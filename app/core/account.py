"""Account snapshot parsing and aggregation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .codex import CodexItem, get_codex
from .equipment import EquipmentReport, get_equipment_engine
from .paths import read_json
from .tiers import Tier, get_tierlists


@dataclass
class OwnedUnit:
    kind: str
    code: str
    name: str
    type: int
    rank: int
    level: int = 0
    mod: int = 0
    count: int = 1
    favor: int = 0
    quality: int = 0
    skill_level: int = 0
    advance: int = 0
    resolution_level: int = 0
    team_id: int = 0
    item: CodexItem | None = None
    tier: Tier | None = None
    copies: list[dict] = field(default_factory=list)

    @property
    def avatar_path(self) -> Path | None:
        return self.item.avatar_path if self.item else None

    @property
    def tier_id(self) -> str:
        return self.tier.id if self.tier else "C"

    @property
    def tier_label(self) -> str:
        return self.tier.label if self.tier else "C"

    @property
    def tier_color(self) -> str:
        return self.tier.color if self.tier else "#7C8896"

    @property
    def tier_score(self) -> int:
        return self.tier.score if self.tier else 40


@dataclass
class AccountView:
    meta: dict
    dolls: list[OwnedUnit]
    fairies: list[OwnedUnit]
    sangvis: list[OwnedUnit]
    equipment: EquipmentReport
    teams: list[dict] = field(default_factory=list)
    squads: list[dict] = field(default_factory=list)
    vehicles: list[dict] = field(default_factory=list)
    source_path: Path | None = None

    @property
    def uid(self) -> str:
        return str(self.meta.get("uid") or "未知")

    @property
    def nickname(self) -> str:
        return str(self.meta.get("nickname") or "未命名指挥官")

    @property
    def level(self) -> str:
        return str(self.meta.get("level") or "")

    @property
    def captured_at(self) -> str:
        return str(self.meta.get("captured_at") or "")

    @property
    def source(self) -> str:
        return str(self.meta.get("source") or "")

    def units(self, kind: str) -> list[OwnedUnit]:
        return {"doll": self.dolls, "fairy": self.fairies, "sangvis": self.sangvis}[kind]

    def owned_codes(self, kind: str) -> set[str]:
        return {unit.code for unit in self.units(kind)}

    def doll_type_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for unit in self.dolls:
            counts[unit.type] = counts.get(unit.type, 0) + 1
        return counts


class SnapshotError(ValueError):
    pass


def _int(value, default=0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


class AccountLoader:
    def __init__(self) -> None:
        self.codex = get_codex()
        self.tiers = get_tierlists()
        self.equipment_engine = get_equipment_engine()

    def load(self, path: Path) -> AccountView:
        payload = read_json(path)
        if not isinstance(payload, dict):
            raise SnapshotError(f"快照不是 JSON 对象：{path}")
        return self.from_payload(payload, source_path=path)

    def from_payload(self, payload: dict, source_path: Path | None = None) -> AccountView:
        meta = dict(payload.get("meta") or {})
        dolls = self._dolls(payload.get("dolls") or [])
        fairies = self._fairies(payload.get("fairies") or [])
        sangvis = self._sangvis(payload.get("sangvis") or [])
        equipment = self.equipment_engine.evaluate(payload.get("equipment") or [])
        return AccountView(
            meta=meta,
            dolls=dolls,
            fairies=fairies,
            sangvis=sangvis,
            equipment=equipment,
            teams=list(payload.get("teams") or []),
            squads=list(payload.get("squads") or []),
            vehicles=list(payload.get("vehicles") or []),
            source_path=source_path,
        )

    # ------------------------------------------------------------------
    def _unit(self, kind: str, code: str, name: str = "", **kwargs) -> OwnedUnit:
        item = self.codex.get(kind, code=code, name=name or code)
        if item is not None:
            code = item.code
            name = item.name
        else:
            name = name or code
        tier = self.tiers[kind].tier_for(code=code, name=name)
        return OwnedUnit(
            kind=kind,
            code=code,
            name=name,
            type=int(item.type if item else 0),
            rank=int(item.rank if item else 0),
            item=item,
            tier=tier,
            **kwargs,
        )

    def _dolls(self, rows: list[dict]) -> list[OwnedUnit]:
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            code = str(row.get("code") or "").strip()
            if code:
                grouped.setdefault(code, []).append(row)
        result = []
        for code, items in grouped.items():
            ordered = sorted(
                items,
                key=lambda row: (_int(row.get("level")), _int(row.get("mod"))),
                reverse=True,
            )
            best = ordered[0]
            copies = [
                {
                    "uid": _int(row.get("uid")),
                    "level": _int(row.get("level")),
                    "mod": _int(row.get("mod")),
                    "favor": _int(row.get("favor")),
                    "team_id": _int(row.get("team_id") or row.get("teamId")),
                    "skin_id": _int(row.get("skin_id") or row.get("skinId")),
                    "location": _int(row.get("location")),
                }
                for row in ordered
            ]
            result.append(
                self._unit(
                    "doll",
                    code,
                    level=_int(best.get("level")),
                    mod=_int(best.get("mod")),
                    count=len(items),
                    favor=max(_int(row.get("favor")) for row in items),
                    team_id=max(_int(row.get("team_id") or row.get("teamId")) for row in items),
                    copies=copies,
                )
            )
        result.sort(key=lambda unit: (-unit.tier_score, -unit.level, unit.name))
        return result

    def _fairies(self, rows: list[dict]) -> list[OwnedUnit]:
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            base = re.sub(r"_\d+$", "", code)
            grouped.setdefault(base, []).append(row)
        result = []
        for base, items in grouped.items():
            ordered = sorted(
                items,
                key=lambda row: (
                    _int(row.get("quality") or row.get("qualityLevel")),
                    _int(row.get("level")),
                    _int(row.get("skill_level") or row.get("mainSkillLevel")),
                ),
                reverse=True,
            )
            best = ordered[0]
            copies = [
                {
                    "id": _int(row.get("id")),
                    "source_code": str(row.get("code") or ""),
                    "level": _int(row.get("level")),
                    "quality": _int(row.get("quality") or row.get("qualityLevel")),
                    "skill_level": _int(row.get("skill_level") or row.get("mainSkillLevel")),
                    "mod": _int(row.get("mod")),
                    "team_id": _int(row.get("team_id") or row.get("teamId")),
                    "equip_id": _int(row.get("equip_id") or row.get("equipId")),
                }
                for row in ordered
            ]
            result.append(
                self._unit(
                    "fairy",
                    base,
                    level=_int(best.get("level")),
                    quality=_int(best.get("quality") or best.get("qualityLevel")),
                    skill_level=_int(best.get("skill_level") or best.get("mainSkillLevel")),
                    mod=_int(best.get("mod")),
                    count=len(items),
                    team_id=max(_int(row.get("team_id") or row.get("teamId")) for row in items),
                    copies=copies,
                )
            )
        result.sort(key=lambda unit: (-unit.tier_score, -unit.quality, -unit.level, unit.name))
        return result

    def _sangvis(self, rows: list[dict]) -> list[OwnedUnit]:
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            code = str(row.get("code") or "").strip()
            if code:
                grouped.setdefault(code, []).append(row)
        result = []
        for code, items in grouped.items():
            ordered = sorted(
                items,
                key=lambda row: (_int(row.get("level")), _int(row.get("advance"))),
                reverse=True,
            )
            best = ordered[0]
            copies = [
                {
                    "info_id": _int(row.get("info_id") or row.get("infoId")),
                    "level": _int(row.get("level")),
                    "advance": _int(row.get("advance")),
                    "resolution_level": _int(row.get("resolution_level") or row.get("resolutionLevel")),
                    "team_id": _int(row.get("team_id") or row.get("teamId")),
                    "sign": _int(row.get("sign")),
                }
                for row in ordered
            ]
            result.append(
                self._unit(
                    "sangvis",
                    code,
                    level=_int(best.get("level")),
                    advance=_int(best.get("advance")),
                    resolution_level=_int(best.get("resolution_level") or best.get("resolutionLevel")),
                    count=len(items),
                    team_id=_int(best.get("team_id") or best.get("teamId")),
                    copies=copies,
                )
            )
        result.sort(key=lambda unit: (-unit.tier_score, -unit.level, unit.name))
        return result
