# Amendment 2 to protocol v3: execution fixes for the RCAEval baselines

**Date:** 2026-10-11. Written and committed **before** any rerun described here.
**Frozen protocol:** commit `939df23`, tag `protocol-v3-frozen-2`. Amendment 1: commit `d013b19`, tag `amendment-1`.
**Status:** the confirmatory results with the first baseline runs had been computed (`out/re2/results.md`, 2026-10-11 02:49 UTC). Those results are kept unchanged as `results_pre_a2.md` and `ranks_rcaeval_pre_a2.json`, and the paper reports them.

## Why this amendment is needed

Section 6 pre-registers eight primary baselines and three secondary ones. Section 9 says a baseline that fails on a case is scored as chance for that case.

Four methods produced **no result on any system**:
- `e_diagnosis`
- `microcause`
- `tracerca`
- `microrank`

Two primary methods stopped partway through Train Ticket:
- `mmbaro` (69 of 90 cases)
- `mmnsigma` (69 of 90 cases)

The logs show the causes. Except for D4, they are faults in how we ran RCAEval, not properties of the methods:

| # | Method(s) | Cause (from `logs_baselines/`) |
|---|---|---|
| D1 | `e_diagnosis` | `ModuleNotFoundError: pyrca`. RCAEval's SETUP.md installs PyRCA as a separate step, which our setup missed. |
| D2 | `microcause` | `pcmci_links` is `None`. RCAEval requires `tigramite>=4.2.2.1`, and pip installed 5.x, where `PCMCI.return_significant_links` returns `None`. tigramite 4.2.2.1 does not build on Python 3.12. After this was fixed, a test on synthetic data hit a second incompatibility (D2b): `float(ret.r)` fails under pandas 3, which RCAEval's own `pandas>2.0.1` allows. |
| D3 | `mmbaro`, `mmnsigma` on TT | One case raised (`Found array with 0 sample(s)` in a scaler). RCAEval `main.py` re-raises any per-case exception (`raise e` placed before its own failure-recording code), so the whole run stopped and the remaining cases were never attempted. This contradicts section 9, which expects a per-case failure. |
| D4 | `tracerca`, `microrank` | `KeyError: 'methodName'`. At the pinned commit, `main.py` passes these methods the metrics table, but they expect a span table. They cannot run on RE2 through `main.py` as pinned. |

## What changes

**A2.1 Install PyRCA.** It is installed, pinned to commit `411310d589fac5cb8e7bdce67d33eadb091a1083`, into the existing Python 3.12 environment with `pip install --no-deps -e .`, so that no installed package changes version. `pip freeze` is saved before and after the install. RCAEval's `main.py` already imports `e_diagnosis` under Python 3.12. SETUP.md suggests its Python 3.8 "rcd" environment instead, but ε-Diagnosis needs only numpy, pandas, pyyaml and dill, so the algorithm is the same.

**A2.2 Patch RCAEval.** `scripts/rcaeval_patch_a2.py` makes three minimal source patches. It is idempotent and prints the sha256 of each file before and after.
- **P1, `main.py`:** remove the `raise e` placed in front of RCAEval's own failure-recording code. A failing case is then written as `*_failed.json`, the run continues, and the failed case is scored as chance (section 9).
- **P2, `e2e/microcause.py`:** replace the call to `return_significant_links` with a verbatim copy of the tigramite 4.2.2.1 function body. The causal graph is built exactly as the pinned version intends.
- **P3, `e2e/microcause.py`:** read the partial correlation with `.iloc[0]`. It is the same number.

Before this amendment was written, the patched MicroCause was run end to end on synthetic data with the same package versions as the study environment (numpy 1.26.4, pandas 3.0.6, networkx 2.5, tigramite 5.2.10.1, pingouin 0.7.0). It returned a ranking.

**A2.3 Reruns.** `scripts/run_rcaeval_a2.sh` reruns the following, with the same 2-hour limit per method and system and the same `--length 20`:
- `e_diagnosis` on OB, SS and TT;
- `microcause` on OB and SS;
- `mmbaro` and `mmnsigma` on TT.

Each first-run folder is moved to `output/kept_pre_a2/`. The following are **not** rerun:
- `microcause` on TT: the first run timed out before finishing its first case, which is unrelated to D2;
- `circa` and `mmcirca` on TT, and `causalrca`: timeouts;
- `nsigma`, `baro`, and `circa`, `mmcirca`, `mmbaro`, `mmnsigma` on OB and SS: completed.

**A2.4 Methods not run.** `tracerca` and `microrank` are reported as **not runnable through RCAEval's `main.py` at the pinned commit**. We do not write our own trace adapter for them, because it would be our implementation rather than RCAEval's. They are secondary methods, so no confirmatory test changes.

## Analysis

- `07_collect_rcaeval.py`, `06_evaluate.py` and `10_exploratory.py` are rerun unchanged on the merged `output/kept/`.
- **The confirmatory RQ1/RQ2 family (13 tests, Holm) uses the post-amendment baselines.** The pre-amendment results are reported in full alongside them as a sensitivity analysis.
- For every baseline, the paper's table gives:
  - cases with a ranking;
  - cases failed;
  - cases timed out (chance);
  - for the four methods affected by D1–D3, the first-run status.
- Every number for the deployed model, the classifiers, the heuristics and every LLM condition is unaffected. None of them depends on RCAEval.
