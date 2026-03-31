from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3}(\D|$))")


def normalize_number_str(s: str) -> str:
    s2 = (s or "").strip()
    if s2 in ("", "--", "—", "–", "n/a", "na", "null"):
        return ""
    s2 = _THOUSANDS_RE.sub("", s2)
    return s2


def parse_int(s: str) -> int | None:
    s2 = normalize_number_str(s)
    if not s2:
        return None
    try:
        return int(float(s2))
    except Exception:
        return None


def parse_float(s: str) -> float | None:
    s2 = normalize_number_str(s)
    if not s2:
        return None
    # European decimal: "78,4" when no ASCII period is present
    if "," in s2 and "." not in s2:
        s2 = s2.replace(",", ".")
    try:
        return float(s2)
    except Exception:
        return None


def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def row_hash_from_normalized_row(normalized_row: dict[str, Any]) -> str:
    blob = stable_json(normalized_row).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def clean_str(v: Any) -> str:
    return ("" if v is None else str(v)).strip()

