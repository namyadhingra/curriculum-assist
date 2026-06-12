# Curriculum PDF → JSON Extractor

A Python CLI tool that parses IIT Jodhpur **B.Tech / B.S. / B.Sc.** curriculum
PDFs and emits a single, clean, structured `curriculum.json`.

Built for programs: **CSE, EE, ME, CM (AI&DS), CE, MT, BB, CI** (B.Tech) and
**PH, CY, MC** (B.S.).

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Installation](#installation)
4. [Usage](#usage)
5. [CLI Reference](#cli-reference)
6. [How It Works](#how-it-works)
   - [PDF Parsing Pipeline](#pdf-parsing-pipeline)
   - [Course Type Classification](#course-type-classification)
   - [Semester Detection](#semester-detection)
   - [Specialization Handling](#specialization-handling)
7. [Output Format](#output-format)
8. [Logging](#logging)
9. [Handling Messy PDFs](#handling-messy-pdfs)
10. [Known Limitations](#known-limitations)
11. [Adding New Programs](#adding-new-programs)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Parse all PDFs already in curriculums/ → output/curriculum.json
python build_curriculum_json.py --parse

# 3. Parse with verbose debug output
python build_curriculum_json.py --parse --verbose
```

---

## Project Structure

```
curriculum-pdfs-extract/
├── build_curriculum_json.py   ← CLI entry point (run this)
├── curriculum-links.txt       ← PDF source URLs per program/branch
├── requirements.txt
├── README.md
│
├── curriculum/                ← Source package
│   ├── __init__.py
│   ├── logger.py              ← Dual file+console logging
│   ├── downloader.py          ← URL → PDF download with file-existence check
│   ├── parser.py              ← PDF → raw row extraction
│   ├── normaliser.py          ← Data cleaning + course-type fuzzy mapping
│   └── assembler.py           ← Rows → nested JSON structure
│
├── curriculums/               ← PDF storage (already populated)
├── output/
│   └── curriculum.json        ← Generated output (created on first run)
└── logs/
    └── parse_YYYYMMDD_HHMMSS.log
```

---

## Installation

### Prerequisites
- Python 3.9 or newer
- pip

### Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
| Package | Version | Purpose |
|---|---|---|
| `pdfplumber` | ≥ 0.10 | Primary PDF table extractor |
| `PyMuPDF` | ≥ 1.23 | Fallback PDF text extractor |
| `rapidfuzz` | ≥ 3.0 | Fuzzy course-type keyword matching |
| `requests` | ≥ 2.31 | HTTP PDF downloads |
| `tqdm` | ≥ 4.66 | Download progress bar |

### Optional: OCR support

If you need to parse scanned (image-only) PDFs:

```bash
pip install pytesseract Pillow
# Also install the Tesseract binary:
#   Windows: https://github.com/UB-Mannheim/tesseract/wiki
#   Linux:   sudo apt install tesseract-ocr
#   macOS:   brew install tesseract
```

The tool will auto-detect and use OCR as a third fallback when available.

---

## Usage

### Parse existing PDFs (most common)

All curriculum PDFs are already in `curriculums/`. Just parse them:

```bash
python build_curriculum_json.py --parse
```

### Download then parse

```bash
python build_curriculum_json.py --download --parse
```

> **Note:** Some curriculum PDFs are not publicly accessible as direct PDF
> links (e.g. B.Tech CI, B.S. Chemistry). These are already pre-downloaded
> in `curriculums/`. The `--download` flag will skip any file that already
> exists and only log warnings for HTML-returning URLs.

### Force full re-run

```bash
python build_curriculum_json.py --force --parse
```

Wipes existing PDFs and `curriculum.json`, then re-parses from scratch.

### Verbose/debug mode

```bash
python build_curriculum_json.py --parse --verbose
```

Prints DEBUG-level messages to console (column detection, fuzzy matches, etc.)

---

## CLI Reference

```
python build_curriculum_json.py [OPTIONS]
```

| Flag | Description |
|---|---|
| `--download` | Download missing PDFs from `curriculum-links.txt` |
| `--parse` | Parse all PDFs → `output/curriculum.json` |
| `--force` | Wipe existing PDFs + JSON and redo from scratch |
| `--verbose` | Show DEBUG output in the console |
| `--pdf-dir DIR` | PDF directory (default: `curriculums/`) |
| `--links-file FILE` | Links file path (default: `curriculum-links.txt`) |
| `--output-dir DIR` | Output directory (default: `output/`) |
| `--logs-dir DIR` | Logs directory (default: `logs/`) |

---

## How It Works

### PDF Parsing Pipeline

Each PDF goes through up to three extraction passes, stopping as soon as
enough rows are found (≥ 5):

```
PDF File
   │
   ▼
Pass 1: pdfplumber
   • page.extract_tables() — native table detection with bounding-box heuristics
   • Best for PDFs with real table structures
   │
   ├── ≥ 5 rows found → proceed
   │
   ▼ (fallback)
Pass 2: PyMuPDF (fitz)
   • get_text("blocks") — text block extraction sorted by y-position
   • Groups blocks into logical lines by y-coordinate proximity
   • Good for text-heavy or non-table PDFs
   │
   ├── ≥ 5 rows found → proceed
   │
   ▼ (optional fallback)
Pass 3: OCR via pytesseract
   • Renders each page as a 2× zoom PNG
   • Runs Tesseract with --psm 6 (uniform block of text)
   • Only used if pytesseract + Pillow + Tesseract are installed
   │
   ▼
Raw Rows (list of dicts per PDF)
   │
   ▼
Normaliser
   • Clean whitespace, remove footnote symbols
   • Extract L-T-P credit strings
   • Fuzzy-map course type keywords → PC/PE/OE/SC/SE
   • Regex-extract course codes [A-Z]{2,4}\d{3,4}
   │
   ▼
Assembler
   • Group rows by (program, branch, semester, type)
   • Separate specialization rows into specializations block
   • Deduplicate courses by code+name
   │
   ▼
curriculum.json
```

---

### Course Type Classification

The normaliser maps raw type strings to canonical codes using a two-step
keyword + fuzzy matching approach:

| Canonical Code | Matched keywords |
|---|---|
| `PC` | "PC", "Program Core", "Programme Core", "Program Compulsory", "Compulsory Course", "Core Course" |
| `PE` | "PE", "Program Elective", "Programme Elective", "Elective" |
| `OE` | "OE", "Open Elective", "Open" |
| `SC` | "SC", "Specialization Core", "Core (Specialization)", "Specialization Compulsory" |
| `SE` | "SE", "Specialization Elective", "Specialisation Elective" |

**Step 1 — Exact substring match:** The raw string is lowercased and checked
against the keyword list in order from most-specific to least-specific (OE
before PE before PC, so "Open Elective" doesn't accidentally match "Elective").

**Step 2 — Fuzzy match:** If no exact match, `rapidfuzz.fuzz.partial_ratio`
is run against all keywords. A score ≥ 80 is accepted.

**Fallback:** Rows that cannot be classified are marked `UNKNOWN` and logged
with their source PDF, page number, and raw values.

---

### Semester Detection

Semester context is tracked **per page** and updated whenever a heading
matches:

```
Semester I / Semester 1 / Sem. I / Sem-3 / SEMESTER IV
```

Roman numerals (I–X) and Arabic numerals (1–10) are both accepted.  The
detected semester number is propagated to all rows extracted from that page
and from subsequent table rows until a new semester heading is found.

---

### Specialization Handling

Specialization context is detected from headings containing keywords:

```
Specialization / Specialisation / Track / Elective Group /
Domain Elective / Area of Specialization
```

When detected, all following rows are tagged with the specialization label
until a new heading clears or changes it. Specialization courses are routed
to the `specializations` block in the JSON:

- Course type `SC` → `specializations.<NAME>.core`
- All other types → `specializations.<NAME>.electives`

---

## Output Format

```json
{
  "BTECH": {
    "CSE": {
      "specializations": {
        "ARTIFICIAL INTELLIGENCE & MACHINE LEARNING": {
          "core": [
            {
              "code": "CS601",
              "name": "Machine Learning",
              "credits": "3-0-0",
              "total_credits": 3,
              "type": "SC"
            }
          ],
          "electives": [ ... ]
        }
      },
      "semesters": {
        "1": {
          "PC": [
            {
              "code": "MA101",
              "name": "Mathematics I",
              "credits": "3-1-0",
              "total_credits": 4,
              "type": "PC"
            }
          ],
          "PE": [],
          "OE": [],
          "SC": [],
          "SE": [],
          "UNKNOWN": []
        },
        "2": { "..." },
        "0": { "..." }
      }
    },
    "EE": { "..." }
  },
  "BS": {
    "PH": { "..." },
    "CY": { "..." },
    "MC": { "..." }
  },
  "BSC": {}
}
```

**Key conventions:**
- All top-level and branch keys are **UPPERCASE**.
- Semester keys are string integers (`"1"` … `"8"`).
- Semester `"0"` holds courses whose semester could not be determined.
- `code` is `null` when no course code was found in the PDF.
- `credits` follows the L-T-P format (`"3-0-0"`) or is `null`.
- `total_credits` = L + T + P÷2 (standard IIT credit calculation).
- Empty type buckets appear as `[]` (never omitted) for consistency.

---

## Logging

Every run creates a timestamped log file in `logs/`:

```
logs/parse_20261206_153022.log
```

The log records:

| Event | Level | Description |
|---|---|---|
| `PARSE_OK` | INFO | PDF parsed successfully with row count |
| `PARSE_FAIL` | ERROR | PDF could not be parsed after all passes |
| `SKIP_ROW` | WARNING | Row skipped (missing course name) |
| `UNMAPPED_ROW` | WARNING | Course type could not be classified (marked UNKNOWN) |
| `SKIP_DOWNLOAD` | INFO | PDF already exists, download skipped |
| `NOT_PDF` | WARNING | URL returned HTML instead of a PDF |
| `DOWNLOAD_FAIL` | ERROR | Network error during download |

Log format:

```
HH:MM:SS | LEVEL    | module | message
```

---

## Handling Messy PDFs

The tool is designed to be robust to common IIT curriculum PDF issues:

| Problem | Handling |
|---|---|
| Merged cells / wide headers | Detected as context-update rows; not added as courses |
| Missing course codes | Code set to `null`; warning logged |
| Roman numeral semesters | Converted to integers (I→1, IV→4, etc.) |
| "OR" course alternatives | Preserved with name prefixed `"OR: "` |
| Footnote symbols (*, †, #) | Stripped from course names |
| Parenthetical LTP in names | Removed with regex (e.g. `(3-0-0)`) |
| Repeated header rows | Detected and skipped via noise-cell regex |
| Inconsistent whitespace | Collapsed to single spaces throughout |
| Scanned / image PDFs | OCR fallback via pytesseract (if installed) |

---

## Known Limitations

1. **B.Tech CI / B.S. Chemistry** — these PDFs were sourced from HTML pages
   that cannot be scraped directly. The pre-downloaded files in `curriculums/`
   are used instead. The `--download` flag will log a warning for their URLs.

2. **Specialization detection accuracy** depends on heading clarity. PDFs
   that embed specialization names inside tables without clear section headers
   may not correctly route courses to the `specializations` block.

3. **OCR quality** — for scanned PDFs, OCR accuracy depends on scan quality
   and Tesseract configuration. Credits and course codes may be less reliable.

4. **L-T-P extraction** — only rows containing a clear `D-D-D` numeric pattern
   will have `credits` populated. Rows using "3+1" or "4 hrs" notation
   will have `credits: null`.

---

## Adding New Programs

1. **Add the PDF** to `curriculums/` with a descriptive filename, e.g.:
   `Curriculum-BTech-XX.pdf`

2. **Register it** in `curriculum/assembler.py` → `FILENAME_MAP`:
   ```python
   "curriculum-btech-xx": ("BTECH", "XX"),
   ```

3. **Add the URL** (if available) to `curriculum-links.txt`:
   ```
   [BTECH]
   XX: https://iitj.ac.in/.../Curriculum-BTech-XX.pdf
   ```

4. Re-run:
   ```bash
   python build_curriculum_json.py --parse
   ```

---

## Reasoning Behind Key Design Decisions

### Why two PDF parsers instead of one?

IIT curriculum PDFs are inconsistent. Some use proper table structures
(pdfplumber excels here), others embed content as free text blocks or use
two-column layouts (better handled by PyMuPDF's block extraction). Using both
maximises row coverage without requiring manual intervention per PDF.

### Why rapidfuzz for type classification?

Course-type labels in different PDFs use wildly different vocabulary:
"Program Core", "PC", "Compulsory Course", "Core (Programme)" all mean the
same thing. Exact matching would miss many; rapidfuzz's `partial_ratio` catches
these with a tuned threshold of 80, balancing precision and recall.

### Why track semester/specialization as running context?

Curriculum PDFs rarely embed semester information in every table row. Instead,
semester headings appear as page-level or section-level text. Tracking context
as a mutable state variable (updated on every heading encountered) is the most
reliable way to propagate this information to all rows extracted from that
region of the document.

### Why deduplicate by code+name in the assembler?

Several PDFs repeat their table headers on every page, which pdfplumber
sometimes captures as data rows. Deduplicating on code+name prevents these
from inflating the output.

### Why semester "0" instead of dropping unknown semesters?

Dropping rows with unknown semesters would silently discard valid course data
from PDFs where semester headings couldn't be detected. Routing them to
semester `"0"` preserves the data and makes the issue visible for review.
