"""Shared normalization helpers for names, codes and slugs."""
from __future__ import annotations

import re
import unicodedata


_ROMAN = str.maketrans({"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V", "Ⅵ": "VI"})


def normalize_name(value: object) -> str:
    """Normalize a unit name for cross-source matching.

    Handles full-width characters, roman numerals, punctuation, whitespace and
    case differences.  Examples: ``Px4 风暴`` / ``Px4风暴`` / ``Px4\u00a0风暴``
    all collapse to the same key, as do ``M4 SOPMOD II`` and ``M4SOPMODII``.
    """
    text = unicodedata.normalize("NFKC", str(value or "")).translate(_ROMAN).lower()
    text = text.replace("&", "and")
    text = re.sub(r"[\s\-_·.,:;'/\\()\[\]{}（）【】、，。：；“”‘’!?！？★☆]", "", text)
    return text


def slugify(value: object) -> str:
    """Filesystem-safe, stable slug used for avatar file names."""
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = text.replace("&", "and")
    text = re.sub(r"[\\/:*?\"<>|\s]+", "_", text)
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_.-]", "", text)
    return text.strip("._") or "unknown"


def type_label(type_id: object) -> str:
    labels = {"1": "HG", "2": "SMG", "3": "RF", "4": "AR", "5": "MG", "6": "SG"}
    return labels.get(str(type_id), "其他")


def type_name_cn(type_id: object) -> str:
    labels = {"1": "手枪", "2": "冲锋枪", "3": "步枪", "4": "突击步枪", "5": "机枪", "6": "霰弹枪"}
    return labels.get(str(type_id), "其他")
