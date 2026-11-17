#!/usr/bin/env python3
"""Writes contain_all.txt, the input of the paper's make_label_sard.py.

In the paper's code this file comes from getVulLineForCounting.py, which reads SARD's manifest and writes one line
per flaw (and per <mixed> line): "<path of source file> <line number>". Its regex expects a language="..." attribute
that the Juliet manifest we use doesn't have, so we write the same format straight from manifest.xml, for the files
that were copied into SRC_DIR/<testcase>/.

Usage: make_contain_all.py MANIFEST SRC_DIR OUT_TXT
"""
import re, sys
from pathlib import Path

manifest, src, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
where = {f.name: f for f in src.glob("*/*") if f.is_file()}
lines, cur = [], None
for line in open(manifest, encoding="utf-8"):
    m = re.search(r'<file path="([^"]+)"', line)
    if m:
        cur = m.group(1)
    m = re.search(r'<(?:flaw|mixed) line="(\d+)"', line)
    if m and cur in where and m.group(1) != "0":
        lines.append(f"{where[cur]} {m.group(1)}")
out.write_text("\n".join(lines))   # no newline at the end: the paper's main() crashes on an empty last line
print(f"{len(lines)} flaw lines for {len(where)} staged files -> {out}")
