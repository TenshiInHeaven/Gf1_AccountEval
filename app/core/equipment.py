"""Equipment target-vs-current accounting."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from .paths import DATA_DIR, PROJECT_ROOT, read_json, write_json


@dataclass(frozen=True)
class EquipmentItem:
    id: int
    name: str
    category: int
    type: int
    code: str
    rank: int
    armor_piercing: int = 0


@dataclass
class EquipmentTarget:
    id: str
    name: str
    target: int
    current: int = 0

    @property
    def gap(self) -> int:
        return max(0, self.target - self.current)

    @property
    def pct(self) -> float:
        return 0.0 if self.target <= 0 else min(100.0, 100.0 * self.current / self.target)

    @property
    def state(self) -> str:
        if self.current >= self.target:
            return "ok"
        if self.current >= self.target * 0.6:
            return "warn"
        return "low"


@dataclass
class EquipmentCategory:
    id: str
    name: str
    weight: float
    targets: list[EquipmentTarget] = field(default_factory=list)

    @property
    def target_total(self) -> int:
        return sum(item.target for item in self.targets)

    @property
    def current_total(self) -> int:
        return sum(min(item.current, item.target) for item in self.targets)

    @property
    def completion(self) -> float:
        total = self.target_total
        return 0.0 if total <= 0 else 100.0 * self.current_total / total


@dataclass
class EquipmentReport:
    categories: list[EquipmentCategory]
    score: float
    target_total: int
    current_total: int

    @property
    def completion(self) -> float:
        return 0.0 if self.target_total <= 0 else 100.0 * self.current_total / self.target_total

    @property
    def all_targets(self) -> list[EquipmentTarget]:
        return [item for category in self.categories for item in category.targets]

    def by_name(self) -> dict[str, EquipmentTarget]:
        return {item.name: item for item in self.all_targets}

    def gaps(self, limit: int = 8) -> list[EquipmentTarget]:
        return sorted(
            (item for item in self.all_targets if item.gap > 0),
            key=lambda item: (-(item.gap / max(1, item.target)), item.gap),
        )[:limit]


def _stat_max(value) -> int:
    """Read the upper value from an STC stat such as ``110,120``."""
    try:
        parts = [int(float(part.strip())) for part in str(value or "").split(",") if part.strip()]
    except ValueError:
        return 0
    return max(parts) if parts else 0


EQUIPMENT_TARGETS_FILE = DATA_DIR / "equipment_targets.json"
EQUIPMENT_OVERRIDE_FILE = PROJECT_ROOT / "equipment_rules.local.json"


def load_equipment_payload() -> dict:
    """Load the user override when valid, otherwise the bundled defaults."""
    override = read_json(EQUIPMENT_OVERRIDE_FILE, None)
    if isinstance(override, dict) and isinstance(override.get("categories"), list):
        return override
    return read_json(EQUIPMENT_TARGETS_FILE, {}) or {}


def save_equipment_payload(payload: dict) -> None:
    write_json(EQUIPMENT_OVERRIDE_FILE, payload)


def reset_equipment_payload() -> None:
    try:
        EQUIPMENT_OVERRIDE_FILE.unlink()
    except FileNotFoundError:
        pass


def reset_equipment_engine() -> None:
    get_equipment_engine.cache_clear()


def _matches(item: EquipmentItem, rule: dict) -> bool:
    if "category" in rule and item.category != int(rule["category"]):
        return False
    if "type" in rule and item.type != int(rule["type"]):
        return False
    if "armor_piercing_min" in rule and item.armor_piercing < int(rule["armor_piercing_min"]):
        return False
    if "armor_piercing_max" in rule and item.armor_piercing > int(rule["armor_piercing_max"]):
        return False
    code = item.code.lower()
    name = item.name.lower()
    for key in ("code_contains", "name_contains"):
        value = str(rule.get(key) or "").lower()
        if value and value not in (code if key.startswith("code") else name):
            return False
    for key in ("code_not_contains", "name_not_contains"):
        value = str(rule.get(key) or "").lower()
        if value and value in (code if key.startswith("code") else name):
            return False
    for value in rule.get("name_not_contains_any") or []:
        if str(value).lower() in name:
            return False
    return True


class EquipmentEngine:
    def __init__(self) -> None:
        self.items = [
            EquipmentItem(
                id=int(row["id"]),
                name=str(row.get("name") or ""),
                category=int(row.get("category") or 0),
                type=int(row.get("type") or 0),
                code=str(row.get("code") or ""),
                rank=int(row.get("rank") or 0),
                armor_piercing=_stat_max(row.get("armor_piercing")),
            )
            for row in (read_json(DATA_DIR / "equipment_items.json", []) or [])
        ]
        self.by_id = {item.id: item for item in self.items}
        payload = load_equipment_payload()
        self.title = str(payload.get("title") or "装备需求")
        self.source = str(payload.get("source") or "")
        self.note = str(payload.get("note") or "")
        self.categories: list[EquipmentCategory] = []
        for cat in payload.get("categories", []):
            category = EquipmentCategory(
                id=str(cat.get("id") or ""),
                name=str(cat.get("name") or ""),
                weight=float(cat.get("weight") or 0),
            )
            for row in cat.get("items", []):
                category.targets.append(
                    EquipmentTarget(
                        id=str(row.get("id") or ""),
                        name=str(row.get("name") or ""),
                        target=int(row.get("target") or 0),
                    )
                )
            self.categories.append(category)
        # Precompute item -> target hits.
        self._hits: dict[int, list[tuple[EquipmentCategory, EquipmentTarget]]] = {}
        for category in self.categories:
            for target in category.targets:
                rule = next(
                    (
                        row.get("match", {})
                        for cat in payload.get("categories", [])
                        if str(cat.get("id")) == category.id
                        for row in cat.get("items", [])
                        if str(row.get("id")) == target.id
                    ),
                    {},
                )
                for item in self.items:
                    if _matches(item, rule):
                        self._hits.setdefault(item.id, []).append((category, target))

    def evaluate(self, equipment_rows: list[dict]) -> EquipmentReport:
        categories = [
            EquipmentCategory(
                id=category.id,
                name=category.name,
                weight=category.weight,
                targets=[EquipmentTarget(id=item.id, name=item.name, target=item.target) for item in category.targets],
            )
            for category in self.categories
        ]
        lookup = {(category.id, target.id): target for category in categories for target in category.targets}
        for row in equipment_rows:
            info_id = int(row.get("info_id") or row.get("infoId") or 0)
            for category, target in self._hits.get(info_id, []):
                key = (category.id, target.id)
                if key in lookup:
                    lookup[key].current += 1
        total_target = sum(target.target for target in lookup.values())
        total_current = sum(min(target.current, target.target) for target in lookup.values())
        score = 0.0
        if total_target > 0:
            for category in categories:
                if category.target_total:
                    score += category.weight * category.completion
            weight_sum = sum(category.weight for category in categories if category.target_total) or 1.0
            score /= weight_sum
        return EquipmentReport(
            categories=categories,
            score=score,
            target_total=total_target,
            current_total=total_current,
        )


@lru_cache(maxsize=1)
def get_equipment_engine() -> EquipmentEngine:
    return EquipmentEngine()
