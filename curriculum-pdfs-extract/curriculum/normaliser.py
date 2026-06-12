"""
curriculum/normaliser.py
------------------------
Cleans raw extracted strings and maps them to canonical types.

Responsibilities
----------------
1. Course code normalisation  — regex extraction + uppercase.
2. Course name normalisation  — strip footnotes, collapse whitespace.
3. Course type fuzzy mapping  — keyword dict → rapidfuzz fallback → "UNKNOWN".
4. Credits normalisation      — extract L-T-P, compute total.
5. Specialization normalisation — clean specialization names.

Design choices
--------------
- `rapidfuzz` is used instead of `fuzzywuzzy` (no C extension required; faster).
- All keyword comparisons are done after lowercasing to be case-insensitive.
- The keyword dict is ordered from most-specific to least-specific so that
  "Open Elective" matches OE before PE.
"""

from __future__ import annotations

import re
from typing import Optional

from rapidfuzz import fuzz

from .logger import get_logger

logger = get_logger("normaliser")

# ---------------------------------------------------------------------------
# Course type keyword mapping
# Ordered from most specific → least specific.
# ---------------------------------------------------------------------------
COURSE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "OE": [
        "open elective",
        "oe",
        "open",
    ],
    "SC": [
        "specialization core",
        "specialisation core",
        "sc",
        "core (specialization)",
        "core (specialisation)",
        "specialization compulsory",
    ],
    "SE": [
        "specialization elective",
        "specialisation elective",
        "se",
    ],
    "PC": [
        "pc",
        "program core",
        "programme core",
        "program compulsory",
        "programme compulsory",
        "compulsory course",
        "core course",
        "core",
        "compulsory",
    ],
    "PE": [
        "pe",
        "program elective",
        "programme elective",
        "elective",
    ],
}

# Regex patterns
_CODE_PATTERN = re.compile(r"\b([A-Z]{2,4}\s?\d{3,4}[A-Z]?)\b")
_LTP_PATTERN  = re.compile(r"(\d)\s*[-–]\s*(\d)\s*[-–]\s*(\d)")
_FOOTNOTE_CHARS = re.compile(r"[*†#^$@!]")
_TRAILING_DIGITS = re.compile(r"\s+\d+$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalise_code(raw: Optional[str]) -> Optional[str]:
    """Extract and normalise a course code from a raw string."""
    if not raw:
        return None
    raw_upper = raw.upper().strip()
    m = _CODE_PATTERN.search(raw_upper)
    if m:
        return m.group(1).replace(" ", "")
    return None


def normalise_name(raw: Optional[str]) -> Optional[str]:
    """
    Clean a course name:
    - Strip footnote symbols and trailing digit annotations.
    - Collapse whitespace.
    - Remove parenthetical L-T-P credit strings.
    """
    if not raw:
        return None
    s = raw.strip()
    s = _FOOTNOTE_CHARS.sub("", s)           # remove *, †, #, ^, …
    s = re.sub(r"\(\s*\d[-–]\d[-–]\d\s*\)", "", s)   # remove (3-0-0)
    s = re.sub(r"\(\s*\d+\s*credits?\s*\)", "", s, flags=re.IGNORECASE)
    s = _TRAILING_DIGITS.sub("", s)          # remove trailing standalone digits
    s = re.sub(r"\s+", " ", s).strip()       # collapse internal whitespace
    return s if s else None


def normalise_type(raw: Optional[str]) -> str:
    """
    Map a raw course-type string to a canonical code using keyword matching
    then rapidfuzz fuzzy matching as fallback.

    Returns one of: "PC", "PE", "OE", "SC", "SE", "UNKNOWN".
    """
    if not raw:
        return "UNKNOWN"

    candidate = raw.strip().lower()

    # 1 — Exact / substring keyword match
    for code, keywords in COURSE_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in candidate:
                return code

    # 2 — Fuzzy match against all keywords (threshold ≥ 80)
    best_score = 0
    best_code  = "UNKNOWN"
    for code, keywords in COURSE_TYPE_KEYWORDS.items():
        for kw in keywords:
            score = fuzz.partial_ratio(kw, candidate)
            if score > best_score:
                best_score = score
                best_code  = code

    if best_score >= 80:
        logger.debug(
            "fuzzy_type | raw=%r → %s (score=%d)", raw, best_code, best_score
        )
        return best_code

    logger.debug("unknown_type | raw=%r (best_score=%d)", raw, best_score)
    return "UNKNOWN"


def normalise_credits(raw: Optional[str]) -> dict:
    """
    Extract L-T-P from a raw credit string.

    Returns:
        {
            "ltp": "3-0-0",   # or None
            "total": 3        # L + T + P/2, or None
        }
    """
    result = {"ltp": None, "total": None}
    if not raw:
        return result
    m = _LTP_PATTERN.search(str(raw))
    if m:
        L, T, P = int(m.group(1)), int(m.group(2)), int(m.group(3))
        result["ltp"]   = f"{L}-{T}-{P}"
        result["total"] = L + T + (P // 2)
    return result


def normalise_specialization(raw: Optional[str]) -> Optional[str]:
    """Clean a specialization name."""
    if not raw:
        return None
    s = raw.strip().upper()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(SPECIALIZATION|SPECIALISATION|TRACK|GROUP)\s*:?\s*", "", s).strip()
    return s if s else None
