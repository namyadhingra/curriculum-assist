"""
curriculum/parser.py
--------------------
Extracts raw course rows from curriculum PDFs.

Strategy (per PDF)
------------------
Pass 1 — pdfplumber
    • Best at extracting tables with bounding-box heuristics.
    • Also reads raw text per page to detect specialization headers.

Pass 2 — PyMuPDF (fitz) fallback
    • Used when pdfplumber finds fewer than MIN_ROWS rows for a document.
    • Parses text blocks and attempts column alignment via x-coordinate bucketing.

OCR fallback (optional)
    • If neither pass yields rows AND pytesseract + Pillow are installed,
      renders each page as an image and runs Tesseract OCR.
    • Soft dependency — tool continues without it if not available.

Row schema
----------
Each returned dict has these keys:
    raw_code        : str | None    — unprocessed code cell
    raw_name        : str | None    — unprocessed name cell
    raw_type        : str | None    — raw course-type label
    raw_credits     : str | None    — raw credit string (may be L-T-P)
    specialization  : str | None    — detected specialization label
    source_pdf      : str           — basename of the source file
    page            : int           — 1-indexed page number

Design choices
--------------
- Specialization headers are detected by a keyword list; once detected the
  current specialization is tracked until another header resets it.
- "OR" rows (alternate course options) are preserved as separate entries
  with name prefixed "OR: " so the assembler can handle them.
- Merged-cell heuristic: if a table cell spans multiple columns and contains
  keyword patterns (e.g. "Elective"), it is treated as a header.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .logger import get_logger, log_parse_failure, log_parse_success

logger = get_logger("parser")

# ─── Constants ────────────────────────────────────────────────────────────────

MIN_ROWS = 5   # if pdfplumber finds fewer → try PyMuPDF


# Specialization heading keywords
_SPEC_KEYWORDS = [
    "specialization", "specialisation", "track", "elective group",
    "domain elective", "area of specialization",
]

# Course-type column header keywords
_TYPE_HEADER_KEYWORDS = re.compile(
    r"\b(pc|pe|oe|sc|se|core|elective|compulsory|open)\b",
    re.IGNORECASE,
)

# Likely course-code pattern (used to identify which column holds codes)
_CODE_LIKE = re.compile(r"^[A-Z]{2,4}\s?\d{3,4}[A-Z]?$")

# Cells that are clearly just table headers or noise
_NOISE_CELLS = re.compile(
    r"^(s\.?\s*no\.?|sr\.?|sl\.?\s*no\.?|course\s*code|course\s*name|"
    r"course\s*title|credits?|l[\s\-]t[\s\-]p|contact|hrs?|hours?|"
    r"theory|practical|tutorial|total|category|type|semester|sem)$",
    re.IGNORECASE,
)

# OR-course separator
_OR_ROW = re.compile(r"^\s*OR\s*$", re.IGNORECASE)


# ─── Main entry point ─────────────────────────────────────────────────────────

def parse_pdf(pdf_path: str | Path) -> list[dict]:
    """
    Parse a single curriculum PDF and return a list of raw row dicts.
    Falls back through pdfplumber → PyMuPDF → OCR automatically.
    """
    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.name
    rows: list[dict] = []

    # ── Pass 1: pdfplumber ────────────────────────────────────────────────
    try:
        rows = _parse_pdfplumber(pdf_path)
        logger.debug("pdfplumber | %s | rows=%d", pdf_name, len(rows))
    except Exception as exc:
        logger.warning("pdfplumber_error | %s | %s", pdf_name, exc)

    # ── Pass 2: PyMuPDF fallback ──────────────────────────────────────────
    if len(rows) < MIN_ROWS:
        logger.info("Falling back to PyMuPDF for %s", pdf_name)
        try:
            rows = _parse_pymupdf(pdf_path)
            logger.debug("pymupdf | %s | rows=%d", pdf_name, len(rows))
        except Exception as exc:
            logger.warning("pymupdf_error | %s | %s", pdf_name, exc)

    # ── Pass 3: OCR (optional) ────────────────────────────────────────────
    if len(rows) < MIN_ROWS:
        rows = _try_ocr(pdf_path, rows)

    if rows:
        log_parse_success(logger, pdf_name, len(rows))
    else:
        log_parse_failure(logger, pdf_name, "zero rows extracted after all passes")

    return rows


# ─── Pass 1: pdfplumber ───────────────────────────────────────────────────────

def _parse_pdfplumber(pdf_path: Path) -> list[dict]:
    import pdfplumber  # local import so PyMuPDF-only installs still work

    rows: list[dict] = []
    pdf_name = pdf_path.name
    current_spec: Optional[str] = None
    prev_was_or = False

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""

            # ── Update specialization context from page headings ────────
            current_spec = _update_context_from_text(page_text, current_spec)

            # ── Extract tables ──────────────────────────────────────────
            tables = page.extract_tables() or []
            for table in tables:
                if not table:
                    continue

                # Detect header row and column mapping
                col_map = _detect_columns(table)

                for row_idx, raw_row in enumerate(table):
                    if raw_row is None:
                        continue

                    cells = [_clean_cell(c) for c in raw_row]

                    # Update context from merged header cells within table
                    row_text = " ".join(c for c in cells if c)
                    current_spec = _update_context_from_text(row_text, current_spec)

                    # Skip pure header rows
                    if _is_header_row(cells):
                        continue

                    # Check for OR separator
                    if any(_OR_ROW.match(c) for c in cells if c):
                        prev_was_or = True
                        continue

                    extracted = _extract_row_from_cells(cells, col_map, pdf_name, page_num)
                    if extracted is None:
                        continue

                    extracted["specialization"] = current_spec
                    if prev_was_or:
                        extracted["raw_name"] = "OR: " + (extracted["raw_name"] or "")
                        prev_was_or = False

                    rows.append(extracted)

    return rows


def _update_context_from_text(
    text: str,
    current_spec: Optional[str],
) -> Optional[str]:
    """Scan text for specialization headers and update context."""

    # Specialization detection
    # Specialization headings appear in section titles
    lower = text.lower()
    for kw in _SPEC_KEYWORDS:
        if kw in lower:
            # Avoid treating "specialization" within a regular sentence as a header
            # — only capture if the keyword is prominent (short surrounding text)
            if len(text.strip()) > 200:
                # Long text block — not a heading
                break
            m = re.search(
                rf"(?:{re.escape(kw)})\s*[:\-\u2013]?\s*([A-Za-z0-9 &/()]+)",
                text,
                re.IGNORECASE,
            )
            if m:
                spec_label = m.group(1).strip().upper()
                # Strip trailing noise that commonly follows spec names
                spec_label = re.sub(
                    r"\s*(CORE|ELECTIVE|COURSE|CREDIT|OFFERED|JOINTLY).*", "",
                    spec_label,
                ).strip()
                if 1 < len(spec_label) <= 60:
                    current_spec = spec_label
            break

    return current_spec



def _detect_columns(table: list[list]) -> dict[str, int]:
    """
    Heuristically identify which column index maps to:
    code, name, type, credits.
    Looks at the first non-empty row to find keyword-bearing headers.
    """
    col_map: dict[str, int] = {}
    for row in table[:4]:  # check first 4 rows for headers
        if not row:
            continue
        for idx, cell in enumerate(row):
            if not cell:
                continue
            cl = str(cell).lower().strip()
            if any(k in cl for k in ("code",)) and "code" not in col_map:
                col_map["code"] = idx
            elif any(k in cl for k in ("name", "title", "course")) and "name" not in col_map:
                col_map["name"] = idx
            elif any(k in cl for k in ("type", "category", "pc", "pe", "oe")) and "type" not in col_map:
                col_map["type"] = idx
            elif any(k in cl for k in ("credit", "l-t", "ltp", "l t p", "hrs", "contact")) and "credits" not in col_map:
                col_map["credits"] = idx
        if len(col_map) >= 2:
            break
    return col_map


def _extract_row_from_cells(
    cells: list[str],
    col_map: dict[str, int],
    pdf_name: str,
    page_num: int,
) -> Optional[dict]:
    """Build a raw row dict from table cells using the detected column map."""
    if not any(cells):
        return None

    # Use col_map if populated, otherwise auto-detect
    code_idx    = col_map.get("code")
    name_idx    = col_map.get("name")
    type_idx    = col_map.get("type")
    credits_idx = col_map.get("credits")

    # Auto-detect code column: first cell matching code pattern
    if code_idx is None:
        for i, c in enumerate(cells):
            if c and _CODE_LIKE.match(c.strip().upper().replace(" ", "")):
                code_idx = i
                break

    # Auto-detect name column: longest non-code non-numeric cell
    if name_idx is None:
        candidate = -1
        max_len = 0
        for i, c in enumerate(cells):
            if i == code_idx:
                continue
            if c and len(c) > max_len and not c.strip().replace("-", "").isdigit():
                max_len = len(c)
                candidate = i
        if candidate >= 0:
            name_idx = candidate

    raw_code    = cells[code_idx]    if code_idx    is not None and code_idx    < len(cells) else None
    raw_name    = cells[name_idx]    if name_idx    is not None and name_idx    < len(cells) else None
    raw_type    = cells[type_idx]    if type_idx    is not None and type_idx    < len(cells) else None
    raw_credits = cells[credits_idx] if credits_idx is not None and credits_idx < len(cells) else None

    # If name is still None or is noise, try every cell
    if not raw_name or _NOISE_CELLS.match(raw_name or ""):
        for i, c in enumerate(cells):
            if c and i != code_idx and not _NOISE_CELLS.match(c) and not c.strip().isdigit():
                raw_name = c
                break

    if not raw_name:
        return None

    return {
        "raw_code":    raw_code,
        "raw_name":    raw_name,
        "raw_type":    raw_type,
        "raw_credits": raw_credits,
        "specialization": None,
        "source_pdf":  pdf_name,
        "page":        page_num,
    }


def _is_header_row(cells: list[str]) -> bool:
    """Return True if the row looks like a column-header row (all noise cells)."""
    non_empty = [c for c in cells if c]
    if not non_empty:
        return True
    return all(_NOISE_CELLS.match(c) for c in non_empty)


def _clean_cell(value) -> str:
    """Normalise a raw table cell value to a clean string."""
    if value is None:
        return ""
    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)
    return s


# ─── Pass 2: PyMuPDF ──────────────────────────────────────────────────────────

def _parse_pymupdf(pdf_path: Path) -> list[dict]:
    """
    Fallback parser using PyMuPDF.  Extracts text blocks sorted by y-position,
    then attempts to bucket text into columns by x-coordinate ranges.
    """
    import fitz  # PyMuPDF

    rows: list[dict] = []
    pdf_name = pdf_path.name
    current_spec: Optional[str] = None

    doc = fitz.open(str(pdf_path))

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
        # Sort top-to-bottom
        blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

        page_text = "\n".join(b[4] for b in blocks)
        current_spec = _update_context_from_text(page_text, current_spec)

        # Group text blocks into logical lines by y proximity
        lines = _group_blocks_into_lines(blocks)

        for line_blocks in lines:
            if not line_blocks:
                continue
            line_text = " ".join(b[4].strip() for b in line_blocks)

            # Context update
            current_spec = _update_context_from_text(line_text, current_spec)

            if _NOISE_CELLS.match(line_text.strip()):
                continue

            # Attempt code extraction
            code_m = re.search(r"\b([A-Z]{2,4}\s?\d{3,4}[A-Z]?)\b", line_text.upper())
            raw_code = code_m.group(1).replace(" ", "") if code_m else None

            # Remove code from text to get name candidate
            name_text = re.sub(r"\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b", "", line_text).strip()
            name_text = re.sub(r"\s+", " ", name_text).strip()

            if not name_text or len(name_text) < 3:
                continue

            rows.append({
                "raw_code":       raw_code,
                "raw_name":       name_text,
                "raw_type":       None,
                "raw_credits":    None,
                "specialization": current_spec,
                "source_pdf":     pdf_name,
                "page":           page_num,
            })

    doc.close()
    return rows


def _group_blocks_into_lines(
    blocks: list, y_tolerance: float = 5.0
) -> list[list]:
    """
    Group text blocks that share roughly the same y-coordinate into a single
    logical line.
    """
    if not blocks:
        return []
    groups: list[list] = []
    current_group = [blocks[0]]
    current_y = blocks[0][1]

    for block in blocks[1:]:
        if abs(block[1] - current_y) <= y_tolerance:
            current_group.append(block)
        else:
            groups.append(current_group)
            current_group = [block]
            current_y = block[1]
    groups.append(current_group)
    return groups


# ─── Pass 3: OCR (optional) ───────────────────────────────────────────────────

def _try_ocr(pdf_path: Path, existing_rows: list[dict]) -> list[dict]:
    """
    Attempt OCR on each page image if pytesseract and Pillow are available.
    Returns existing_rows unchanged if OCR is unavailable.
    """
    try:
        import pytesseract
        from PIL import Image
        import fitz
    except ImportError:
        logger.info(
            "OCR unavailable for %s (pytesseract/Pillow/fitz not installed).",
            pdf_path.name,
        )
        return existing_rows

    logger.info("Attempting OCR for %s", pdf_path.name)
    rows: list[dict] = []
    current_spec: Optional[str] = None

    doc = fitz.open(str(pdf_path))
    for page_num, page in enumerate(doc, start=1):
        mat = fitz.Matrix(2, 2)  # 2× zoom for better OCR accuracy
        clip = page.get_pixmap(matrix=mat)
        img_bytes = clip.tobytes("png")

        import io
        img = Image.open(io.BytesIO(img_bytes))
        page_text = pytesseract.image_to_string(img, config="--psm 6")

        current_spec = _update_context_from_text(page_text, current_spec)

        for line in page_text.splitlines():
            line = line.strip()
            if not line or _NOISE_CELLS.match(line):
                continue
            code_m = re.search(r"\b([A-Z]{2,4}\s?\d{3,4}[A-Z]?)\b", line.upper())
            raw_code = code_m.group(1).replace(" ", "") if code_m else None
            name_text = re.sub(r"\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b", "", line).strip()
            if not name_text or len(name_text) < 3:
                continue
            rows.append({
                "raw_code":       raw_code,
                "raw_name":       name_text,
                "raw_type":       None,
                "raw_credits":    None,
                "specialization": current_spec,
                "source_pdf":     pdf_path.name,
                "page":           page_num,
            })

    doc.close()
    return rows if rows else existing_rows


# ─── Helpers ──────────────────────────────────────────────────────────────────


