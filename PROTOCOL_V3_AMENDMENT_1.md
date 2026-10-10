# Amendment 1 to protocol v3

**Date:** 2026-10-10, written after the confirmatory results were computed (commit of the frozen protocol: `939df23`, tag `protocol-v3-frozen-2`).
**Status:** results had been seen. Nothing below changes a confirmatory analysis, a hypothesis, a decision rule or a frozen file's behaviour. It adds (1) a more exact version of the pre-registered permutation test, reported alongside the pre-registered one, and (2) exploratory analyses that the paper will label as post hoc.
**Trigger:** an independent review of the analysis (`review2/REVIEW_REPORT.md`), which reproduced every number and raised the points addressed here.

## A1. Exact permutation p-values

The pre-registered test is a two-sided cluster sign-flip permutation, estimated with 10,000 seeded random flips (section 7). When few clusters have a non-zero paired difference, the full set of sign patterns is small enough to enumerate. The exact p-value is the limit of the pre-registered estimator.

`10_exploratory.py` reports both values for every confirmatory test:
- **Verdicts stay those of the pre-registered Monte Carlo estimate.**
- Where the two values fall on different sides of 0.05 after Holm correction, the result is reported as **borderline**, with both values given.
- This applies to one test: P3a for qwen3.8-27b. Monte Carlo gives p = 0.0177 (Holm 0.053); the exact value is 0.0156 over 7 non-zero clusters (Holm 0.047).

## A2. Reporting of verdicts

`06_evaluate.py` prints p-values but not verdicts. `10_exploratory.py`, section 1, states each verdict as section 7's rules define it:
- for P2: whether the classifier is also superior;
- for P3b: whether the decoy outweighs the evidence (the "more than half" rule).

The Holm family for RQ1/RQ2 is recomputed over the 13 pre-registered comparators once the RCAEval baselines are available, as section 7 already specifies.

## A3. Exploratory analyses (post hoc; labelled as such in the paper)

### Analyses of existing data (no new model calls)

| # | Analysis |
|---|---|
| X1 | Paired differences on flagged cases only, and against the leave-one-system-out classifier |
| X2 | Position in the AFFECTED SERVICES line: how often top-1 equals the first-listed service, and accuracy when the root is listed first vs not |
| X3 | Run-to-run variation on byte-identical prompts (no-NOTE cases, annotated vs stripped), per system |
| X4 | Always-on alarms: the most often flagged non-root service per system, and how often each model names it first |
| X5 | Decoy detail by system and template, and the decoy's presence in the top 5 under decoy, placebo and stripped |
| X6 | Anonymisation by system and by leak status |
| X7 | What the natural NOTE lines pointed at |
| X8 | SimpleRCA diagnostic (`09_simplerca_diag.py`): ties at the top, root vs best-other alert counts, alert sources for the root, expected accuracy with ties broken at random. This explains the gap to the values Fang et al. publish. |

### New runs

All new runs use the deployed model (gpt-oss-120b), on the flagged cases. They are specified here before any of them is run. Together they add about 1,225 calls.

**E1. Repeat runs.** Two more runs of the `annotated` condition (tags `repA`, `repB`). Together with the main run, this gives three runs, from which we report:
- the run-to-run SD of AC@1;
- the AC@1 of the unique-plurality answer.

**E2. Order randomisation.** The `shuffled` condition, with order seeds 1 and 2 (tags `order1`, `order2`). The service order in the AFFECTED SERVICES summary line, and in the user message's affected-services list, is permuted with a seed derived from the case id. All other text is unchanged. Each shuffled run is compared with the frozen order.

**E3. Baseline-aware log alarms.** Contexts are rebuilt with `03_build_contexts.py --chronic-filter` into `out/re2_chronic`, and the deployed model is run on the `annotated` condition. The rule is fixed now, before the run:
- An error-count alarm fires only if the service's error lines in the 5-minute look-back exceed both the deployed threshold (10) **and** twice the count in the 5 minutes before injection.
- A dependency hint is dropped if the same hint already appeared in that pre-injection window.
- Everything else is as frozen.

We report AC@1 with and without the filter, for the deployed model and for `detector_count`.

## A4. Code changes

`03_build_contexts.py` (flag `--chronic-filter`), `rcastudy/detectors.py` (argument `chronic_filter`, default `False`) and `04_run_llm.py` (condition `shuffled`, flag `--order-seed`) gain options. Their defaults leave the frozen behaviour unchanged. The check: a default build on the synthetic test data gives byte-identical `contexts.jsonl`, `ranks_nonllm.json` and `features_visible.csv` to the frozen code.

New scripts: `09_simplerca_diag.py` and `10_exploratory.py`. `06_evaluate.py` is unchanged.

## A5. Corrections to interpretation (for the paper, not the protocol)

- The Train Ticket always-on alarm (`ts-inside-payment-service`) attracts the models much less than Sock Shop's `queue-master`. It is named first by gpt-oss-120b in 18 of 89 cases, gpt-oss-20b in 28 and qwen in 41, compared with 69, 70 and 82 of 90 for `queue-master`.
- **Anonymisation.** No change is detected overall, and equivalence is not shown. The effect differs by system: +14 points in Sock Shop, where 86 of 90 prompts still leak a name, and −6 points in Train Ticket. On fully anonymised prompts the difference is −1.3 points [−7.5, +5.1].
- **Decoy vs placebo.** The claim, not the mention, drives top-1. The mention alone still lifts the decoy into the top 5 (76 → 172 of 245 cases).
- **Comparators.** `lr_visible` is a supervised reference. The label-free comparison is `detector_count`; the strictest supervised one is leave-one-system-out.
