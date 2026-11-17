#!/usr/bin/env bash
# Downloads the CWE-416 part of Juliet C/C++ 1.3 (NIST SARD, public domain) from the GitHub mirror at
# github.com/arichardson/juliet-test-suite-c. Ubuntu 20.04 ships git 2.25, which has no `git clone --sparse`,
# hence the separate sparse-checkout commands. The mirror is pinned to one commit (2025-03-27), so every run gets
# exactly the same files.
set -euo pipefail
JULIET_COMMIT="${JULIET_COMMIT:-f88433e3443648a17671398797a04ea1f8e1a274}"
D="$1"; mkdir -p "$D"; cd "$D"
rm -rf juliet
git clone -q --filter=blob:none --no-checkout https://github.com/arichardson/juliet-test-suite-c juliet
git -C juliet sparse-checkout init --cone
git -C juliet sparse-checkout set testcases/CWE416_Use_After_Free testcasesupport
git -C juliet checkout -q "$JULIET_COMMIT"
n=$(ls juliet/testcases/CWE416_Use_After_Free | wc -l)
[ "$n" -eq 520 ] || { echo "Juliet download incomplete ($n files, expected 520)"; exit 1; }
echo "Juliet CWE-416: $n files in $D/juliet"
