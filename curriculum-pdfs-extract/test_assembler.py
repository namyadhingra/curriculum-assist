#!/usr/bin/env python3
from curriculum.assembler import assemble
import json

test_rows = [
    {
        "raw_code": "CS101",
        "raw_name": "Intro to CS",
        "raw_type": "PC",
        "raw_credits": "3-0-0",
        "specialization": None,
        "source_pdf": "curriculum-btech-cse.pdf",
        "page": 1,
    },
    {
        "raw_code": None,
        "raw_name": "AI & ML Track Course",
        "raw_type": "SC",
        "raw_credits": "3-0-0",
        "specialization": "AI & ML",
        "source_pdf": "curriculum-btech-cse.pdf",
        "page": 2,
    }
]

result = assemble(test_rows)
print("Output structure:")
print(json.dumps(result, indent=2))

# Check if 'semesters' key exists anywhere
def has_semesters(obj, depth=0):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "semesters":
                return True
            if has_semesters(v, depth+1):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if has_semesters(item, depth+1):
                return True
    return False

if has_semesters(result):
    print("\n❌ ERROR: 'semesters' key still found in output!")
else:
    print("\n✓ SUCCESS: No 'semesters' key in output")
