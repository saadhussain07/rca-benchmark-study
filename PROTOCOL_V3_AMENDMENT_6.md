# Amendment 6 to protocol v3: does the model read the log text, and what do service names give it?

**Date:** 2026-10-12. Written and committed **before any run described here**.

**Earlier record:** frozen protocol `939df23` (tag `protocol-v3-frozen-2`); Amendments 1–5 (tags `amendment-1` … `amendment-5`); review numbers (`scripts/16_review_numbers.py`, `out/review_numbers.md`, no model calls).

**What had been seen:**
- every RE2 and RE3 result reported so far, including Amendments 1–5;
- the review numbers. Of these, the one that bears on this amendment: in 37 of the 78 flagged RE3 cases the log samples in the prompt name the root service (OB 18, SS 19, TT 0), and under `anon_full` its label stays in all 37.

**What had not been seen:** any result of the two conditions defined here (`nolog`, `permuted`), on any suite or model, and the second `annotated` run on RE3 (`a6rep`).

**Status:** a new pre-registered test of an explanation the paper currently states only as a hypothesis. It does not change any earlier verdict, condition, statistic or file behaviour.

## Why

On RE3 the deployed model (AC@1 0.600) is above the pipeline's detector count (0.378) and the classifier on the features the prompt shows (0.422), although not significantly after Holm. The paper's working explanation is that the model reads raw log text that the detectors do not turn into numbers. No condition so far tests this:
- `stripped`, `decoy` and `placebo` change only the interpretive NOTEs;
- `anon_full` lowered RE3 accuracy by 0.211 (H5b not supported), but it keeps a consistent name→label link, so it removes what names *mean*, not which service a log line refers to. It cannot tell evidence from prior knowledge.

Two conditions answer these questions directly.

## Conditions (text only; the detector output is the same as `annotated`)

**`nolog`.** All raw log text is removed from the prompt; the log detector's output stays.
- Removed:
  - every `Sample error log: "…"` line of the summary;
  - the template text in `New log pattern detected: <template>` (the reason itself stays, as `New log pattern detected`);
  - in the anomalous-logs JSON, `sample_error_log` (set to null) and the template text of `top_pattern` (only its count stays).
- Kept:
  - which services the log detector flags;
  - their error and log counts;
  - the other reason strings;
  - the dependency keywords and the dependency NOTE built from them;
  - everything that does not come from logs.
- Implemented in `rcastudy/context.py: strip_log_text`.
- **Manipulation check**, stored per call: the number of the context's raw log strings (sample lines, templates, new patterns of 8 or more characters) that remain in the prompt. It must be 0.

**`permuted`.** The real service names are deranged among the candidate services, with a seed derived from the case id, so that no service keeps its own name.
- **Where.** Every spelling of every name is rewritten everywhere, raw log text included. The spellings and the matching rules are those of `anon_full`: the exact name, the name without `ts-`, and hyphen, underscore, space and no-separator variants. Spellings of 10 or more characters also match inside identifiers.
- **How.** Each spelling becomes the same spelling of the target name, and its case pattern is kept:
  - `InsidePaymentServiceImpl` → `SecurityServiceImpl`;
  - `[Inside Payment Service]` → `[Security Service]`.
- **Siblings.** A non-candidate name that extends a candidate (`carts-db`) follows that candidate.
- **System names** are kept.
- **What this preserves and removes.** Names still look like names, and a log line still points at the same (renamed) service as the metrics. Only the correspondence between a name and the service it really is, is broken.
- **Scoring.** The model's answers are mapped back through the permutation before scoring (`resolve_parsed`). A name that maps to no service is dropped, as the ranking rule already does for non-candidates.
- Implemented in `rcastudy/context.py: permuter`.
- **Manipulation check**, stored per call: with every spelling of every name removed, the permuted prompt must equal the original prompt (case-insensitive). The number of failures must be 0.

**`a6rep`.** A second run of `annotated` on RE3 for the deployed model. It is descriptive and gives the run-to-run variation on RE3.

## Hypotheses and decision rules

Deployed model `gpt-oss-120b`, one vote, settings as frozen. AC@1 is computed on all cases, with unflagged cases ranked by chance (section 7). Clusters are (system, root service, fault). The cluster bootstrap uses 2,000 resamples and the cluster sign-flip permutation test 10,000, both seeded. The exact p (Amendment 1) is reported alongside, and a disagreement between the two Holm values about 0.05 is called borderline.

| # | Hypothesis | Statistic | Supported if |
|---|---|---|---|
| H6a | On RE3, raw log text raises the deployed model's accuracy. | `annotated` − `nolog`, RE3, paired | mean > 0 and Holm p < 0.05 |
| H6b | Raw log text matters more on RE3 than on RE2. | (`annotated` − `nolog`) per case; mean on RE3 minus mean on RE2. Clusters are independent between suites: the bootstrap resamples clusters within each suite, and the test permutes suite labels among clusters (10,000, seeded). | mean > 0 and Holm p < 0.05 |
| H6c-1 | Wrong but name-like names differ from neutral labels. | `permuted` − `anon_full`, RE3, paired | Holm p < 0.05, two-sided; the sign is the finding |
| H6c-2 | Names that refer to the right service differ from names that refer to the wrong one. | `annotated` − `permuted`, RE3, paired | Holm p < 0.05, two-sided; the sign is the finding |

- **Holm family:** H6a, H6b, H6c-1 and H6c-2 (four tests).
- **H6a and H6b are directional predictions.** A significant result in the other direction is reported as contradicting them.
- **H6c-1 and H6c-2 are two-sided questions.** Their outcomes are read as follows, fixed now:
  - H6c-2 > 0: the correct name→service correspondence helps. This covers prior knowledge of these systems and the agreement of names with other words in the prompt.
  - H6c-1 < 0: wrong meanings actively mislead the model, so it uses what names mean.
  - H6c-1 > 0: name-like tokens help even when their meaning is wrong.
  - A null result on either is reported as "not detected".
- **Interpretation of H6a.** If H6a is supported, the paper may state that on RE3 the model uses raw log text. If it is not, the paper states that this explanation was tested and not supported.

## Secondary and descriptive analyses

None of these enters a Holm family. All are reported.
1. The same three paired differences for `gpt-oss-20b` and `qwen3.8-27b` on RE3, and for the deployed model on RE2.
2. `nolog` − detector count, beside `annotated` − detector count, on both suites. This asks whether the model's position relative to its own detectors changes without log text.
3. RE3 flagged cases split by whether the log samples name the root (the 37 / 41 split above): AC@1 under each condition, and `annotated` − `nolog` within each stratum. The prediction, descriptive only, is that the `nolog` drop is concentrated where the logs name the root.
4. The pull of the root's real name under `permuted`: how often the model's top-1 is the wrong service that is now *shown* under the root's real name, against the count expected at chance.
5. Run-to-run on RE3 (`a6rep` against the main `annotated` run): changed top-1 among flagged cases, and the AC@1 difference.
6. Sensitivity: the four tests on the 84 RE3 cases outside `pilot_re3.txt`, with RE2 unchanged.
7. The manipulation checks, per suite, model and condition.

**Power.** With about 30 RE3 clusters, the smallest detectable paired difference is about 14 points (section 7). A null result on H6a or H6c is therefore weak evidence of no effect, and the paper says so.

## Runs

`scripts/run_amendment6.sh` uses Groq and the existing contexts. It rebuilds nothing and does not use RCAEval. It runs in priority order and is resumable:

| # | Suite | Model | Condition | Calls (flagged cases) |
|---|---|---|---|---|
| 1 | RE3 | deployed | `nolog`, `permuted` | 2 × 78 |
| 2 | RE2 | deployed | `nolog` | 245 |
| 3 | RE3 | `gpt-oss-20b`, `qwen3.8-27b` | `nolog`, `permuted` | 4 × 78 |
| 4 | RE2 | deployed | `permuted` | 245 |
| 5 | RE3 | deployed | `annotated`, tag `a6rep` | 78 |

In all, about 1,036 calls. If the provider's spending cap stops the run, it resumes from where it stopped. The confirmatory analysis needs only steps 1 and 2.

**Analysis:** `python scripts/17_amendment6.py --out out --pilot out/pilot_re3.txt` writes `out/re3/amendment6.md` and `.json`.

## Code

- **`rcastudy/context.py`**, appended:
  - `strip_log_text`, `log_text_items`, `log_text_residue`;
  - `derangement`, `permuter`, `resolve_parsed`.
- **`scripts/04_run_llm.py`:**
  - two new choices, `nolog` and `permuted`, in `messages_for`;
  - for `permuted`, answers are mapped back with `resolve_parsed` before the frozen `ranking` rule.
  - Every other condition takes the same code path as before.
- **New files:** `scripts/17_amendment6.py`, `scripts/run_amendment6.sh`.

**Checks done before this commit**, on the 245 flagged RE2 contexts of the study (real prompts):
- every existing condition (`annotated`, `stripped`, `decoy`, `placebo`, `anon`, `anon_full`, `shuffled`) produces byte-identical prompts and leak counts with the old and new `04_run_llm.py`;
- `nolog`:
  - leaves 0 raw log strings in all 245 prompts (189 of them contain log text);
  - no summary line needed the fallback rewrite;
- `permuted`:
  - has no fixed point;
  - passes the skeleton check in all 245 prompts;
  - maps every shown name, in four spellings, back to the right service (0 errors in 31,364 lookups);
- the runner and `17_amendment6.py` were run end to end with a mock model on these contexts;
- the between-suite test was checked on simulated data:
  - no shift gives p = 1;
  - a 0.25 shift gives p < 0.001 with an interval around 0.25.

RE3 contexts were not opened for these checks.
