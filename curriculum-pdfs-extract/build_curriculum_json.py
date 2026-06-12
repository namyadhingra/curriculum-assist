#!/usr/bin/env python3
"""
build_curriculum_json.py
========================
CLI entry point for the IIT Jodhpur curriculum extractor.

Usage examples
--------------
# Parse all PDFs in ./curriculums/ → output/curriculum.json
python build_curriculum_json.py --parse

# Download missing PDFs first, then parse
python build_curriculum_json.py --download --parse

# Wipe everything and start fresh
python build_curriculum_json.py --force --download --parse

# Show debug output while parsing
python build_curriculum_json.py --parse --verbose

# Override default paths
python build_curriculum_json.py --parse --pdf-dir my_pdfs/ --links-file my_links.txt

Design notes
------------
- Folder creation (pdfs/, output/, logs/) happens at startup automatically.
- When --parse is used without --download, the tool uses whatever PDFs exist
  in --pdf-dir (default: curriculums/).
- A run summary is printed at the end showing counts and the output path.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# ─── Bootstrap: add project root to sys.path ──────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from curriculum.logger import setup_logging, get_logger, get_log_file_path
from curriculum.downloader import download_pdfs
from curriculum.parser import parse_pdf
from curriculum.assembler import assemble


# ─── Argument parsing ─────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_curriculum_json",
        description="Download curriculum PDFs and extract structured JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_curriculum_json.py --parse
  python build_curriculum_json.py --download --parse --verbose
  python build_curriculum_json.py --force --parse
        """,
    )
    p.add_argument(
        "--download",
        action="store_true",
        help="Download missing PDFs from --links-file.",
    )
    p.add_argument(
        "--parse",
        action="store_true",
        help="Parse PDFs in --pdf-dir and write output/curriculum.json.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-download and re-parse everything from scratch.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print DEBUG-level messages to the console.",
    )
    p.add_argument(
        "--pdf-dir",
        default="curriculums",
        metavar="DIR",
        help="Directory containing (or for storing) curriculum PDFs. Default: curriculums/",
    )
    p.add_argument(
        "--links-file",
        default="curriculum-links.txt",
        metavar="FILE",
        help="Path to the PDF links text file. Default: curriculum-links.txt",
    )
    p.add_argument(
        "--output-dir",
        default="output",
        metavar="DIR",
        help="Directory for output files. Default: output/",
    )
    p.add_argument(
        "--logs-dir",
        default="logs",
        metavar="DIR",
        help="Directory for log files. Default: logs/",
    )
    return p


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_arg_parser()
    args   = parser.parse_args()

    # Must specify at least one action
    if not args.download and not args.parse:
        parser.print_help()
        print("\n[ERROR] Specify at least one of --download or --parse.", file=sys.stderr)
        return 1

    # ── Resolve paths ──────────────────────────────────────────────────────
    pdf_dir    = Path(args.pdf_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    logs_dir   = Path(args.logs_dir).resolve()
    links_file = Path(args.links_file).resolve()

    # ── Create directories ─────────────────────────────────────────────────
    for d in (pdf_dir, output_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    # ── Setup logging ──────────────────────────────────────────────────────
    log_file = setup_logging(logs_dir, verbose=args.verbose)
    logger   = get_logger("main")
    logger.info("=" * 60)
    logger.info("IIT Jodhpur Curriculum Extractor — starting run")
    logger.info("pdf_dir    : %s", pdf_dir)
    logger.info("output_dir : %s", output_dir)
    logger.info("log_file   : %s", log_file)

    # ── Force wipe ─────────────────────────────────────────────────────────
    if args.force:
        logger.info("--force: wiping existing PDFs and output")
        for f in pdf_dir.glob("*.pdf"):
            f.unlink()
        out_json = output_dir / "curriculum.json"
        if out_json.exists():
            out_json.unlink()

    # ── Download ───────────────────────────────────────────────────────────
    if args.download:
        if not links_file.exists():
            logger.error("Links file not found: %s", links_file)
            return 1
        logger.info("Downloading PDFs from %s", links_file)
        download_pdfs(
            links_file=links_file,
            pdf_dir=pdf_dir,
            force=args.force,
        )

    # ── Parse ──────────────────────────────────────────────────────────────
    if args.parse:
        pdf_files = sorted(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            logger.error(
                "No PDF files found in %s. "
                "Run with --download to fetch them first.",
                pdf_dir,
            )
            return 1

        logger.info("Found %d PDF(s) to parse.", len(pdf_files))

        all_rows: list[dict] = []
        parse_stats = {"success": 0, "failure": 0, "total_rows": 0}

        for pdf_path in pdf_files:
            logger.info("-" * 50)
            logger.info("Parsing: %s", pdf_path.name)
            try:
                rows = parse_pdf(pdf_path)
                all_rows.extend(rows)
                parse_stats["total_rows"] += len(rows)
                if rows:
                    parse_stats["success"] += 1
                else:
                    parse_stats["failure"] += 1
            except Exception as exc:
                logger.error("FATAL | %s | %s", pdf_path.name, exc, exc_info=args.verbose)
                parse_stats["failure"] += 1

        logger.info("=" * 60)
        logger.info(
            "Parse complete: %d success / %d failure / %d total rows",
            parse_stats["success"],
            parse_stats["failure"],
            parse_stats["total_rows"],
        )

        # ── Assemble JSON ──────────────────────────────────────────────────
        logger.info("Assembling JSON structure …")
        curriculum_json = assemble(all_rows)

        # ── Write output ───────────────────────────────────────────────────
        out_path = output_dir / "curriculum.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(curriculum_json, fh, indent=2, ensure_ascii=False)

        logger.info("Output written → %s", out_path)

        # ── Run summary ────────────────────────────────────────────────────
        _print_summary(curriculum_json, parse_stats, out_path, log_file)

    return 0


# ─── Summary helper ────────────────────────────────────────────────────────────

def _print_summary(
    data: dict,
    stats: dict,
    out_path: Path,
    log_file: Path,
) -> None:
    """Print a human-readable run summary to stdout."""
    sep = "-" * 60
    print(f"\n{sep}")
    print("  CURRICULUM EXTRACTOR -- RUN SUMMARY")
    print(sep)
    print(f"  PDFs parsed (success) : {stats['success']}")
    print(f"  PDFs with no rows     : {stats['failure']}")
    print(f"  Raw rows extracted    : {stats['total_rows']}")
    print()

    total_courses = 0
    for program, branches in data.items():
        if not branches:
            continue
        print(f"  [{program}]")
        for branch, content in branches.items():
            sems  = content.get("semesters", {})
            specs = content.get("specializations", {})
            branch_courses = sum(
                len(courses)
                for sem_data in sems.values()
                for courses in sem_data.values()
            )
            total_courses += branch_courses
            spec_info = f"  +{len(specs)} specializations" if specs else ""
            print(f"    {branch:6s}  {len(sems):2d} semesters  {branch_courses:4d} courses{spec_info}")
        print()

    print(f"  Total courses         : {total_courses}")
    print(f"  Output JSON           : {out_path}")
    print(f"  Log file              : {log_file}")
    print("-" * 60)


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(main())
