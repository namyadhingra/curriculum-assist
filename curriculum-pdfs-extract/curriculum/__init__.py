"""
curriculum — internal package for the curriculum PDF extractor tool.

Modules
-------
logger      : Structured logging to file + console.
parser      : PDF → raw CourseRow extraction (pdfplumber + PyMuPDF fallback).
normaliser  : Data cleaning, course-type fuzzy mapping, code/credit normalisation.
assembler   : Normalised rows → final nested JSON structure.
downloader  : PDF download + file-existence check helpers.
"""
