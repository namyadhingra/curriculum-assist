"""
curriculum/assembler.py
-----------------------
Takes a flat list of normalised CourseRow dicts and assembles them into the
final nested JSON structure.

Output schema
-------------
{
  "BTECH": {
    "CSE": {
      "specializations": {
        "AI & ML": {
          "core":     [ CourseObj, ... ],
          "electives":[ CourseObj, ... ]
        }
      }
    }
  },
  "BS":  { ... },
  "BSC": { ... }
}

CourseObj
---------
{
  "code":    "CS101" | null,
  "name":    "Introduction to Computing",
  "credits": "3-0-0" | null,
  "total_credits": 3 | null,
  "type":    "PC"
}

Design choices
--------------
- Program keys are inferred from PDF filenames (see FILENAME_MAP).
- All keys written to JSON are uppercase strings.
- `specializations` block only added when at least one specialization row
  exists for that branch.
- Duplicate courses (same code appearing twice in the same bucket) are merged —
  the first occurrence wins.  This handles PDFs that repeat header rows.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .logger import get_logger, log_unmapped_row, log_skip_row
from .normaliser import (
    normalise_code,
    normalise_credits,
    normalise_name,
    normalise_type,
    normalise_specialization,
)

logger = get_logger("assembler")

# ─── Filename → (program, branch) mapping ─────────────────────────────────────
# Keys are lowercased PDF basenames (without extension); values are
# (PROGRAM_KEY, BRANCH_CODE) tuples that match the desired JSON structure.

FILENAME_MAP: dict[str, tuple[str, str]] = {
    "curriculum-btech-cse": ("BTECH", "CSE"),
    "curriculum-btech-ee":  ("BTECH", "EE"),
    "curriculum-btech-me":  ("BTECH", "ME"),
    "curriculum-btech-cm":  ("BTECH", "CM"),
    "curriculum-btech-ce":  ("BTECH", "CE"),
    "curriculum-btech-mt":  ("BTECH", "MT"),
    "curriculum-btech-bb":  ("BTECH", "BB"),
    "curriculum-btech-ci":  ("BTECH", "CI"),
    # B.S. programs
    "curriculum-bs-physics with specialization": ("BS", "PH"),
    "curriculum-bs-chemistry with specialization": ("BS", "CY"),
    "curriculum-bs-mathematics and computing":    ("BS", "MC"),
}

# Fallback regex patterns for filenames not in the map
_BTECH_PATTERN = re.compile(r"btech[-_\s]?([a-z]{2,4})", re.IGNORECASE)
_BS_PATTERN    = re.compile(r"bs[-_\s]?([a-z]{2,4})", re.IGNORECASE)
_BSC_PATTERN   = re.compile(r"bsc[-_\s]?([a-z]{2,4})", re.IGNORECASE)

# All valid course-type bucket keys
BUCKET_KEYS = ["PC", "PE", "OE", "SC", "SE", "IS", "IE", "IH", "LS", "PP", "EC", "EE", "NH", "NE", "ND", "UNKNOWN"]


# ─── Public API ────────────────────────────────────────────────────────────────

def assemble(raw_rows: list[dict]) -> dict[str, Any]:
    """
    Normalise and assemble all raw rows into the final JSON structure.

    Parameters
    ----------
    raw_rows : list of raw row dicts from parser.parse_pdf()

    Returns
    -------
    Nested dict ready for json.dumps().
    """
    # Top-level structure — programs we know about
    output: dict[str, dict] = {
        "BTECH": {},
        "BS":    {},
        "BSC":   {},
    }

    # Temporary staging: output[program][branch]["_semesters"][sem][type]
    #                    output[program][branch]["_specs"][spec]["core"/"electives"]
    staging: dict = {}

    for row in raw_rows:
        _process_row(row, staging)

    # Convert staging → clean output
    for program, branches in staging.items():
        if program not in output:
            output[program] = {}
        for branch, data in branches.items():
            output[program][branch] = _build_branch_entry(data)

    return output


# Names that are clearly metadata labels, not course names
_META_LABELS = re.compile(
    r"^(title|department|offered\s*for|prerequisite|objectives?|"
    r"learning\s*outcomes?|contents?|textbook|reference\s*books?|"
    r"laboratory\s*experiments?|self[\s\-]learning|online\s*course|"
    r"course|representative|courses?|category|credits?|contact|"
    r"hrs?|hours?|type|l\s*-?\s*t\s*-?\s*p|ltp|"
    r"(i{1,4}|vi{0,3}|iv|v)\s*semester|semester\s*(i{1,4}|vi{0,3}|iv|v|\d)|"
    r"s\.?\s*no\.?|sr\.?|sl\.?\s*no\.?)$",
    re.IGNORECASE,
)

# Rows that are URLs
_URL_PATTERN = re.compile(r"https?://\S+")

# Max name length for a course without a code — very long strings are syllabi
_MAX_NAME_LEN_NO_CODE = 200

# Minimum meaningful course name length
_MIN_NAME_LEN = 4


def _is_noise_row(name: str, raw_code, raw_credits) -> bool:
    """
    Return True if the row should be discarded as noise.

    Rules:
    1. Name matches a known metadata label exactly.
    2. Name contains a URL.
    3. No code found AND no credits AND name is very long (syllabus paragraph).
    4. Name is extremely short (< MIN_NAME_LEN chars) and has no code.
    5. Name is purely numeric.
    """
    if not name:
        return True

    # Rule 1 — metadata label
    if _META_LABELS.match(name.strip()):
        return True

    # Rule 2 — URL in name
    if _URL_PATTERN.search(name):
        return True

    has_code    = bool(raw_code and str(raw_code).strip())
    has_credits = bool(raw_credits and str(raw_credits).strip())

    # Rule 3 — very long, no code, no credits → syllabus paragraph
    if len(name) > _MAX_NAME_LEN_NO_CODE and not has_code and not has_credits:
        return True

    # Rule 4 — too short and no code
    if len(name.strip()) < _MIN_NAME_LEN and not has_code:
        return True

    # Rule 5 — purely numeric
    if name.strip().replace("-", "").replace(".", "").isdigit():
        return True

    return False


def _process_row(row: dict, staging: dict) -> None:
    """Normalise a single raw row and stage it under the right keys."""
    pdf_name = row.get("source_pdf", "")
    page     = row.get("page", 0)


    # ── Identify program + branch ──────────────────────────────────────
    program, branch = _identify_program_branch(pdf_name)
    if not program or not branch:
        logger.warning("UNIDENTIFIED_PDF | pdf=%s — skipping row", pdf_name)
        return

    # ── Normalise fields ───────────────────────────────────────────────
    raw_name = row.get("raw_name")
    name     = normalise_name(raw_name)
    if not name:
        log_skip_row(logger, "missing_name", pdf_name, page, row)
        return

    # ── Noise rejection ───────────────────────────────────────────────
    if _is_noise_row(name, row.get("raw_code"), row.get("raw_credits")):
        log_skip_row(logger, "noise_row", pdf_name, page, row)
        return

    code        = normalise_code(row.get("raw_code") or raw_name)
    course_type = normalise_type(row.get("raw_type"))
    credits_obj = normalise_credits(row.get("raw_credits"))
    spec_raw    = row.get("specialization")
    spec        = normalise_specialization(spec_raw) if spec_raw else None

    course_obj: dict = {
        "code":          code,
        "name":          name,
        "credits":       credits_obj["ltp"],
        "total_credits": credits_obj["total"],
        "type":          course_type,
    }

    if course_type == "UNKNOWN":
        log_unmapped_row(logger, pdf_name, page, row)

    # ── Stage the course ───────────────────────────────────────────────
    staging.setdefault(program, {}).setdefault(branch, {
        "_specs":     defaultdict(lambda: {"core": [], "electives": []}),
    })
    branch_data = staging[program][branch]

    if spec:
        # Specialization course
        if course_type in ("SC",):
            bucket = "core"
        else:
            bucket = "electives"
        _append_unique(branch_data["_specs"][spec][bucket], course_obj)


def _build_branch_entry(data: dict) -> dict:
    """Convert staged branch data into the final clean dict."""
    entry: dict = {}

    # ── Specializations ────────────────────────────────────────────────
    specs = dict(data.get("_specs", {}))
    if specs:
        entry["specializations"] = {
            spec: {
                "core":     core_list,
                "electives": elec_list,
            }
            for spec, d in specs.items()
            for core_list, elec_list in [( d["core"], d["electives"] )]
        }

    return entry


def _append_unique(lst: list, course_obj: dict) -> None:
    """Append course_obj to lst only if no existing entry has the same code+name."""
    code = course_obj.get("code")
    name = course_obj.get("name")
    for existing in lst:
        if code and existing.get("code") == code:
            return
        if existing.get("name") == name:
            return
    lst.append(course_obj)


def _identify_program_branch(pdf_name: str) -> tuple[str | None, str | None]:
    """
    Map a PDF filename to (program, branch) using the static map first,
    then regex fallbacks.
    """
    stem = Path(pdf_name).stem.lower().strip()

    # Static map
    if stem in FILENAME_MAP:
        return FILENAME_MAP[stem]

    # Fuzzy match against static map keys
    for key, value in FILENAME_MAP.items():
        if key in stem:
            return value

    # Regex fallbacks
    m = _BTECH_PATTERN.search(stem)
    if m:
        return ("BTECH", m.group(1).upper())

    m = _BSC_PATTERN.search(stem)
    if m:
        return ("BSC", m.group(1).upper())

    m = _BS_PATTERN.search(stem)
    if m:
        return ("BS", m.group(1).upper())

    return (None, None)
