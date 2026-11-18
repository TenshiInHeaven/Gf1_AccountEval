"""Tier-list loading and resolution."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .codex import Codex, get_codex
from .normalize import normalize_name
from .paths import TIER_DIR, read_json

RECOMMEND_LEVELS = ("gold", "green", "blue", "white", "gray")
_RECOMMEND_ALIASES = {
    "gold": "gold",
    "金": "gold",
    "金色": "gold",
    "green": "green",
    "绿": "green",
    "绿色": "green",
    "blue": "blue",
    "蓝": "blue",
    "蓝色": "blue",
    "white": "white",
    "白": "white",
    "白色": "white",
    "gray": "gray",
    "grey": "gray",
    "灰": "gray",
    "灰色": "gray",
}


def normalize_recommend(value) -> str | None:
    if value is True:
        return "gold"
    if value is False or value is None:
        return "gray"
    key = str(value).strip().lower()
    return _RECOMMEND_ALIASES.get(key)


@dataclass(frozen=True)
class Tier:
    id: str
    label: str
    name: str
    color: str
    score: int


@dataclass
class TierList:
    kind: str
    title: str
    version: str
    source: str
    note: str
    tiers: list[Tier]
    entries: list[dict]
    default_tier: str = "C"
    tier_by_id: dict[str, Tier] = field(default_factory=dict)
    code_tier: dict[tuple[str, str], str] = field(default_factory=dict)
    name_tier: dict[str, str] = field(default_factory=dict)
    crown_codes: set[tuple[str, str]] = field(default_factory=set)
    crown_names: set[str] = field(default_factory=set)
    frame_overrides: dict[str, str] = field(default_factory=dict)
    recommend_overrides: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.tier_by_id = {tier.id: tier for tier in self.tiers}
        codex = get_codex()
        for entry in self.entries:
            tier_id = str(entry.get("tier") or self.default_tier)
            if tier_id not in self.tier_by_id:
                continue
            names = [entry.get("name", ""), *(entry.get("aliases") or [])]
            frame = str(entry.get("frame") or "").strip()
            has_recommend = "recommend" in entry
            recommend = normalize_recommend(entry.get("recommend")) if has_recommend else None
            for name in names:
                norm = normalize_name(name)
                if norm:
                    self.name_tier.setdefault(norm, tier_id)
                    if frame:
                        self.frame_overrides[norm] = frame
                    if recommend is not None:
                        self.recommend_overrides[norm] = recommend
                for item in codex.by_norm.get(norm, []):
                    if item.kind == self.kind:
                        self.code_tier.setdefault((self.kind, item.code), tier_id)
                        if entry.get("crown"):
                            self.crown_codes.add((self.kind, item.code))
                        if frame:
                            self.frame_overrides[normalize_name(item.code)] = frame
                        if recommend is not None:
                            self.recommend_overrides[normalize_name(item.code)] = recommend
                if entry.get("crown") and norm:
                    self.crown_names.add(norm)
            explicit_code = str(entry.get("code") or "")
            if explicit_code:
                self.code_tier.setdefault((self.kind, explicit_code), tier_id)
                if entry.get("crown"):
                    self.crown_codes.add((self.kind, explicit_code))
                if frame:
                    self.frame_overrides[normalize_name(explicit_code)] = frame
                if recommend is not None:
                    self.recommend_overrides[normalize_name(explicit_code)] = recommend

    def is_crown(self, code: str = "", name: str = "") -> bool:
        if code and (self.kind, code) in self.crown_codes:
            return True
        return bool(name and normalize_name(name) in self.crown_names)

    def frame_for(self, code: str = "", name: str = "") -> str:
        """Return a frame key (tier id or explicit override)."""
        for value in (code, name):
            norm = normalize_name(value)
            if norm and norm in self.frame_overrides:
                return self.frame_overrides[norm]
        return self.tier_for(code=code, name=name).id

    def recommend_level(self, code: str = "", name: str = "") -> str:
        """Gold / green / blue / white / gray recommendation surface."""
        for value in (code, name):
            norm = normalize_name(value)
            if norm and norm in self.recommend_overrides:
                return self.recommend_overrides[norm]
        tier = self.tier_for(code=code, name=name).id
        if tier == "SS":
            return "gold"
        if tier == "S":
            return "blue" if self.frame_for(code=code, name=name) == "A-" else "green"
        if tier in ("A-", "A"):
            return "blue"
        if tier == "B":
            return "white"
        return "gray"

    def is_recommended(self, code: str = "", name: str = "") -> bool:
        """Backward-compatible boolean for older callers/tests."""
        return self.recommend_level(code=code, name=name) in ("gold", "green")

    def tier_for(self, code: str = "", name: str = "") -> Tier:
        tier_id = self.code_tier.get((self.kind, code))
        if tier_id is None:
            tier_id = self.name_tier.get(normalize_name(name))
        if tier_id is None:
            tier_id = self.default_tier
        return self.tier_by_id.get(tier_id) or self.tier_by_id[self.default_tier]

    def tier_counts(self) -> dict[str, int]:
        return {tier.id: 0 for tier in self.tiers}

    def ordered(self) -> list[Tier]:
        return list(self.tiers)


def _load(kind: str, filename: str, codex: Codex) -> TierList:
    base = TIER_DIR / filename
    local = TIER_DIR / f"{Path(filename).stem}.local.json"
    payload = None
    if os.environ.get("GF1_IGNORE_LOCAL_RATINGS") != "1":
        payload = read_json(local, None)
    if not isinstance(payload, dict) or not isinstance(payload.get("tiers"), list):
        payload = read_json(base, {}) or {}
    tiers = [
        Tier(
            id=str(row["id"]),
            label=str(row.get("label") or row["id"]),
            name=str(row.get("name") or ""),
            color=str(row.get("color") or "#7C8896"),
            score=int(row.get("score") or 0),
        )
        for row in payload.get("tiers", [])
    ]
    return TierList(
        kind=kind,
        title=str(payload.get("title") or filename),
        version=str(payload.get("version") or ""),
        source=str(payload.get("source") or ""),
        note=str(payload.get("note") or ""),
        tiers=tiers,
        entries=list(payload.get("entries") or []),
        default_tier=str(payload.get("default_tier") or "C"),
    )


@lru_cache(maxsize=1)
def get_tierlists() -> dict[str, TierList]:
    codex = get_codex()
    return {
        "doll": _load("doll", "dolls.json", codex),
        "fairy": _load("fairy", "fairies.json", codex),
        "sangvis": _load("sangvis", "sangvis.json", codex),
    }
