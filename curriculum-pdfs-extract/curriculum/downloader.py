"""
curriculum/downloader.py
------------------------
Handles PDF download and file-existence checks.

Since all PDFs for this project are already present in the `curriculums/`
folder (some were sourced from HTML pages that cannot be scraped
automatically), the download step is intentionally kept minimal.

What this module does
---------------------
1. Reads `curriculum-links.txt` and parses its section/key/URL structure.
2. For each entry, checks whether a matching file already exists in the
   PDF directory.
3. If `--download` is requested and a file is missing, it attempts
   `requests.get(url)` and validates that the response is a PDF.
4. If the URL returns HTML (e.g. B.S. Chemistry, B.Tech CI), it logs a
   warning and skips rather than saving garbage data.
5. `--force` re-downloads even if files already exist.

Design choices
--------------
- File matching uses a loose substring check (pdf_dir / "*{branch}*") rather
  than an exact name so that URLs with long identifiers still hit cached files.
- Content-Type is checked before writing to avoid saving HTML error pages.
- tqdm progress bar is used only when downloading; the import is soft so the
  rest of the tool works without it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import requests

from .logger import get_logger

logger = get_logger("downloader")

# Matches section headers like [BTECH], [BS], [BSC]
_SECTION_RE = re.compile(r"^\[([A-Z]+)\]$")
# Matches "KEY: URL" lines (handles keys with spaces and parentheses)
_ENTRY_RE   = re.compile(r"^(.+?):\s+(https?://\S+)$")


# ─── Public API ────────────────────────────────────────────────────────────────

def read_links_file(links_file: str | Path) -> list[dict]:
    """
    Parse curriculum-links.txt and return a list of link descriptors:
    [
      {
        "program": "BTECH",
        "label":   "CSE",
        "url":     "https://..."
      },
      ...
    ]
    """
    entries: list[dict] = []
    current_section = "UNKNOWN"

    with open(links_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _SECTION_RE.match(line)
            if m:
                current_section = m.group(1).upper()
                continue
            m = _ENTRY_RE.match(line)
            if m:
                label, url = m.group(1).strip(), m.group(2).strip()
                entries.append({
                    "program": current_section,
                    "label":   label,
                    "url":     url,
                })

    logger.debug("read_links_file | found %d entries", len(entries))
    return entries


def find_existing_pdf(label: str, pdf_dir: Path) -> Optional[Path]:
    """
    Search pdf_dir for a file whose name contains the label (case-insensitive).
    Returns the first match, or None.
    """
    label_clean = re.sub(r"[^A-Za-z0-9]", "", label).lower()
    for p in sorted(pdf_dir.glob("*.pdf")):
        stem_clean = re.sub(r"[^A-Za-z0-9]", "", p.stem).lower()
        if label_clean in stem_clean:
            return p
    return None


def download_pdfs(
    links_file: str | Path,
    pdf_dir: str | Path,
    force: bool = False,
    timeout: int = 60,
) -> None:
    """
    Download missing PDFs from curriculum-links.txt into pdf_dir.

    Parameters
    ----------
    links_file : path to the links text file
    pdf_dir    : directory where PDFs are stored
    force      : if True, re-download even if file exists
    timeout    : HTTP request timeout in seconds
    """
    pdf_dir = Path(pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    entries = read_links_file(links_file)

    # Soft-import tqdm
    try:
        from tqdm import tqdm
        iterable = tqdm(entries, desc="Downloading PDFs", unit="file")
    except ImportError:
        iterable = entries

    for entry in iterable:
        label   = entry["label"]
        url     = entry["url"]
        program = entry["program"]

        existing = find_existing_pdf(label, pdf_dir)
        if existing and not force:
            logger.info("SKIP_DOWNLOAD | already exists: %s", existing.name)
            continue

        logger.info("DOWNLOAD | %s / %s → %s", program, label, url)
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except Exception as exc:
            logger.error("DOWNLOAD_FAIL | %s / %s | %s", program, label, exc)
            continue

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            logger.warning(
                "NOT_PDF | %s / %s | Content-Type=%r — skipping (HTML page or redirect?)",
                program,
                label,
                content_type,
            )
            continue

        # Build output filename
        url_filename = Path(url.split("?")[0]).name
        suffix = ".pdf" if not url_filename.lower().endswith(".pdf") else ""
        out_name = f"Curriculum-{program}-{label}{suffix}" if not url_filename else url_filename
        out_path = pdf_dir / out_name

        out_path.write_bytes(resp.content)
        logger.info("SAVED | %s (%d KB)", out_path.name, len(resp.content) // 1024)
