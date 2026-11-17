#!/usr/bin/env python3
"""Copies the Juliet CWE-416 test cases into SRC_DIR, one folder per test case. SySeVR's slicer uses the folder
name as the program id, so files that belong to the same test case have to share a folder.

Usage: select_programs.py JULIET_DIR SRC_DIR [all | N | name1,name2,...]
  N takes a small sample of N test cases, spread over the variants (malloc/free in C, new/delete in C++)."""
import re, shutil, sys
from pathlib import Path

jul, src = Path(sys.argv[1]), Path(sys.argv[2])
sel = sys.argv[3] if len(sys.argv) > 3 else "all"
cases = {}
# Juliet spreads some test cases over several files. The test case name is the file name minus the part that
# tells those files apart: a letter (..._51a.c, ..._51b.c), or _bad / _good1 in class-based cases, where
# ..._01_bad.cpp has the flaw and ..._01_good1.cpp the fixed version.
PART = re.compile(r"(?:(?<=\d)[a-z]|_bad|_good\d+)?\.(?:c|cpp)$")
for f in sorted((jul / "testcases" / "CWE416_Use_After_Free").iterdir()):
    if f.suffix in (".c", ".cpp"):
        cases.setdefault(PART.sub("", f.name), []).append(f)
names = sorted(cases)
if sel == "all":
    pick = names
elif sel.isdigit():
    n = int(sel); step = max(1, len(names) // n); pick = names[::step][:n]
else:
    pick = sel.split(",")
if src.exists():
    shutil.rmtree(src)
for name in pick:
    d = src / name; d.mkdir(parents=True)
    for f in cases[name]:
        shutil.copy(f, d / f.name)
print(f"selected {len(pick)} of {len(names)} test cases")
