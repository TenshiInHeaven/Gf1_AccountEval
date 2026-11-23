"""Static codex (all T-Dolls / fairies / Sangvis units) and lookup helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .normalize import normalize_name
from .paths import CODEX_DIR, PROJECT_ROOT, read_json


@dataclass
class CodexItem:
    kind: str
    id: int
    code: str
    name: str
    en_name: str = ""
    type: int = 0
    rank: int = 0
    avatar: str = ""
    aliases: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    @property
    def avatar_path(self) -> Path | None:
        if not self.avatar:
            return None
        path = PROJECT_ROOT / self.avatar
        return path if path.is_file() else None


class Codex:
    def __init__(self) -> None:
        self.dolls = self._dedupe(self._load("dolls.json", "doll"))
        self.fairies = self._dedupe(self._load("fairies.json", "fairy"))
        self.sangvis = self._dedupe(self._load("sangvis.json", "sangvis"))
        self.by_kind: dict[str, list[CodexItem]] = {
            "doll": self.dolls,
            "fairy": self.fairies,
            "sangvis": self.sangvis,
        }
        self.by_code: dict[tuple[str, str], CodexItem] = {}
        self.by_norm: dict[str, list[CodexItem]] = {}
        for kind, items in self.by_kind.items():
            for item in items:
                self.by_code[(kind, item.code)] = item
                for key in {item.code, item.name, item.en_name, *item.aliases}:
                    norm = normalize_name(key)
                    if not norm:
                        continue
                    bucket = self.by_norm.setdefault(norm, [])
                    if item not in bucket:
                        bucket.append(item)

    @staticmethod
    def _dedupe(items: list[CodexItem]) -> list[CodexItem]:
        seen: set[str] = set()
        result: list[CodexItem] = []
        for item in items:
            if item.code in seen:
                continue
            seen.add(item.code)
            result.append(item)
        return result

    @staticmethod
    def _load(filename: str, kind: str) -> list[CodexItem]:
        rows = read_json(CODEX_DIR / filename, []) or []
        result = []
        for row in rows:
            result.append(
                CodexItem(
                    kind=kind,
                    id=int(row.get("id") or 0),
                    code=str(row.get("code") or ""),
                    name=str(row.get("name") or row.get("code") or ""),
                    en_name=str(row.get("en_name") or ""),
                    type=int(row.get("type") or 0),
                    rank=int(row.get("rank") or 0),
                    avatar=str(row.get("avatar") or ""),
                    aliases=list(row.get("aliases") or []),
                    extra={
                        key: value
                        for key, value in row.items()
                        if key
                        not in {"kind", "id", "code", "name", "en_name", "type", "rank", "avatar", "aliases"}
                    },
                )
            )
        return result

    def get(self, kind: str, code: str = "", name: str = "") -> CodexItem | None:
        if code and (kind, code) in self.by_code:
            return self.by_code[(kind, code)]
        for key in (code, name):
            norm = normalize_name(key)
            if not norm:
                continue
            for item in self.by_norm.get(norm, []):
                if item.kind == kind:
                    return item
        return None

    def base_code(self, kind: str, code: str) -> str:
        """Map a doll's Mod3 code back to its prototype card."""
        value = self.canonical_code(kind, code)
        if kind == "doll" and value.endswith("Mod") and (kind, value[:-3]) in self.by_code:
            return value[:-3]
        return value

    def canonical_code(self, kind: str, code: str) -> str:
        """Resolve formatting variants such as ``AK-15_Mod`` / numeric ids."""
        raw = str(code or "").strip()
        item = self.get(kind, code=raw)
        if item is not None:
            return item.code
        norm = normalize_name(raw)
        for candidate in self.by_kind.get(kind, []):
            if normalize_name(candidate.code) == norm:
                return candidate.code
        if raw.isdigit():
            value = int(raw)
            for candidate in self.by_kind.get(kind, []):
                if candidate.id == value:
                    return candidate.code
            # Android CN reports modded dolls as 20000 + the base gun id
            # (e.g. AK-15's 20293) instead of the codex ``AK15Mod`` code.
            if kind == "doll" and value >= 20000:
                base_id = value - 20000
                base = next(
                    (candidate for candidate in self.by_kind[kind] if candidate.id == base_id),
                    None,
                )
                if base is not None:
                    mod = self.by_code.get((kind, f"{base.code}Mod"))
                    return mod.code if mod is not None else base.code
        return raw

    def is_mod_variant(self, kind: str, code: str) -> bool:
        return self.base_code(kind, code) != str(code or "")

    def is_deployable(self, kind: str, item: CodexItem) -> bool:
        """Filter story-only NPCs/allies that cannot be placed in a normal echelon."""
        code = str(item.code or "").lower()
        if code in {"isc"}:
            return False
        if code.startswith("npc_") or any(
            marker in code for marker in ("_npc", "_ally", "_motor", "_ogas")
        ):
            return False
        return True

    def find_all(self, kind: str, query: str) -> list[CodexItem]:
        norm = normalize_name(query)
        if not norm:
            return list(self.by_kind.get(kind, []))
        return [
            item
            for item in self.by_kind.get(kind, [])
            if norm in normalize_name(item.name)
            or norm in normalize_name(item.code)
            or norm in normalize_name(item.en_name)
        ]


@lru_cache(maxsize=1)
def get_codex() -> Codex:
    return Codex()
