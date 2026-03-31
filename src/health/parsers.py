from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.health.normalization import (
    clean_str,
    parse_float,
    parse_int,
    row_hash_from_normalized_row,
    stable_json,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedHealthRow:
    date: str  # YYYY-MM-DD (already in user tz)
    source: str
    row_type: str
    metrics: dict[str, Any]
    raw_row: dict[str, Any]
    confidence: dict[str, float] | None
    normalized_row_for_hash: dict[str, Any]

    @property
    def row_hash(self) -> str:
        return row_hash_from_normalized_row(self.normalized_row_for_hash)


def detect_source_from_csv_header(header: Iterable[str]) -> str | None:
    cols = {c.strip().lower() for c in header if c}
    # Garmin Activities.csv (common columns)
    if "activity type" in cols and "date" in cols and ("distance" in cols or "calories" in cols):
        return "garmin"
    # FatSecret exports vary; heuristics
    if ("food" in cols or "food name" in cols or "item" in cols) and ("calories" in cols or "kcal" in cols):
        return "fatsecret"
    # Arboleaf exports vary
    if ("weight" in cols or "weight(kg)" in cols or "body fat" in cols or "fat%" in cols) and ("date" in cols or "time" in cols):
        return "arboleaf"
    return None


def parse_garmin_activities_csv(csv_bytes: bytes, user_tz: str) -> list[ParsedHealthRow]:
    """
    Parse Garmin Connect Activities.csv (activity feed).
    For now we interpret Garmin 'Date' as local/user timezone and take YYYY-MM-DD.
    """
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out: list[ParsedHealthRow] = []
    for row in reader:
        raw = {k: v for k, v in (row or {}).items()}
        date_raw = clean_str(raw.get("Date"))
        if not date_raw:
            continue
        # Typical: 2026-03-16 06:45:12
        date_part = date_raw.split(" ")[0]
        try:
            datetime.strptime(date_part, "%Y-%m-%d")
        except Exception:
            continue

        distance = parse_float(clean_str(raw.get("Distance")))
        # Garmin distance may be in miles depending on locale; we assume km if value is clearly metric?
        # MVP: treat as km when header says "Distance" with no unit; keep as provided and store in distance_km.
        calories = parse_int(clean_str(raw.get("Calories")))
        steps = parse_int(clean_str(raw.get("Steps")))
        avg_hr = parse_int(clean_str(raw.get("Avg HR")))
        moving_time = clean_str(raw.get("Time")) or clean_str(raw.get("Moving Time"))

        metrics: dict[str, Any] = {}
        if steps is not None:
            metrics["steps"] = steps
        if distance is not None:
            metrics["distance_km"] = float(distance)
        if calories is not None:
            metrics["active_calories_kcal"] = calories
        if avg_hr is not None:
            metrics["avg_hr_bpm"] = avg_hr
        if moving_time:
            metrics["time_str"] = moving_time

        norm_for_hash = {
            "date": date_part,
            "source": "garmin",
            "row_type": "activity",
            "raw": raw,
            "metrics": metrics,
        }

        out.append(
            ParsedHealthRow(
                date=date_part,
                source="garmin",
                row_type="activity",
                metrics=metrics,
                raw_row=raw,
                confidence=None,
                normalized_row_for_hash=jsonable_norm(norm_for_hash),
            )
        )
    return out


def parse_fatsecret_csv(csv_bytes: bytes, user_tz: str) -> list[ParsedHealthRow]:
    """
    Parse FatSecret CSV export.
    We aim to capture full food item list (per-item).
    Since export formats vary, we use best-effort column mapping.
    """
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out: list[ParsedHealthRow] = []

    def get_any(raw: dict[str, Any], *keys: str) -> str:
        for k in keys:
            if k in raw and raw.get(k) not in (None, ""):
                return clean_str(raw.get(k))
        # case-insensitive lookup
        lower = {str(k).lower(): k for k in raw}
        for k in keys:
            lk = k.lower()
            if lk in lower:
                return clean_str(raw.get(lower[lk]))
        return ""

    for row in reader:
        raw = {k: v for k, v in (row or {}).items()}
        date_raw = get_any(raw, "Date", "date", "Day")
        if not date_raw:
            continue
        date_part = date_raw.split(" ")[0]
        try:
            datetime.strptime(date_part, "%Y-%m-%d")
        except Exception:
            # Some exports use MM/DD/YYYY
            try:
                d = datetime.strptime(date_part, "%m/%d/%Y").date()
                date_part = d.strftime("%Y-%m-%d")
            except Exception:
                continue

        item = get_any(raw, "Food", "Food Name", "Item", "Description", "Name")
        calories = parse_int(get_any(raw, "Calories", "kcal", "Energy (kcal)"))
        protein = parse_int(get_any(raw, "Protein", "Protein (g)"))
        carbs = parse_int(get_any(raw, "Carbs", "Carbohydrate", "Carbs (g)"))
        fat = parse_int(get_any(raw, "Fat", "Fat (g)"))

        metrics: dict[str, Any] = {}
        if item:
            metrics["item"] = item
        if calories is not None:
            metrics["calories_kcal"] = calories
        if protein is not None:
            metrics["protein_g"] = protein
        if carbs is not None:
            metrics["carbs_g"] = carbs
        if fat is not None:
            metrics["fat_g"] = fat

        norm_for_hash = {
            "date": date_part,
            "source": "fatsecret",
            "row_type": "food_item",
            "raw": raw,
            "metrics": metrics,
        }

        out.append(
            ParsedHealthRow(
                date=date_part,
                source="fatsecret",
                row_type="food_item",
                metrics=metrics,
                raw_row=raw,
                confidence=None,
                normalized_row_for_hash=jsonable_norm(norm_for_hash),
            )
        )
    return out


def parse_arboleaf_csv(csv_bytes: bytes, user_tz: str) -> list[ParsedHealthRow]:
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out: list[ParsedHealthRow] = []

    def get_any(raw: dict[str, Any], *keys: str) -> str:
        for k in keys:
            if k in raw and raw.get(k) not in (None, ""):
                return clean_str(raw.get(k))
        lower = {str(k).lower(): k for k in raw}
        for k in keys:
            lk = k.lower()
            if lk in lower:
                return clean_str(raw.get(lower[lk]))
        return ""

    for row in reader:
        raw = {k: v for k, v in (row or {}).items()}
        date_raw = get_any(raw, "Date", "date", "Time", "time")
        if not date_raw:
            continue
        date_part = date_raw.split(" ")[0]
        parsed_ok = False
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                d = datetime.strptime(date_part, fmt).date()
                date_part = d.strftime("%Y-%m-%d")
                parsed_ok = True
                break
            except Exception:
                pass
        if not parsed_ok:
            continue

        weight = parse_float(get_any(raw, "Weight", "Weight(kg)", "weight_kg"))
        body_fat = parse_float(get_any(raw, "Body Fat", "BodyFat", "Fat%", "body_fat_pct"))
        bmi = parse_float(get_any(raw, "BMI", "bmi"))

        metrics: dict[str, Any] = {}
        if weight is not None:
            metrics["weight_kg"] = float(weight)
        if body_fat is not None:
            metrics["body_fat_pct"] = float(body_fat)
        if bmi is not None:
            metrics["bmi"] = float(bmi)

        norm_for_hash = {
            "date": date_part,
            "source": "arboleaf",
            "row_type": "weigh_in",
            "raw": raw,
            "metrics": metrics,
        }

        out.append(
            ParsedHealthRow(
                date=date_part,
                source="arboleaf",
                row_type="weigh_in",
                metrics=metrics,
                raw_row=raw,
                confidence=None,
                normalized_row_for_hash=jsonable_norm(norm_for_hash),
            )
        )
    return out


def jsonable_norm(obj: Any) -> Any:
    """
    Convert obj into something stable-json-safe:
    - ensure dict keys are strings
    - keep values as basic JSON types
    """
    if isinstance(obj, dict):
        return {str(k): jsonable_norm(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonable_norm(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    # fallback: stringify
    return str(obj)


def stable_preview(rows: list[ParsedHealthRow], limit: int = 3) -> str:
    parts = []
    for r in rows[:limit]:
        parts.append(f"- {r.date} {r.source}/{r.row_type}: {stable_json(r.metrics)[:160]}")
    if len(rows) > limit:
        parts.append(f"- … and {len(rows) - limit} more")
    return "\n".join(parts) if parts else "(no rows)"


# --- Freeform paste (US-057 quick import) ------------------------------------

_DATE_ISO_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_DATE_DMY_RE = re.compile(
    r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d{2})\b",
)


def extract_date_from_freeform_text(text: str, default_date: str) -> str:
    m = _DATE_ISO_RE.search(text)
    if m:
        return m.group(1)
    m2 = _DATE_DMY_RE.search(text)
    if m2:
        d, mo, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except Exception:
            pass
    return default_date


def detect_source_from_freeform(text: str) -> str | None:
    tl = text.lower()
    score = {"garmin": 0, "fatsecret": 0, "arboleaf": 0}
    if re.search(r"\bsteps?\b", tl) or re.search(r"\bpas\b", tl):
        score["garmin"] += 2
    if "distance" in tl or re.search(r"\bkm\b", tl) or "parcouru" in tl:
        score["garmin"] += 1
    if "avg" in tl and "hr" in tl:
        score["garmin"] += 1
    if "protein" in tl or "protéines" in tl or "carbs" in tl or "glucides" in tl:
        score["fatsecret"] += 2
    if "calorie" in tl or "kcal" in tl:
        score["fatsecret"] += 1
    if "weight" in tl or "poids" in tl or "body fat" in tl or "masse grasse" in tl:
        score["arboleaf"] += 2
    best = max(score.values())
    if best == 0:
        return None
    for k, v in score.items():
        if v == best:
            return k
    return None


def _first_int(text: str, patterns: list[str]) -> int | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            v = parse_int(m.group(1))
            if v is not None:
                return v
    return None


def _first_float(text: str, patterns: list[str]) -> float | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            v = parse_float(m.group(1))
            if v is not None:
                return v
    return None


def _garmin_freeform_rows(text: str, default_date: str) -> list[ParsedHealthRow]:
    date_part = extract_date_from_freeform_text(text, default_date)
    metrics: dict[str, Any] = {}
    conf: dict[str, float] = {}

    steps = _first_int(
        text,
        [
            r"(?i)steps?\s*[:\s]+\s*([\d][\d\s,\.]*)",
            r"(?i)\bpas\b\s*[:\s]+\s*([\d][\d\s,\.]*)",
        ],
    )
    if steps is not None:
        metrics["steps"] = steps
        conf["steps"] = 0.72

    dist = _first_float(
        text,
        [
            r"(?i)distance\s*[:\s]+\s*([\d][\d\s,\.]*)",
            r"(?i)\b([\d][\d\s,\.]*)\s*km\b",
        ],
    )
    if dist is not None:
        metrics["distance_km"] = float(dist)
        conf["distance_km"] = 0.72

    kcal = _first_int(
        text,
        [
            r"(?i)active\s+calories?\s*[:\s]+\s*([\d][\d\s,\.]*)",
            r"(?i)calories?\s*actives\s*[:\s]+\s*([\d][\d\s,\.]*)",
        ],
    )
    if kcal is not None:
        metrics["active_calories_kcal"] = kcal
        conf["active_calories_kcal"] = 0.65

    hr = _first_int(text, [r"(?i)avg\.?\s*hr\s*[:\s]+\s*(\d+)"])
    if hr is None:
        m = re.search(r"(?i)\bfc\s*(?:moyenne)?\s*[:\s]+\s*(\d+)", text)
        if m:
            hr = parse_int(m.group(1))
    if hr is not None:
        metrics["avg_hr_bpm"] = hr
        conf["avg_hr_bpm"] = 0.7

    if not metrics:
        return []

    raw = {"paste": text.strip()}
    norm_for_hash = {
        "date": date_part,
        "source": "garmin",
        "row_type": "activity",
        "raw": raw,
        "metrics": metrics,
    }
    return [
        ParsedHealthRow(
            date=date_part,
            source="garmin",
            row_type="activity",
            metrics=metrics,
            raw_row=raw,
            confidence=conf or None,
            normalized_row_for_hash=jsonable_norm(norm_for_hash),
        )
    ]


def _fatsecret_freeform_rows(text: str, default_date: str) -> list[ParsedHealthRow]:
    date_part = extract_date_from_freeform_text(text, default_date)
    cal = _first_int(
        text,
        [
            r"(?i)calories?\s*[:\s]+\s*([\d][\d\s,\.]*)",
            r"(?i)\b([\d][\d\s,\.]*)\s*kcal\b",
        ],
    )
    prot = _first_int(text, [r"(?i)protein\s*[:\s]+\s*([\d][\d\s,\.]*)", r"(?i)protéines\s*[:\s]+\s*([\d][\d\s,\.]*)"])
    carbs = _first_int(text, [r"(?i)carbs?\s*[:\s]+\s*([\d][\d\s,\.]*)", r"(?i)glucides\s*[:\s]+\s*([\d][\d\s,\.]*)"])
    fat = _first_int(text, [r"(?i)fats?\s*[:\s]+\s*([\d][\d\s,\.]*)", r"(?i)lipides\s*[:\s]+\s*([\d][\d\s,\.]*)"])

    if cal is None and prot is None and carbs is None and fat is None:
        return []

    metrics: dict[str, Any] = {"item": "(pasted summary)"}
    conf: dict[str, float] = {}
    if cal is not None:
        metrics["calories_kcal"] = cal
        conf["calories_kcal"] = 0.7
    if prot is not None:
        metrics["protein_g"] = prot
        conf["protein_g"] = 0.7
    if carbs is not None:
        metrics["carbs_g"] = carbs
        conf["carbs_g"] = 0.7
    if fat is not None:
        metrics["fat_g"] = fat
        conf["fat_g"] = 0.7

    raw = {"paste": text.strip()}
    norm_for_hash = {
        "date": date_part,
        "source": "fatsecret",
        "row_type": "food_item",
        "raw": raw,
        "metrics": metrics,
    }
    return [
        ParsedHealthRow(
            date=date_part,
            source="fatsecret",
            row_type="food_item",
            metrics=metrics,
            raw_row=raw,
            confidence=conf or None,
            normalized_row_for_hash=jsonable_norm(norm_for_hash),
        )
    ]


def _arboleaf_freeform_rows(text: str, default_date: str) -> list[ParsedHealthRow]:
    date_part = extract_date_from_freeform_text(text, default_date)
    w = _first_float(
        text,
        [
            r"(?i)weight\s*[:\s]+\s*([\d][\d\s,\.]*)",
            r"(?i)poids\s*[:\s]+\s*([\d][\d\s,\.]*)",
            r"(?i)\b([\d][\d\s,\.]*)\s*kg\b",
        ],
    )
    bf = _first_float(
        text,
        [
            r"(?i)body\s*fat\s*[:\s]+\s*([\d][\d\s,\.]*)",
            r"(?i)masse\s*grasse\s*[:\s]+\s*([\d][\d\s,\.]*)",
        ],
    )
    bmi = _first_float(text, [r"(?i)bmi\s*[:\s]+\s*([\d][\d\s,\.]*)"])

    if w is None and bf is None and bmi is None:
        return []

    metrics: dict[str, Any] = {}
    conf: dict[str, float] = {}
    if w is not None:
        metrics["weight_kg"] = float(w)
        conf["weight_kg"] = 0.72
    if bf is not None:
        metrics["body_fat_pct"] = float(bf)
        conf["body_fat_pct"] = 0.68
    if bmi is not None:
        metrics["bmi"] = float(bmi)
        conf["bmi"] = 0.68

    raw = {"paste": text.strip()}
    norm_for_hash = {
        "date": date_part,
        "source": "arboleaf",
        "row_type": "weigh_in",
        "raw": raw,
        "metrics": metrics,
    }
    return [
        ParsedHealthRow(
            date=date_part,
            source="arboleaf",
            row_type="weigh_in",
            metrics=metrics,
            raw_row=raw,
            confidence=conf or None,
            normalized_row_for_hash=jsonable_norm(norm_for_hash),
        )
    ]


def parse_freeform_health_text(
    text: str,
    *,
    default_date: str,
    source_hint: str | None,
) -> tuple[list[ParsedHealthRow], str | None]:
    """
    Deterministic extraction from pasted summary text (EN/FR).
    Returns (rows, resolved_source).
    """
    t = text.strip()
    if not t:
        return [], None

    source = source_hint if source_hint in ("garmin", "fatsecret", "arboleaf") else None
    if source is None:
        source = detect_source_from_freeform(t)
    if source is None:
        return [], None

    if source == "garmin":
        rows = _garmin_freeform_rows(t, default_date)
    elif source == "fatsecret":
        rows = _fatsecret_freeform_rows(t, default_date)
    else:
        rows = _arboleaf_freeform_rows(t, default_date)

    if not rows:
        return [], None
    return rows, source

