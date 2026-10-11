# Amendment 2: execution log

This file records what happened when Amendment 2 was carried out (commit `2d6bf25`, tag `amendment-2`). Where the execution differs from the amendment text, the difference is stated. Sections 1–4 were written **before any rerun result was seen**. Section 5 is filled in after the reruns.

## 1. Timeline (UTC)

| Time | Event |
|---|---|
| 2026-10-11 01:01:40 | First-run `causalrca` on `re2-tt` starts (last job of `run_rcaeval_baselines.sh`) |
| 2026-10-11 02:49 | First-run confirmatory results computed (`out/re2/results.md`, now `results_pre_a2.md`) |
| 2026-10-11 ~03:01:40 | `causalrca` on `re2-tt` ends at the 2-hour limit (`exit=124`, 0 cases) |
| 2026-10-11 ~03:05 | Amendment 2 committed (`2d6bf25`), tagged `amendment-2`, pushed |
| 2026-10-11 03:05–03:08 | PyRCA install, package fixes (section 2), RCAEval patch (section 3) |
| 2026-10-11 03:08:29 | `run_rcaeval_a2.sh` starts |

## 2. Environment changes, with the differences from A2.1

A2.1 said PyRCA would be installed with `--no-deps` so that no installed package changes version. Two further changes turned out to be needed before `pyrca` would import. Each was recorded with `pip freeze --all` before and after.

| Change | Reason | Record |
|---|---|---|
| `sfr-pyrca` added: editable install of PyRCA at commit `411310d589fac5cb8e7bdce67d33eadb091a1083`, `--no-deps` | A2.1 | `out/pip_freeze_pre_a2.txt` → `out/pip_freeze_post_a2.txt` (one line added) |
| `setuptools` 84.0.0 → 80.10.2 | `pyrca/__init__.py` imports `pkg_resources`, only to read PyRCA's own version string. The installed setuptools 84.0.0 no longer ships `pkg_resources`; its own deprecation warning recommends pinning setuptools below 81. | `out/pip_freeze_all_pre_setuptools.txt` → `..._post_setuptools.txt` (one line changed) |
| `dill` 0.4.1 added | `pyrca/base.py` imports it | `out/pip_freeze_all_pre_dill.txt` → `..._post_dill.txt` (one line added) |

**Unmet PyRCA requirements.** pip reports that PyRCA's declared requirements `JPype1`, `schema`, `networkx>=2.6` and `scikit-learn<1.2` are not met. That is expected after a `--no-deps` install, and no installed package was changed to satisfy them. The ε-Diagnosis import path (`pyrca.analyzers.epsilon_diagnosis` → `pyrca.base`, `pyrca.analyzers.base`) uses none of them, and the import succeeds.

**Earlier results unaffected.** Neither change touches numpy, pandas, scipy, scikit-learn or any other package our pipeline or the completed RCAEval runs use at run time. No earlier result depends on setuptools or dill.

## 3. RCAEval patch (A2.2)

`scripts/rcaeval_patch_a2.py`, run in `~/rca/RCAEval` (log in `out/rcaeval_patch_a2.log`):

| Patch | File | sha256 before | sha256 after |
|---|---|---|---|
| P1 | `main.py` | `4e527f1f16736ef8353f7372bdbbd24270e6a383edb00f3a34b7a599d429e0e0` | `0ade6a58827aa9deeec2097a4c19a7eaf0527511d230dcc971c18025ee0fc94d` |
| P2 | `RCAEval/e2e/microcause.py` | `373bbe69b71a7608889169d8b114ed7234b71f70cb31157d195475c3b276855f` | `0df3f54cc1921bf10fde67ec5a812962888da06f1d3e8c9d4dfcc4287458da03` |
| P3 | `RCAEval/e2e/microcause.py` | `0df3f54c…` (after P2) | `5334d728ed958ba5514ac15fcc08e4f98b456625770b54e4bb3044b717367d9d` |

Both "before" hashes match a clean checkout of RCAEval at the pinned commit `259ea4167160256a74ad30004aa3d96a998c846e`, so the study copy had not been modified. The "after" hashes match the copy on which the patch was tested.

## 4. Corrections to the amendment text, and one rule fixed before results

**Correction (A2.2).** The amendment lists pingouin 0.7.0 among the study environment's versions. The study environment has pingouin **0.6.1**:
- tigramite 5.2.10.1, networkx 2.5 and pandas 3.0.6 are as stated;
- the synthetic MicroCause test was repeated with pingouin 0.6.1 and gave the same ranking as with 0.7.0: `svcb_cpu, svca_cpu, svcc_latency, frontend_latency`;
- in both versions `partial_corr` returns a one-row frame with an `r` column, so P3 reads the same value.

**Rule fixed before the rerun results.** We found that `06_evaluate.py` (frozen) adds an RCAEval method to the RQ1/RQ2 family only if the method has a ranking for at least one case. So the first-run results (`results_pre_a2.md`) contain **11** of the 13 pre-registered tests: `e_diagnosis` and `microcause` had no ranked case and were left out, rather than scored as chance as section 6 says. The following is fixed now, before any rerun result is seen:
- The paper reports the number of tests in each Holm family as computed.
- If any primary method still has no ranked case after the reruns, the paper's table lists it as all-chance, as section 6 says.
- That method's test against the deployed model is also reported, with a Holm adjustment over all 13 tests, as a sensitivity check.

## 5. Rerun outcome

From `out/run_rcaeval_a2.log` (UTC). The reruns started 2026-10-11 03:08:29 and finished 08:08:46. "Ranked" counts result files; "failed" counts `*_failed.json` files written under P1. Cases that were neither ranked nor failed were not reached before the 2-hour limit. All unranked cases are scored as chance.

| Method | System | First run | Rerun exit | Ranked | Failed | Not reached |
|---|---|---|---|---|---|---|
| e_diagnosis | ob | exit=1, 0 ranked | 0 | 90 | 0 | 0 |
| e_diagnosis | ss | exit=1, 0 ranked | 0 | 90 | 0 | 0 |
| e_diagnosis | tt | exit=1, 0 ranked | 0 | 90 | 0 | 0 |
| microcause | ob | exit=1, 0 ranked | 124 (2-h limit) | 27 | 0 | 63 |
| microcause | ss | exit=1, 0 ranked | 124 (2-h limit) | 21 | 0 | 69 |
| microcause | tt | exit=124, 0 ranked | not rerun | 0 | 0 | 90 |
| mmbaro | tt | exit=1, 69 ranked | 0 | 89 | 1 | 0 |
| mmnsigma | tt | exit=1, 69 ranked | 0 | 89 | 1 | 0 |

**Effect of each patch:**
- **P1:** the one Train Ticket case that stopped `mmbaro` and `mmnsigma` in the first run was recorded as failed, and the remaining 20 cases ran.
- **P2 and P3:** MicroCause produced rankings on RE2 for the first time. It remains too slow to finish a system within the limit.
- **MicroCause caveat:** RCAEval's harness passes it the root service's own latency as its SLI when that column exists (Amendment 3, section D), so its rankings are not label-free.
