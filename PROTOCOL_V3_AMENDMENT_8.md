# Amendment 8 to protocol v3: is it the evidence or the prompt, and does the generic pipeline depend on the onset?

**Date:** 2026-10-13. Written and committed **before any run described here**.

**Earlier record:** frozen protocol `939df23` (tag `protocol-v3-frozen-2`); Amendments 1–7 (tags `amendment-1` … `amendment-7`).

**What had been seen:** every result reported so far, including Amendment 7, and an independent pre-submission review of the paper.

**What had not been seen:**
- any output of the two crossed conditions defined here;
- any generic-pipeline summary or output with a shifted onset.

**Status:** pre-registered tests of two points the review raised. No earlier verdict, condition, statistic or file behaviour changes.

## Why

The same model scored 0.44 on RE2 in the deployed agent and 0.87 in the generic pipeline (Amendment 7, descriptive). The two pipelines differ in two ways at once:
- **Evidence:** the user message, i.e. what the pipeline extracts and shows.
- **Prompt:** the system prompt, i.e. persona, instructions and answer schema.

A 2×2 that crosses them tells which of the two carries the difference.

The generic summary compares the windows before and after the given onset, as N-Sigma does. Under a late onset, N-Sigma lost most of its accuracy (H5c). Whether the generic pipeline shares this fragility is untested.

## Part A: evidence × prompt

The 2×2 uses the deployed agent's flagged cases (245 RE2, 78 RE3) and the deployed model `gpt-oss-120b` with one vote and the frozen settings. Evidence and prompt are defined as follows:
- **Evidence E** is the user message.
  - E_d is the deployed agent's user message exactly as in `annotated`: summary, context lines and anomalous-metrics/logs blocks.
  - E_g is the generic pipeline's user message exactly as in `g_full`.
- **Prompt P** is the system message.
  - P_d is the deployed system prompt, with its persona, instructions and answer schema.
  - P_g is the generic system prompt.

The four cells:

| Cell | Condition | Source |
|---|---|---|
| E_d P_d | `annotated` | existing run (main study) |
| E_g P_g | `g_full` | existing run (Amendment 7), restricted to the same flagged cases |
| E_g P_d | `x_dsys_guser` | new |
| E_d P_g | `x_gsys_duser` | new |

- The answer is parsed and ranked by the frozen rule.
- The schema retry uses the schema of the system prompt in use.
- Restricting every cell to the flagged cases removes the severity gate as a difference between the cells.

## Part B: the generic pipeline under onset shifts

The generic summaries are rebuilt with the injection time shifted by +120 s and by −120 s, and `g_full` is run for the deployed model on all RE2 and RE3 cases. Everything else is as in Amendment 7. This is the same shift as in Amendments 4 and 5.

## Hypotheses and decision rules

Statistics follow the protocol and Amendments 6–7:
- the unit is the case;
- clusters are (system, root service, fault), with RE2 and RE3 pooled as separate clusters;
- the cluster bootstrap uses 2,000 resamples and the sign-flip permutation test 10,000;
- the exact p is reported alongside, and a disagreement between the two Holm values about 0.05 is called borderline.

| # | Hypothesis | Per-case statistic | Supported if |
|---|---|---|---|
| H8a | The evidence a pipeline shows, not its prompt, carries the difference between the pipelines: the generic user message raises accuracy. | evidence effect ((E_g P_g + E_g P_d) − (E_d P_g + E_d P_d)) / 2, RE2 + RE3 flagged | mean > 0 and Holm p < 0.05 |
| H8b | The system prompt changes accuracy (two-sided question). | prompt effect ((E_g P_g + E_d P_g) − (E_g P_d + E_d P_d)) / 2, same cases | Holm p < 0.05; the sign is the finding; a null is reported as "not detected" |
| H8c | The generic pipeline, like N-Sigma, loses accuracy when the onset is 120 s late. | `g_full` at the given onset − `g_full` at +120 s, RE2 + RE3 all cases | mean > 0 and Holm p < 0.05 |

- **Holm family:** H8a, H8b and H8c.
- **If H8a is supported,** the paper may say that the difference between the pipelines is carried by the evidence they show, under either prompt.
- **If H8b is supported,** the prompt contributes as well, and the paper says by how much.
- **If H8c is supported,** the generic pipeline's accuracy is, like N-Sigma's, conditional on knowing the onset, and the paper says so wherever it compares the generic pipeline with the baselines.

## Descriptive

None of these enters the family.
- The four cell accuracies and the interaction, per suite and pooled.
- `g_full` at −120 s.
- `g_full` at +120 s set beside N-Sigma, the SimpleRCA-style heuristic and the deployed agent at +120 s (from Amendments 4 and 5).
- **Sensitivity:** the three tests without the six RE3 pilot cases.

## Runs

`scripts/run_amendment8.sh`, in order, resumable:
1. Build `out/{re2,re3}_generic_shift{120,-120}` with `18_generic_contexts.py --onset-shift`. This reads RCAEval data and calls no model.
2. Part A: `21_run_crossed.py`, two conditions on RE3 and RE2 flagged cases, 646 calls.
3. Part B: `19_run_generic.py --condition g_full` on the four shifted folders, 720 calls.

**Analysis:** `python scripts/22_amendment8.py --out out --pilot out/pilot_re3.txt` writes `out/re3/amendment8.md` and `.json`.

## Code

- **`scripts/18_generic_contexts.py`:** new option `--onset-shift`. Its default of 0 leaves the Amendment 7 behaviour unchanged.
- **New files:** `scripts/21_run_crossed.py`, `scripts/22_amendment8.py`, `scripts/run_amendment8.sh`.

**Before this commit:**
- the builder (with and without a shift), the crossed runner and the analysis were run end to end with a mock model on synthetic RCAEval-format data and on the study's real RE2 contexts;
- the crossed runner's `x_gsys_duser` user message was checked to be the `annotated` user message.
