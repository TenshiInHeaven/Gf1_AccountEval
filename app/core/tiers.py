"""Tier-list loading and resolution."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from .codex import Codex, get_codex
from .normalize import normalize_name
from .paths import TIER_DIR, read_json


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

    def __post_init__(self) -> None:
        self.tier_by_id = {tier.id: tier for tier in self.tiers}
        codex = get_codex()
        for entry in self.entries:
            tier_id = str(entry.get("tier") or self.default_tier)
            if tier_id not in self.tier_by_id:
                continue
            names = [entry.get("name", ""), *(entry.get("aliases") or [])]
            for name in names:
                norm = normalize_name(name)
                if norm:
                    self.name_tier.setdefault(norm, tier_id)
                for item in codex.by_norm.get(norm, []):
                    if item.kind == self.kind:
                        self.code_tier.setdefault((self.kind, item.code), tier_id)
                        if entry.get("crown"):
                            self.crown_codes.add((self.kind, item.code))
                if entry.get("crown") and norm:
                    self.crown_names.add(norm)
            explicit_code = str(entry.get("code") or "")
            if explicit_code:
                self.code_tier.setdefault((self.kind, explicit_code), tier_id)
                if entry.get("crown"):
                    self.crown_codes.add((self.kind, explicit_code))

    def is_crown(self, code: str = "", name: str = "") -> bool:
        if code and (self.kind, code) in self.crown_codes:
            return True
        return bool(name and normalize_name(name) in self.crown_names)

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
    payload = read_json(TIER_DIR / filename, {}) or {}
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
