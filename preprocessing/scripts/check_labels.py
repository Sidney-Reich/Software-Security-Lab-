#!/usr/bin/env python3
"""Copies the labelled slices into the results folder and double-checks every label against Juliet's manifest.

SARD_DIR is the folder make_label_sard.py works in (C/test_data/data_source_add/sard). It holds <kind>_slices.txt
and the paper's <kind>_slices_label.pkl, a list of 0/1 labels in the same order as the slices.

Writes to OUT_DIR:
  slices/<kind>_slices.txt, labels/<kind>_slices_label.pkl   copied unchanged
  slices_index.csv                                           one row per slice, easy to open in a spreadsheet
and prints how many labels disagree with the manifest (there should be none).

Usage: check_labels.py SARD_DIR MANIFEST OUT_DIR
"""
import csv, pickle, re, shutil, sys
from pathlib import Path

sard, manifest, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
KINDS = {"api": "FC (library/API call)", "pointer": "PU (pointer usage)",
         "array": "AU (array usage)", "expr": "AE (arithmetic expression)"}
flaws, cur = {}, None
for line in open(manifest, encoding="utf-8"):
    m = re.search(r'<file path="([^"]+)"', line)
    if m:
        cur = m.group(1)
    m = re.search(r'<(?:flaw|mixed) line="(\d+)"', line)    # the same lines make_contain_all.py uses for labelling
    if m and cur and m.group(1) != "0":
        flaws.setdefault(cur, set()).add(int(m.group(1)))

(out / "slices").mkdir(parents=True, exist_ok=True); (out / "labels").mkdir(exist_ok=True)
rows, disagree = [], 0
for kind, desc in KINDS.items():
    txt_p, lab_p = sard / f"{kind}_slices.txt", sard / f"{kind}_slices_label.pkl"
    if not txt_p.exists():
        continue
    shutil.copy(txt_p, out / "slices")
    labels = pickle.load(open(lab_p, "rb"), encoding="latin1") if lab_p.exists() else []
    if lab_p.exists():
        shutil.copy(lab_p, out / "labels")
    # split the file the same way make_label_sard.make_label does, so slice i lines up with labels[i]
    blocks = txt_p.read_text(encoding="utf-8", errors="replace").split("------------------------------")[:-1]
    blocks = [b for b in blocks if [x for x in b.split("\n") if x.strip()]]
    if len(blocks) != len(labels):
        sys.exit(f"{kind}: {len(blocks)} slices but {len(labels)} labels")
    for block, label in zip(blocks, labels):
        lines = [x for x in block.split("\n") if x.strip()]
        parts = lines[0].split(" ")
        base, testcase = Path(parts[1]).name, Path(parts[1]).parent.name
        nums = [int(t) for t in (s.split(" ")[-1] for s in lines[1:]) if t.isdigit()]
        check = int(any(n in flaws.get(base, ()) for n in nums))
        disagree += check != label
        rows.append(dict(slice_id=f"{kind}:{parts[0]}", testcase=testcase, file=base, syvc_kind=desc,
                         focus=" ".join(parts[2:])[:80], n_lines=len(lines) - 1,
                         flaw_lines=";".join(map(str, sorted(flaws.get(base, ())))), label=label))
with open(out / "slices_index.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(rows[0]))
    w.writeheader(); w.writerows(rows)
vul = sum(r["label"] for r in rows)
print(f"{len(rows)} slices: {vul} vulnerable, {len(rows) - vul} not vulnerable, "
      f"from {len({r['testcase'] for r in rows})} test cases; label re-check disagreements: {disagree}")
