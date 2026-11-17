# SySeVR on Juliet use-after-free (CWE-416)

An implementation of SySeVR (Li et al., "SySeVR: A Framework for Using Deep Learning to Detect Software
Vulnerabilities", IEEE TDSC 19(4), 2022) applied to one vulnerability type: use-after-free (CWE-416), on the
Juliet C/C++ 1.3 test suite (NIST SARD).

Preprocessing uses the authors' released code ([github.com/SySeVR/SySeVR](https://github.com/SySeVR/SySeVR),
commit `db9ceaf`). The model is the paper's BGRU, rewritten in PyTorch. Everything runs on CPU inside Docker.

```
Juliet CWE-416 ──► 1. PREPROCESSING ──────────────────────────────► 2. TRAINING ──► 3. TESTING
 459 test cases     graphs → slices → labels → vectors, 80/20 split    BGRU, 20 epochs   test split, metrics
```

## Repository layout

| Path                                      | Phase | What it does                                                                                  |
| ----------------------------------------- | ----- | --------------------------------------------------------------------------------------------- |
| `preprocessing/Dockerfile`                | 1     | Toolchain: Joern 0.3.1, Neo4j 2.1.5, Python 2.7, gensim 3.4, SySeVR code at a pinned commit   |
| `preprocessing/run.sh`                    | 1     | Downloads Juliet CWE-416, then runs steps 1-4                                                 |
| `preprocessing/steps/1_build_graphs.sh`   | 1     | Joern parses the code; the paper's scripts build CFGs, PDGs and the call graph                |
| `preprocessing/steps/2_extract_slices.sh` | 1     | SyVCs (API calls, pointer use, array use, arithmetic) → SeVCs (slices)                        |
| `preprocessing/steps/3_label_slices.sh`   | 1     | Paper's `make_label_sard.py`: a slice is 1 if it holds a Juliet flaw line; labels re-checked  |
| `preprocessing/steps/4_vectorize.sh`      | 1     | Paper's `data_preprocess`: dedupe, symbolize, word2vec, 80/20 split by program, pad to 500    |
| `preprocessing/scripts/`                  | 1     | Small adapters around the paper's scripts (listed under "Differences from the released code") |
| `model/bgru.py`                           | 2, 3  | The BGRU network                                                                              |
| `model/train.py`                          | 2     | Trains on the train split only; saves `bgru.pt`                                               |
| `model/test.py`                           | 3     | Tests a saved model on the test split; writes metrics and per-slice predictions               |
| `reference/`                              |       | Outputs of our reference run (see "Expected results")                                         |
| `run.sh`, `run.ps1`                       |       | Run all three phases (Linux/macOS, Windows)                                                   |

## How to run

Requirements: Docker (Docker Desktop on Windows/macOS), 4 CPU cores and 8 GB RAM recommended, about 10 GB disk,
internet access for the first build (Ubuntu packages, SySeVR repository, Juliet mirror, PyTorch).

Linux / macOS:

```bash
./run.sh                          # all three phases: 459 test cases, 20 epochs
./run.sh preprocess --cases 3     # quick toolchain check on 3 test cases (a few minutes after the build)
./run.sh train --epochs 20        # phase 2 only (needs phase 1 output)
./run.sh test                     # phase 3 only: tests results/training/bgru.pt, or reference/training/bgru.pt if absent
                                  # (the reference model needs the full 459-case preprocessing output: same word vectors)
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 # To run the entire pipeline at once
powershell -ExecutionPolicy Bypass -File .\run.ps1 -Phase preprocess -Cases 3 # To run every phase separately
```

Outputs:

| Folder                   | Files                                                                                                                                                                                                                      |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `results/preprocessing/` | `slices/*.txt` (slices as text), `labels/*.pkl`, `slices_index.csv` (one row per slice), `vectors/` (word2vec model, train/test vectors, `vectorize_stats.json`), `benchmark.csv` (time, CPU, peak RAM per stage), `logs/` |
| `results/training/`      | `bgru.pt` (weights), `epochs.csv` (loss and time per epoch), `training.json` (settings, time, RAM)                                                                                                                         |
| `results/testing/`       | `metrics.json` (TP, FP, FN, TN, FPR, FNR, accuracy, precision, recall, F1, train/test overlap, inference speed), `test_predictions.csv`                                                                                    |

## 1. Preprocessing

Input: the 459 CWE-416 test cases of Juliet 1.3, downloaded from the GitHub mirror
[arichardson/juliet-test-suite-c](https://github.com/arichardson/juliet-test-suite-c). Each test case holds a bad
(vulnerable) function and good (fixed) functions; `manifest.xml` gives every flaw line.

| Step             | Paper's code                                                                                            | Output                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 1 Build graphs   | Joern 0.3.1 parse; `get_cfg_relation`, `complete_PDG`, `access_db_operate` (queries Neo4j)              | CFG, PDG and call graph per function          |
| 2 Extract slices | `points_get` (SyVCs), `extract_df` (SeVCs)                                                              | `slices/{api,pointer,array,expr}_slices.txt`  |
| 3 Label slices   | `make_label_sard.py`                                                                                    | `labels/*_label.pkl`, `slices_index.csv`      |
| 4 Vectorize      | `create_hash`, `delete_list`, `process_dataflow_func`, `create_w2vmodel`, `get_dl_input`, `dealrawdata` | `vectors/dl_input_shuffle/{train,test}/*.pkl` |

Step 4 details: exact duplicate slices are removed; variable and function names become `variable_N` / `func_N`;
word2vec (skip-gram, 30 numbers per word, seed 1) is trained on all slices; programs are shuffled with seed 113 and
split 80/20 (train/test), so all slices of a program are on the same side; every slice is padded or cut to 500 words.

## 2. Training

`model/train.py`, the paper's settings: BiGRU 256 → Dropout 0.2 → BiGRU 256 → Dropout 0.2 → Dense(1, sigmoid);
binary cross-entropy; Adamax, learning rate 0.002; batch 16; 20 epochs; float32; shuffle seed 2018 (released
`bgru.py`). Padded words are masked. Training reads the train split only.

## 3. Testing

`model/test.py` loads a saved model and predicts every slice of the test split; a slice is vulnerable when the
probability is ≥ 0.5. It reports the paper's metrics and the inference speed.

It also measures train/test overlap. Duplicates are removed before names are symbolized, so a test slice can still be
word-for-word identical to a training slice. `test.py` counts those slices, says whether their training copies have
the same label, and repeats the metrics on the test slices that have no identical copy (`train_test_overlap` in
`metrics.json`, column `train_copy_labels` in `test_predictions.csv`).

## Expected results

All numbers below are **measured** on one reference run (cloud VM, 4 CPU cores, 15 GB RAM, Docker on Linux,
2026-11-13). The output files are in `reference/`. The data numbers and test metrics are deterministic: two runs of this code
and one run of our earlier, unrefactored code gave byte-identical slices, labels, vectors and model weights.
Times vary between runs and machines.

**Data** (`reference/preprocessing/vectorize_stats.json`, `slices_index.csv`)

|                                                | Slices | Vulnerable | Not vulnerable |
| ---------------------------------------------- | ------ | ---------- | -------------- |
| Extracted from 459 test cases                  | 5,061  | 728        | 4,333          |
| After removing exact duplicates (263 programs) | 1,960  | 415        | 1,545          |
| Train split (80% of programs)                  | 1,574  | 335        | 1,239          |
| Test split (20% of programs, 53 programs)      | 386    | 80         | 306            |

Labels re-checked against `manifest.xml`: 0 disagreements. By slice kind after dedup: API call 1,144,
pointer use 765, arithmetic 50, array use 1. Vocabulary 73 words; words per slice: median 62, max 117 (none over 500).

**Test metrics** (`reference/testing/metrics.json`, model `reference/training/bgru.pt`, 20 epochs)

| TP  | FP  | FN  | TN  | Precision | Recall | F1    | FPR   | FNR   | Accuracy |
| --- | --- | --- | --- | --------- | ------ | ----- | ----- | ----- | -------- |
| 78  | 2   | 2   | 304 | 0.975     | 0.975  | 0.975 | 0.007 | 0.025 | 0.990    |

**Cost** (`reference/preprocessing/benchmark.csv`, `reference/training/training.json`, `reference/testing/metrics.json`)

| Phase                             | Time (4 cores)                                                | Peak RAM                              |
| --------------------------------- | ------------------------------------------------------------- | ------------------------------------- |
| Preprocessing, all 459 test cases | 12.6 min (of which `complete_PDG` 6.4 min)                    | Neo4j server 6.2 GB; scripts ≤ 1.0 GB |
| Training, 20 epochs               | 6.2 min (about 18.5 s per epoch)                              | 0.7 GB                                |
| Testing, 386 slices               | 6.7 ms per slice one at a time; 899 slices/s in batches of 64 | 0.5 GB                                |

Preprocessing time is dominated by the Neo4j graph queries and changes from run to run (our runs: 10.5, 12.6 and
13.2 min); extra cores barely help. Model size: 1,625,601 parameters, 6.5 MB file.

Notes on the reference run:

- The reference PyTorch was the PyPI build of torch 2.4.1 (`2.4.1+cu121`, run on CPU), because the CPU-only index
  `download.pytorch.org` was not reachable from that machine. `model/Dockerfile` installs the CPU-only build of the
  same version. Small floating-point differences between builds are possible; we have not measured them.
- Juliet's test cases are generated from templates, so slices in the train and test splits can be very similar.
  The test F1 above should not be read as performance on real-world code.

## Differences from the released code

The released code does not run end to end as published. These changes were needed; the ones marked \* can change a
number, the others only connect file names and formats.

| Where                         | Change                                                                                                                                                                                                               | Why                                                                                                                           |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Scope                         | CWE-416 only                                                                                                                                                                                                         | Study design                                                                                                                  |
| `scripts/make_contain_all.py` | Writes `contain_all.txt` (input of `make_label_sard.py`) directly from Juliet's `manifest.xml`                                                                                                                       | The paper's `getVulLineForCounting.py` needs a `language=` attribute this manifest lacks                                      |
| `scripts/label_with_paper.py` | Runs `make_label_sard.main()` unchanged, but returns an empty label list for an empty slice file                                                                                                                     | The paper's code crashes on an empty file                                                                                     |
| `steps/2_extract_slices.sh`   | Focus-variable header `[u'data']` written by `extract_df.py` becomes `data`                                                                                                                                          | Later scripts expect the plain name                                                                                           |
| `scripts/vectorize.py`        | Label list → dict keyed by slice header; duplicate list saved under the name `process_dataflow_func.py` opens; slice files named as `get_dldata` selects them; empty files skipped; unused `imblearn` import stubbed | The released scripts disagree with each other on these formats                                                                |
| `scripts/vectorize.py` \*     | Word vectors have 30 numbers                                                                                                                                                                                         | `create_w2vmodel.py` trains 30; released `dealrawdata.py` says 40                                                             |
| `scripts/vectorize.py` \*     | Test set = all slices of all test programs (same seed-113 split, same train files)                                                                                                                                   | Released `get_dldata` keeps pointer slices of only 2/8 of the test programs, and `dealrawdata` keeps only API-call test files |
| `scripts/vectorize.py` \*     | Every folder listing is sorted                                                                                                                                                                                       | `os.listdir` order depends on the file system, so the seeded split and word2vec differed between Windows and Linux            |
| `model/` \*                   | PyTorch instead of Keras: standard sigmoid gates (Keras: hard_sigmoid) and a second bias per GRU gate, 1,625,601 parameters instead of 1,622,529 (+0.2%)                                                             | PyTorch's GRU                                                                                                                 |
| `model/train.py` \*           | Trains on `train/` and tests on `test/`                                                                                                                                                                              | Released `bgru.py` skips every training file (inverted filter) and evaluates on the training folder                           |
| `lib.sh`                      | Neo4j's `data/rrd` monitoring file is deleted before each start                                                                                                                                                      | Neo4j 2.1.5 on Java 11 otherwise hangs on restart                                                                             |
| `scripts/check_labels.py`     | Re-checks every label against `manifest.xml` (the same flaw and mixed lines `make_contain_all.py` writes) and writes `slices_index.csv`                                                                              | Verification only; changes nothing                                                                                            |

## Citation

Z. Li, D. Zou, S. Xu, H. Jin, Y. Zhu, Z. Chen, "SySeVR: A Framework for Using Deep Learning to Detect Software
Vulnerabilities," IEEE Transactions on Dependable and Secure Computing, 19(4), 2244-2258, 2022.
