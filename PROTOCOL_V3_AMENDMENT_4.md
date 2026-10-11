# Amendment 4 to protocol v3: heuristic variants and onset uncertainty (exploratory)

**Date:** 2026-10-11. Written and committed **before any run described here**.

**What had been seen:**
- every RE2 result;
- the SimpleRCA diagnostic X8 (`out/re2/simplerca_diag.txt`);
- the Amendment 2 rerun counts (not their accuracy).

**What had not been seen:** any RE3 accuracy, any Amendment 3 analysis, and any `anon_full` result. The RE3 baselines (Amendment 3) are still running.

**Status:** exploratory and post hoc throughout. No confirmatory verdict changes.

## Why

Two questions a reviewer will ask:

1. **Our SimpleRCA-style heuristic scores far above the values Fang et al. publish for RE2.** Ours is 0.811; theirs are OB 0.47, SS 0.24 and TT 0.80. X8 shows the gap does not come from ties (0.815 with random tie-breaking). It points to three choices in our pre-registered rules:
   - one alert per metric column;
   - `-db` columns counting for their owner;
   - an alert on any change in a column that was constant before the injection (the σ = 0 rule).

   How much of the score rests on each?
2. **Every method, the model included, is told the exact injection time.** Simple change detectors gain most from this (Pham et al., ASE 2024). How do the comparisons change when the onset is wrong by two minutes?

## A. SimpleRCA variants

`scripts/13_simplerca_variants.py` uses the same windows and thresholds as `baselines.simplerca`.

| Variant | Rule |
|---|---|
| V0 | as pre-registered. Checked to reproduce `ranks_nonllm.json["simplerca"]` exactly. |
| V1 | V0 without the σ = 0 rule |
| V2 | V0 counting only the service's own columns (`-db` columns ignored) |
| V3 | at most one alert per signal type (metric, trace, log) per service, the per-modality form of Fang et al. |
| V4 | V1 + V2 + V3 |

**Runs:** RE2 and RE3, plus RE2 under each onset shift (section B).

**Report:**
- AC@1 per system;
- chance;
- Fang et al.'s published RE2 values;
- the deployed model minus each variant (cluster CI, permutation p).

The pre-registered comparator stays V0.

## B. Onset uncertainty (RE2)

**Shifts:** the injection time given to every method is shifted by **−120 s** and **+120 s**. Ground truth, cases and seeds are unchanged.
- **+120 s** (onset placed late): the baseline window contains the first two minutes of the fault.
- **−120 s** (onset placed early): the anomaly window starts two minutes before the fault.

**How each method is shifted:**

| Method | How |
|---|---|
| Pipeline: detectors, context, `detector_count`, `first_affected`, `largest_anomaly`, the pre-registered SimpleRCA | `03_build_contexts.py --onset-shift S` into `out/re2_shiftS`. Default behaviour is unchanged (checked: byte-identical outputs on synthetic data with logs and traces). |
| `lr_visible` | `05_classifiers.py` on the shifted features |
| SimpleRCA variants | `13_simplerca_variants.py --onset-shift S` |
| Deployed model | `gpt-oss-120b`, `annotated` condition, on the flagged cases of each shifted build; one vote, same settings |
| N-Sigma, BARO | RCAEval `main.py --tdelta S`, which shifts RCAEval's own windows the same way. Only these two are rerun: they are the fast primary methods that completed on every case. |

**Analysis** (`scripts/14_amendment4.py`):
- AC@1 of each method at −120, 0 and +120 s;
- the change from 0 s, with a 95% cluster CI;
- the deployed model's gap to each method at each shift;
- the number of flagged cases at each shift.

## Code changes and checks

**Changed:** `scripts/03_build_contexts.py` gains the `--onset-shift` option, default 0, which leaves output unchanged.

**New files:**
- `scripts/13_simplerca_variants.py`
- `scripts/14_amendment4.py`
- `scripts/run_amendment4_a.sh` (variants, shifted builds and model runs; can run alongside the RE3 baselines)
- `scripts/run_amendment4_b.sh` (N-Sigma and BARO with `--tdelta`; after the RE3 baselines, because both use RCAEval's `output/results`)

**Checks, done before this commit, on synthetic data with logs and traces loaded:**
- the default build is byte-identical to the Amendment 3 code;
- V0 reproduces the frozen SimpleRCA rankings on every case;
- both shifted builds, the variants, a mock model run and `14_amendment4.py` run end to end.

## Cost

- **Model calls:** about 490 (two shifted builds × the flagged RE2 cases, deployed model only), a few US dollars.
- **CPU:** about 2–3 hours for the variants and builds, and under an hour for N-Sigma and BARO.
