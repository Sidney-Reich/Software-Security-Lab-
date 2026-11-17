#!/usr/bin/env bash
# Runs the whole experiment in Docker on Linux or macOS: preprocessing, then training, then testing.
# Usage: ./run.sh [all | preprocess | train | test] [--cases all|N] [--epochs 20]
#
#   ./run.sh                      everything: all 459 Juliet test cases, 20 epochs
#   ./run.sh preprocess --cases 3   a quick check that the toolchain works, on 3 test cases
#   ./run.sh train --epochs 20      training only (needs the preprocessing output)
#   ./run.sh test                   tests results/training/bgru.pt, or the reference model if you haven't trained one
#
# Results end up in results/preprocessing/, results/training/ and results/testing/.
set -euo pipefail
cd "$(dirname "$0")"
PHASE="${1:-all}"; shift || true
CASES=all; EPOCHS=20
while [ $# -gt 0 ]; do case "$1" in
  --cases) CASES="$2"; shift 2 ;; --epochs) EPOCHS="$2"; shift 2 ;; *) echo "unknown option $1"; exit 1 ;; esac; done
R="$PWD/results"; VEC="$R/preprocessing/vectors"
# On Linux, files a container writes keep the container's user id. The model containers run as you, and the
# preprocessing container hands its files back to you when it exits, so results/ never ends up owned by root.
ME="$(id -u):$(id -g)"
need_vectors() {
  [ -d "$VEC/dl_input_shuffle" ] || { echo "No preprocessing output in $VEC: run ./run.sh preprocess first."; exit 1; }
}

if [ "$PHASE" = all ] || [ "$PHASE" = preprocess ]; then
  echo "== 1. PREPROCESSING  (Juliet CWE-416 -> slices -> labels -> vectors)"
  docker build --load -t sysevr-preprocessing preprocessing
  rm -rf "$R/preprocessing"; mkdir -p "$R/preprocessing"
  docker run --rm -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" -v "$R/preprocessing:/results" sysevr-preprocessing "$CASES"
fi
if [ "$PHASE" = all ] || [ "$PHASE" = train ] || [ "$PHASE" = test ]; then
  need_vectors
  docker build --load -t sysevr-model model
fi
if [ "$PHASE" = all ] || [ "$PHASE" = train ]; then
  echo "== 2. TRAINING  (BGRU, $EPOCHS epochs, train split)"
  mkdir -p "$R/training"
  docker run --rm --user "$ME" -v "$VEC:/vectors:ro" -v "$R/training:/out" sysevr-model train.py /vectors /out --epochs "$EPOCHS"
fi
if [ "$PHASE" = all ] || [ "$PHASE" = test ]; then
  MODEL="$R/training/bgru.pt"; [ -f "$MODEL" ] || MODEL="$PWD/reference/training/bgru.pt"
  echo "== 3. TESTING  ($MODEL on the test split)"
  mkdir -p "$R/testing"
  docker run --rm --user "$ME" -v "$VEC:/vectors:ro" -v "$MODEL:/bgru.pt:ro" -v "$R/testing:/out" sysevr-model test.py /bgru.pt /vectors /out
fi
