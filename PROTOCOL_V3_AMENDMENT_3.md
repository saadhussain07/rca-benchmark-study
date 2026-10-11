# Amendment 3 to protocol v3: RE3 replication (B) and full anonymisation (C)

**Date:** 2026-10-11. Written and committed **before any run described here**.

**Earlier record:**
- frozen protocol: `939df23`, tag `protocol-v3-frozen-2`
- Amendment 1: `d013b19`, tag `amendment-1`
- Amendment 2: `2d6bf25`, tag `amendment-2`
- Amendment 2 execution log: `a616916`

**What had been seen:** every RE2 result, both confirmatory and exploratory. Of RE3, only the six pilot cases had been run (pre-freeze, deployed model, `annotated`), and the pilot log records that their accuracy was not inspected. The Amendment 2 reruns of the RCAEval baselines are still running, and their results have not been seen.

**Status:** neither part changes a RE2 confirmatory verdict.
- **B** is a replication on a second benchmark suite, specified now. It is reported as a replication, not as part of the original confirmatory families.
- **C** is exploratory and is labelled as such.

## B. Replication on RE3

### B1. Cases

All RE3 cases: 90 in total, 30 per system. The faults are code-level (OB f1–f5, SS f1–f4, TT f1–f4). The number of repetitions per (service, fault) varies from 3 to 4.

Two data properties were seen in `01_inspect.py` before the freeze:

1. **A second batch folder in RE3-TT.** The folder is named `ts-route-service_f3_1` and holds 3 cases. Its cases get the ids `re3tt_ts-route-service_f3_b1r<n>`, with root `ts-route-service` and fault `f3`. They therefore share the f3 cluster.
   - Our earlier parser read this folder as root `ts-route-service_f3` with fault `1`, which is wrong. The fix is in `rcastudy/data.py`. It applies only to folder names of the form `<service>_f<k>_<n>`, and no RE1 or RE2 folder has that form (checked against `data_manifest_RE1/RE2.txt`).
   - RCAEval's `main.py` stops on this folder. Patch P4 (`scripts/rcaeval_patch_a3.py`) gives its result files the same `b<k>r<n>` case names.
2. **Sock Shop services in some RE3-OB metric files.** Some RE3-OB cases list Sock Shop services as well as Online Boutique ones (for example 28 services in `re3ob_adservice_f3_2`). This is noted, not repaired. Every method ranks the same candidate set, so the comparison stays fair. Chance is lower in those cases.

**Primary analysis:** all 90 cases. **Sensitivity:** the 84 cases outside `pilot_re3.txt`.

### B2. Pipeline and runs

**Pipeline.** The detectors, the deployed `ContextBuilder`, the prompt, the NOTE stripping, and the decoy and placebo templates and seeds are all **unchanged**. `03_build_contexts.py --suite re3` writes to `out/re3`.

**Model runs.** Same settings as RE2 (temperature 0.1, max_tokens 3000, one vote):

| Model | Conditions |
|---|---|
| gpt-oss-120b (deployed), gpt-oss-20b, qwen3.8-27b | `annotated`, `stripped`, `decoy`, and `annotated --tag rep2` on NOTE cases |
| deployed model only | `placebo` |

There are no `anon`, vote-check or E1–E3 runs on RE3.

**Comparators.**
- `lr_visible`, `detector_count`, `first_affected`, `simplerca` and `largest_anomaly`, as frozen. `lr_visible` is cross-validated within RE3 (grouped 5-fold over (system, root service, fault)), as on RE2.
- **Secondary:** `lr_visible_re2train`, the same classifier trained on all 270 RE2 cases and applied unchanged to RE3 (`scripts/12_transfer_classifier.py`). It uses no RE3 label.
- **RCAEval baselines:** the five single-source primary methods (`nsigma`, `baro`, `e_diagnosis`, `circa`, `microcause`) on `re3-ob`, `re3-ss` and `re3-tt`, using `main.py --length 20`, a 2-hour limit per method and system, and patches P1–P4. Failed and timed-out cases are scored as chance, as in section 6.
  - **The three multi-source methods are not run.** `mmnsigma`, `mmbaro` and `mmcirca` need `logts.csv` and `tracets_*.csv`. The RE3 release has neither (`data_manifest_RE3.txt` lists 90 `logs.csv` and 73 `traces.csv`, but no `logts.csv` or `tracets_*`). `main.py` reads these files before its per-case try block, so it would stop on the first case. Building them ourselves would be our preprocessing, not RCAEval's.
  - They stay in the 13-comparator family as chance (section 6 rule) and are listed as "not runnable on RE3".
  - The secondary methods are not run either. `tracerca` and `microrank` cannot run through `main.py` (Amendment 2, D4), and `causalrca` timed out on RE2.

### B3. Analysis

1. `06_evaluate.py`, **unchanged**, on `out/re3`. It produces the same tables as for RE2. P3a and P3c are reported as **descriptive** on RE3, decided now: they rest on NOTE cases, and RE3 has few cases in all.
2. `scripts/11_amendment3.py` sets each confirmatory quantity on RE3 beside its RE2 value, using the same statistics. These are cluster bootstrap, cluster permutation, and Holm within each family as in section 7. In the RQ1/RQ2 family, all 13 comparators are included, and a method with no ranking is scored as chance (Amendment 2 log, section 4).

### B4. Replication verdict, fixed now

| Quantity | Rule |
|---|---|
| RQ1/RQ2 comparisons where the RE2 result met its decision rule (Holm p < 0.05) | **replicated** if RE3 has the same sign and Holm p < 0.05 on RE3; **same direction, not significant** if the sign agrees but p does not; **opposite direction** otherwise |
| RQ1/RQ2 comparisons where the RE2 result did not meet its rule | reported as "RE2 not significant", with the RE3 result stated as it is |
| P2 | **replicated** if the RE3 lower 95% bound of (lr_visible − deployed) > −0.05; otherwise inconclusive or contradicted, by section 7 |
| P3b, per model, and decoy vs placebo | as for RQ1/RQ2. The "more than half" rule for the decoy outweighing the evidence is also stated for RE3. |

**Predictions** are those of RE2: P2 non-inferiority; P3b, the decoy is named first more often than under `stripped`; decoy above placebo. RQ1 has no directional prediction.

**Power.** With 90 cases in about 30 clusters, the smallest difference that can reach p < 0.05 is about 14 points without correction (section 7 table). A difference below that is reported as **not detected**, not as absent.

## C. Full anonymisation (exploratory, RE2)

**Why.** RQ4 replaced service names in the structured prompt, but in raw log text it replaced only distinctive names. A stricter detector, defined now, finds an original name in:
- 87 of 90 Sock Shop prompts (mostly the Spring Sleuth prefix `[carts,,,]`);
- 79 of 89 Train Ticket prompts (for example `InsidePaymentServiceImpl`).

So RQ4 could not separate memorisation from name leakage.

**The condition `anon_full`.** It is implemented in `rcastudy/context.py: anonymiser_full`, and it uses the same `service-NN` labels as `anon`.
- **What is replaced:** every spelling of every service name, everywhere in the prompt, raw log text included. The spellings are:
  - the exact name;
  - the name without Train Ticket's `ts-` prefix;
  - each of these with hyphens removed, or replaced by `_` or a space;

  all matched case-insensitively.
  - Spellings of 10 or more characters are also replaced inside longer identifiers.
  - Shorter spellings are replaced as whole tokens, where `_`, `.`, `/` and `[` count as token edges.
- **System names** (Sock Shop, socks, socksdb, weave, hipstershop, Online Boutique, Train Ticket, fudan) become `app`.
- **What is left:** ordinary words such as "order" or "payment" in a log message. These are meaning rather than names, and are named as a residual cue in the paper.

**Check (done before this amendment, on the 245 flagged RE2 cases).**
- `anon_full` prompts contain **0** occurrences under the strict detector (`leak_count_full`). Under the same detector, `anon` prompts have leaks in 87 SS and 79 TT cases.
- Prompt length is 84–102% of `annotated` (median 98%).

**Runs.** `anon_full` on the 245 flagged RE2 cases, for all three models.

**Analysis** (`11_amendment3.py`, part C), per model and system:
- `anon_full` − `annotated`, AC@1, with a 90% cluster-bootstrap interval and a permutation p. The ±0.05 equivalence rule is applied descriptively.
- The number of prompts with any leak, which should be 0.
- The number of answers that name a real (non-anonymised) candidate service.
- For the deployed model only: `anon_full` − `anon`.

The RQ4 confirmatory verdict is unchanged.

## D. A note on RCAEval's MicroCause harness (applies to Amendment 2 and here)

RCAEval's `main.py` passes MicroCause an "SLI" metric, `<root service>_latency`, whenever that column exists, where the root service is taken from the case folder. MicroCause starts its random walk at that metric (`microcause.py`, `frontend = [node_names.index(sli) + 1]`), so its ranking can use ground-truth information. We keep RCAEval's harness unchanged, as for every baseline. MicroCause's numbers are reported with this caveat and are not interpreted as label-free.

## E. Code changes and checks

**Changed files:**
- `rcastudy/data.py`: batch-folder case names (B1).
- `rcastudy/context.py`: `anonymiser_full`, `name_forms`, `leak_count_full`, appended to the file.
- `scripts/04_run_llm.py`: condition `anon_full`.

**New files:**
- `scripts/11_amendment3.py`
- `scripts/12_transfer_classifier.py`
- `scripts/rcaeval_patch_a3.py` (P4)
- `scripts/run_amendment3.sh`
- `scripts/run_rcaeval_re3.sh`

**Checks, done before this commit:**
- On the synthetic RE2 data, the default build gives **byte-identical** `contexts.jsonl`, `ranks_nonllm.json`, `features_visible.csv` and `features_all.csv` to the Amendment-1 code.
- The prompts of every existing condition (`annotated`, `stripped`, `decoy`, `placebo`, `anon`, `shuffled`) have the same sha256 digest before and after the change.
- A synthetic RE3 suite with a batch folder builds 30 unique case ids, with the batch cases in the right cluster. `07_collect_rcaeval.py` maps `b<k>r<n>` result files to them.
- `06_evaluate.py` and `11_amendment3.py` run end to end with a mock model.

## F. Cost and order

**Model calls:**
- RE3: at most 90 flagged cases × (3 models × 3 conditions) + placebo + rep2, which is about 1,000 calls.
- `anon_full`: 735 calls.

At RE2 prices this is a few US dollars, within the Groq spend limit.

**Order:**
1. Commit and tag this amendment.
2. Build RE3 and run the model runs (`run_amendment3.sh`). These can run alongside the Amendment 2 reruns.
3. When the Amendment 2 reruns have finished, apply P4 and run the five RE3 baselines (`run_rcaeval_re3.sh`).
4. Run `07`, `06` on `out/re3`, and `11`.
