# Pre-registered protocol v3: where does the accuracy of an LLM root-cause agent come from? A benchmark study on RCAEval RE2

**Authors:** Muhammad Saad Hussain, Alishba Farrukh

**Status:** DRAFT 2 (2026-10-10), revised after an independent methods and code
review.

**Freeze condition.** The protocol is frozen when all of the following are
committed to a GitHub repository and tagged `protocol-v3-frozen`:
- this file;
- `rcastudy/` and `scripts/`;
- `rcastudy/config.py`, with the unit constants set by the rules in section 8.

The freeze must happen before any RE2 anomalous-window data reaches a detector,
a baseline or a model. After the freeze, any change is made only through a
numbered, dated amendment (`PROTOCOL_V3_AMENDMENT_n.md`) that says what
changed, why, and whether any result had been seen.

**Predecessors:**
- `FGCS_V2_PROTOCOL.md` and amendments 1–4
- `REPLAY_ABLATION_PROTOCOL.md`
- `EXECUTION_STUDY_PROTOCOL.md`

---

## 1. Background

In a live study of our AIOps agent on an Online Boutique deployment (330
cycles, six scenarios), the system detected the fault in 24 of 25 runs.

A pre-registered decomposition of those records found two things:
- Removing the pipeline's interpretive `NOTE` lines reversed 17 of 20 crash verdicts.
- Outside the crash scenario, a logistic regression on the same features matched every model tested.

That study had three weaknesses:
- one system;
- a small fault set that changed while it was being measured;
- no comparison with established root-cause analysis (RCA) methods.

This study evaluates the same agent on the public RCAEval benchmark (Pham et
al., WWW 2025). RE2 has 270 cases from three systems, with metrics, logs and
traces. The study compares the agent with the RCA methods RCAEval ships, with a
SimpleRCA-style heuristic, and with classifiers on the features the agent sees.
It then tests how far interpretive text in the prompt decides the agent's
answer.

**The live finding cannot be replicated directly.** Two things rule it out:
- The NOTE that drove the live result (pod restart) cannot fire on RCAEval, which has no pod-lifecycle data and no pod-kill fault (A6).
- The CPU-saturation NOTE cannot fire either, because RCAEval publishes no resource limits (A5).

Natural NOTEs here are therefore limited to memory pressure and dependency
hints. RQ3 adds a controlled manipulation (decoy and placebo NOTEs), so that the
question can be tested on every case rather than only where a NOTE happens to
fire.

**We do not claim to be first to run LLMs on RCAEval.**
- Pham 2026 (arXiv 2601.21359) reports an LLM agent (RCLAgent) at about 10% top-1, against 68% for PRISM.
- GALA (arXiv 2508.12472) re-ranks BARO's output with an LLM on RE2-OB.
- DecompRCA (arXiv 2609.36686) studies one-call LLM ranking on RE1.
- Luo et al. (arXiv 2610.05009) vary the diagnosis tools given to an agent.
- Fang et al. (arXiv 2510.04711) show that a rule-based heuristic, SimpleRCA, matches or beats state-of-the-art methods on RE2 and RE3.

None of these removes interpretive hints while holding the evidence fixed,
plants a false or neutral hint, or compares the agent with a classifier on the
features the agent sees.

## 2. Research questions and predictions

**RQ0 (descriptive).** How many RE2 cases trigger at least one detector, and how
many carry a NOTE, per system and fault?

**RQ1 (state of the art).** How accurately does the agent localise the
root-cause service, compared with the RCAEval baselines, the SimpleRCA-style
heuristic and the pipeline's own detectors? No directional prediction.

**RQ2 (features).** Does a classifier on the features the agent sees localise
the root cause as accurately as the agent?
- **P2 (non-inferiority, margin 5 points):** the AC@1 of `lr_visible` minus that of the deployed model has a 95% lower bound above −0.05.

**RQ3 (annotations).** How far does interpretive text in the prompt decide the
agent's answer?
- **P3a:** for each model, on cases whose context carries a NOTE, removing the NOTEs changes the top-1 service more often than re-running the same annotated text does.
- **P3b (central):** for each model, a NOTE claiming that a seeded non-root service is the problem (decoy) makes the model name that service first more often than it does under the stripped context. Secondary for the deployed model: more often than under a placebo NOTE that names the same service without a claim.
- **P3c:** on NOTE cases, the three models agree on the top-1 service more often with NOTEs than without them.

**RQ4 (memorisation).** Does replacing service names with neutral labels change
the deployed model's AC@1? No direction is predicted. We report equivalence:
the 90% interval of the difference lies within ±0.05.

**RQ5 (live case study).** The 330-cycle Online Boutique study is reported as
published (JSS submission, with its corrections), as field evidence. No new
confirmatory analysis is run on it.

## 3. Benchmark, cases, candidates

- **Confirmatory set:** all RE2 cases. We expect 270:
  - three systems: Online Boutique (OB), Sock Shop (SS), Train Ticket (TT);
  - six faults: CPU, MEM, DISK, SOCKET, DELAY, LOSS;
  - five root services per system;
  - three repetitions of each.
- **Data copy:** RCAEval's Zenodo release (record 14590730), downloaded with RCAEval's own `download_re*_dataset()`. File hashes are recorded in `data_manifest_*.txt` before the freeze. The RCAEval code is pinned to commit `259ea4167160256a74ad30004aa3d96a998c846e`.
- **Ground truth:** the root-cause service from the case folder name, with `-db` folded into its owner (RCAEval's convention). It is used only for scoring, and never reaches a prompt or a feature.
- **Candidates:** every metric-column prefix of the case, with `-db` folded. This is the set RCAEval scores, and it is used for every method and for chance.
- **Root not among candidates:** the case is kept and logged.
- **Metrics file:** the file RCAEval `main.py` reads: `data.csv` if present, otherwise `simple_metrics.csv`. For RE2 this is `simple_metrics.csv` in every case.
- **RE1** is used for calibration and the pilot (section 8). Six **RE3** cases are used for the pilot only; RE3 is otherwise out of scope.
- **RE1 metrics file (pilot only):** RE1 Sock Shop and Train Ticket store raw cAdvisor names in `data.csv`, with no `_cpu` columns. For those cases the pilot reads `simple_data.csv`.

### Data notes (from `01_inspect.py`, 2026-10-10; normal windows and file structure only)

- **Case count:** RE2 has 270 cases, 90 per system, 15 per system × fault.
- **Stray demo folder:** the Zenodo archive also contains RCAEval's demo sample at `RE2-OB/checkoutservice_cpu/multi-source-data/`. It has no `simple_metrics.csv`, so `main.py` ignores it, and so does our case discovery (only numbered case folders are read). It is not a case.
- **Two short cases:** `re2ob_checkoutservice_cpu_2` and `re2ob_checkoutservice_mem_2` have about 256 metric rows without a timestamp, and only 210 and 284 seconds of data after injection. They are kept (section 9). Every method sees the same shortened window. Rows without a timestamp are dropped by our loader; RCAEval forward-fills them (a difference confined to these two cases).
- **Sampling:** metrics are sampled every 1 s. Each RE2 case has 720 s before injection and 720 s after.
- **Traces:** Sock Shop has none. Train Ticket spans carry no status code (empty), so trace errors cannot fire there; only latency can. Online Boutique status codes are gRPC (0 = OK).
- **Logs:** Online Boutique lines carry a `level`. Sock Shop and Train Ticket lines do not, so error lines are found from the message and error text alone (A9).

## 4. The system under test, and what changed to run it offline

The deployed detectors are ported to offline data in `rcastudy/detectors.py`,
returning dicts in the live schema. The deployed `ContextBuilder` is called
unchanged.

The deployed files are kept byte for byte in `original/`:

| File | sha256 |
|---|---|
| `context_builder.py` | `5f9b023853c5f2d1347168cf2b4ea2ad4e0290667b61de6dd41bd963a0419cef` |
| `runtime_anomaly_agent.py` | `e703654bb0b4bcda313b4b017eee8d3454c2699fc7aa4fdedf8988f79186d63c` |
| `metric_collector.py` | `be5b30ac871ec8fb40242e783b77db065e083beaa5034336db78b98001d07707` |
| `trace_analyser.py` | `2b97d440ed8fd90f79eeb926451d7871f5adb6d016c0998c58593ac6f80e9756` |
| `log_parser.py` | `2b9df9a02ff08f30e9ed0e2ba5f2662ae8c6f22ffc556b9e766ed046d64a0632` |
| `main.py` | `9be324a501f89cc37fb6d46355d71f8f213a2e8f29ac375ee88aec2d7b86f13a` |

`main.py` holds the gate that calls the model only when severity is not NORMAL.

In the live study, Drain3 was active only in S5–S6; S1–S4 used the
keyword-based fallback parser. This port runs Drain3, with the deployed
fallback for services without error lines (A10).

Every difference from the live system is listed below.

### Adaptations forced by offline data (A)

| # | Live system | This study | Reason / consequence |
|---|---|---|---|
| A1 | 60-min fault-free baseline per Isolation Forest | the 10 min before injection (20 points at a 30-s step) | RCAEval's window (`--length 20`), shared by every method |
| A2 | a cycle every 30 s plus processing (~60 s in practice), each scored on the last 10 min | one cycle per case, at injection + 10 min | Every method sees the same 20-min window. The metric and trace look-backs cover only post-injection data; the log look-back covers minutes 5–10 after injection. |
| A3 | Prometheus `rate(...[2m])` with a 30-s step | RCAEval's 1-s samples (already rates) averaged into 30-s bins; no filling | — |
| A4 | CPU in cores; absolute floor 0.005 cores | RCAEval CPU × `CPU_TO_CORES` (section 8), then the same floor | If the unit is ambiguous, the absolute floor is dropped and 1.5 × baseline p95 kept |
| A5 | CPU and memory limits from the manifest | none (`CPU limit unknown`) | The CPU-saturation NOTE cannot fire |
| A6 | pod age; restart trigger below 300 s | none | The restart trigger and restart NOTE cannot fire |
| A7 | error-rate feature (constant 1.0, no Istio) | constant 1.0 | Kept as deployed |
| A8 | Jaeger: up to 100 most recent traces containing the service, as whole traces; error = `error` tag | the same from `traces.csv` (spans up to the cycle time); error = a non-OK gRPC code (1–16) or HTTP ≥ 500 | RCAEval's `statusCode` mixes gRPC and HTTP codes. Sock Shop has no traces; Train Ticket spans have no status code. |
| A9 | Loki: the last 5 min, at most 500 raw lines per service | the same from `logs.csv`; a line is `level`, `message` and `error` joined | The raw Loki line carried the level |
| A10 | Drain3 `seen_patterns` accumulated since process start; fallback to the keyword parser when a service has no error lines | the miner and the seen set primed with the normal window; same fallback | Offline analogue of a long-running process |
| A11 | undeployed-service filter (Online Boutique testbed) | off | Every RCAEval service is deployed |
| A12 | five monitored services, hard-coded | detectors monitor every service with a `_cpu` column; log and trace names are mapped to the longest matching service name | Candidates are defined in section 3 |
| A13 | `AFFECTED SERVICES` ordered by `list(set(...))`, varying with the hash seed | the same code with `PYTHONHASHSEED=0` | Reproducible text; the order stays arbitrary, as deployed |
| A14 | every service had a memory series | a service without `_mem` gets memory 0 in the Isolation Forest, so its CPU is still scored | Without this it would be unscored |

### Changes to the agent (B)

| # | Change | Reason |
|---|---|---|
| B1 | The system prompt lists the case's services, without ports or dependencies | Different systems. This drops the topology the deployed prompt gave (for example, "cartservice … uses Redis"). |
| B2 | Two keys added to the JSON schema: `root_cause_service` and `ranked_root_cause_services` (at most 5) | Avg@k needs a ranking |
| B3 | No conversation history | Each case is an independent incident |
| B4 | One vote per call instead of K = 5 | Cost. Checked in section 5.4. |
| B5 | A `<think>…</think>` block in the message text is removed before the deployed JSON extraction | Some reasoning models put their reasoning in the message text |
| B6 | Everything else verbatim: role text, data-source names, silence paragraph, user-message template, temperature 0.1, `max_tokens` 3000, one schema retry, JSON extraction. Reasoning settings are left at provider defaults, as deployed; `finish_reason` and reasoning tokens are logged. | — |

### Ranking from a response

- **Order:** `ranked_root_cause_services`, then `root_cause_service`, then `affected_services`.
- **Cleaning:** each name is mapped back from anonymised form, folded, and kept only if it is a candidate.
- **Fill:** the remaining candidates follow in the case's shared chance order (one seeded order per case, used by every method).

### Gating

As deployed, the model is called only when at least one detector fires.
Unflagged cases receive the case's chance order and stay in the denominator.
Every score is also reported on flagged cases only.

## 5. Conditions, models and calls

### 5.1 Models (Groq, temperature 0.1)

| Name | Groq ID | Role |
|---|---|---|
| `gpt-oss-120b` | `openai/gpt-oss-120b` | Deployed model |
| `gpt-oss-20b` | `openai/gpt-oss-20b` | Same family, smaller |
| `qwen3.8-27b` | `qwen/qwen3.8-27b` | Different family |

These are the same three models as the live replay study. They are
open-weight models served by one provider. Run dates are logged.

### 5.2 Conditions

| Condition | Text | Models |
|---|---|---|
| `annotated` | the deployed context | all |
| `annotated`, tag `rep2` | the same text again, on NOTE cases (within-case noise for P3a) | all |
| `stripped` | every line beginning `NOTE:` removed (the manipulation of `REPLAY_ABLATION_PROTOCOL.md`, unchanged) | all |
| `decoy` | `stripped` plus one decoy NOTE (5.3) | all |
| `placebo` | `stripped` plus one placebo NOTE naming the same service (5.3) | deployed |
| `anon` | `annotated` with service names replaced by `service-NN` | deployed |

**How `anon` replaces names.**
- Structured text (service lists, summary lines, JSON service fields): every service name, case-insensitive, with pod-hash suffixes.
- Raw log text: only distinctive names (those containing a hyphen or ending in "service"), so that words such as "user" or "payment" in a log message are not rewritten.
- Any name left in the prompt is counted, and the leak rate is reported.

### 5.3 Decoy and placebo NOTEs

- **Decoy service:** drawn uniformly from the candidates other than the root cause (seed `20261010` and the case id). There is no decoy if no such candidate exists.
- **Decoy template:** drawn uniformly from the two deployed NOTE types that can occur on RCAEval. Both are verbatim from the deployed builder:
  - **memory pressure**, about the decoy;
  - **dependency**: "this error text specifically references ‹decoy› — if ‹first affected service› depends on a ‹decoy› service…".
- **Placebo:** `NOTE: ‹decoy› is one of the services deployed in this cluster.`
- **Placement:** each NOTE is its own block (a blank line before it), placed before the `CORRELATED SIGNALS` block or the `TASK` line.
- **Pre-registered harm outcome:** among cases the model gets right under `stripped`, how often the decoy run names the decoy first.

### 5.4 Vote check

- **Cases:** 30 RE2 cases, drawn with a fixed seed (`vote_check_cases.txt`). Only the flagged ones are run.
- **Run:** the deployed model, `annotated`, K = 5.
- **Outcome:** how often the first vote's top-1 equals a unique plurality top-1. Ties count as disagreement.

### 5.5 SimpleRCA-style heuristic (our reimplementation, not the authors' code)

Each alert below adds one to the service's count. Services are ranked by alert
count, with seeded ties.

| Signal | Alert rule |
|---|---|
| Metrics | each metric column whose post-injection mean leaves the pre-injection mean ± 3σ (if σ = 0, any change) |
| Traces | the service's post-injection p95 span duration is at least 3× its pre-injection p95 |
| Logs | the service's post-injection count of lines matching `error\|fail\|exception` is at least 5 and at least 3× the pre-injection count |

**Validity check:** we report our heuristic's RE2 top-1 next to the values Fang
et al. publish (OB 0.47, SS 0.24, TT 0.80). We do not tune it to match them.

### 5.6 Call budget (upper bound; each cell runs only on flagged cases)

| Runs | Calls (at most) |
|---|---|
| 3 models × (annotated + stripped + decoy) × 270 | 2,430 |
| 3 models × rep2, NOTE cases only | 810 |
| Placebo and anon, deployed model | 540 |
| Vote check (30 × 5) | 150 |
| **Total** | **3,930**, plus up to one schema retry per call |

Runs are resumable. A daily-quota stop pauses a run and does not change
anything else.

## 6. Comparators

**The pipeline without the model:**
- `detector_count`: number of signals flagging a service; ties broken by the prompt-visible Isolation Forest ratio (0 if unflagged), then seeded.
- `first_affected`: the order of the prompt's `AFFECTED SERVICES` line, a position-only comparator.
- `largest_anomaly`: Isolation Forest ratio alone.

**Same-feature classifiers.** One row per candidate per case, 13 features
(`VISIBLE_FEATURES`), label = root cause. `-db` siblings are merged into their
owner (OR of flags, max of values, union of hints).

| Name | Model and features | Validation |
|---|---|---|
| `lr_visible` | logistic regression; values the prompt does not show are masked to 0 | 5-fold `GroupKFold`, grouped by (system, root service, fault) |
| `rf_visible` | random forest, same masked features | same |
| `lr_all` | logistic regression, unmasked features | same |
| `lr_visible_loso` | logistic regression, masked features | trained on two systems, tested on the third |

Grouping keeps the three repetitions of a fault on the same side of every
split. Class weights are balanced.

**SimpleRCA-style heuristic:** section 5.5.

**RCAEval baselines.** RCAEval `main.py --length 20` on each RE2 system,
2-hour limit per method and system.
- **Primary:** `nsigma`, `baro`, `circa`, `e_diagnosis`, `microcause`, `mmnsigma`, `mmbaro`, `mmcirca`.
- **Secondary:** `tracerca`, `microrank`, `causalrca`.
- A method that fails or times out keeps its finished cases; the rest are chance, and this is reported.
- Reproduced BARO numbers are checked against RCAEval's published table.
- PRISM is not in this RCAEval version; its published numbers are cited for context only.

## 7. Outcomes and analysis

**Metrics.**
- AC@1, AC@3, AC@5 and Avg@5 at service level, computed with RCAEval's own `Evaluator`.
- Chance Avg@5 over the same candidate sets.
- Reported per system and pooled, on all cases and on flagged cases.

**Confirmatory statistic.** For every paired comparison: the difference in AC@1
between two methods on the same cases. AC@1 is the primary endpoint; Avg@5 is
descriptive.

**Uncertainty and tests.** The three repetitions of a (system, root service,
fault) are not independent, so inference is done over these clusters:
- **Interval:** 95% cluster-bootstrap interval of the paired difference (2,000 resamples, seeded).
- **Test:** two-sided cluster sign-flip permutation (10,000 permutations, seeded).
- **Secondary:** exact McNemar, unclustered, reported alongside.
- **Level:** α = 0.05.

**Families and multiplicity (Holm within each).**

| Family | Comparisons |
|---|---|
| RQ1/RQ2 | deployed model (`annotated`) minus each of `lr_visible`, `detector_count`, `first_affected`, `simplerca`, `largest_anomaly` and the 8 primary RCAEval baselines, pooled over systems (13 tests). Per-system differences are reported with intervals as descriptive. |
| P3a | one test per model (3): change rate (annotated vs stripped) minus change rate (annotated vs rep2), NOTE cases |
| P3b | one test per model (3): decoy named first under `decoy` minus under `stripped` |
| P3c, RQ4, decoy vs placebo | single tests |

**Decision rules, fixed now.**

| Prediction | Supported | Contradicted | Otherwise |
|---|---|---|---|
| P2 | lower 95% bound of (lr_visible − deployed) > −0.05 | upper bound < 0 and p < 0.05 | inconclusive |
| RQ4 | equivalent if the 90% interval of (anon − annotated) lies within ±0.05 | — | — |
| P3a, P3b, P3c | Holm-adjusted p < 0.05 in the predicted direction | — | — |

- For P3b, following the decoy in more than half the decoy cases is reported as the decoy outweighing the evidence for that model.
- A null result is reported as prominently as a supported one.

**Sensitivity (smallest observed difference that can reach p < 0.05).**
Approximate, assuming 30% discordant cases:

| Cases | Correction | Difference needed |
|---|---|---|
| 270 pooled | none | 7 points |
| 270 pooled | Holm over 13 comparators | 10 points |
| 90 per system | none | 14 points |

Smaller differences are reported as not detected, not as no difference.

**Completeness.** The analysis script refuses to report while any model cell
lacks a flagged case, unless the gap is declared. Missing cases are then scored
as chance and listed.

**Exploratory, labelled as such:** per-fault breakdowns, NOTE templates
followed, confidence and escalation, token use and latency, free-text quality,
and `rf_visible`, `lr_all`, `lr_visible_loso` and the secondary baselines in
paired form.

## 8. Calibration, pilot, and what may be seen before the freeze

**Unit rules.** Applied to the normal-window values printed by
`scripts/01_inspect.py` for RE1 and RE2:

| Unit | Rule |
|---|---|
| Sampling | the median metric step must be 1 s, so that our time windows equal `main.py`'s row windows. Otherwise the windows are re-expressed in rows before the freeze. |
| CPU | p95 of per-service medians > 1 and every value ≤ 800 → percent of one core, `CPU_TO_CORES = 0.01`. p95 ≤ 4 → cores, `1.0`. Otherwise `None` (relative floor only). |
| Memory | median > 10⁵ → bytes (as assumed); otherwise MB, `MEM_BYTES_PER_MB = 1` |
| Span duration | median between 10 and 10⁷ → µs (as assumed); above 10⁷ → ns, `TRACE_DURATION_TO_US = 0.001` |

**Unit decisions (applied 2026-10-10, from `inspect_re1/re2/re3.txt`):**

| Unit | Observed in normal windows | Decision |
|---|---|---|
| Sampling | median step 1.0 s in all three suites | time windows equal `main.py`'s row windows |
| CPU | p95 of per-service medians 19.1 (RE1), 5.3 (RE2), 3.2 (RE3); maximum 44.5 | percent of one core, `CPU_TO_CORES = 0.01` |
| Memory | median 3.9 × 10⁷ to 8.0 × 10⁷ | bytes |
| Span duration | median 1,790 (RE2), 2,932 (RE3) | µs |

**Pilot.**
- **Cases:** 15 RE1 cases (one per system × fault, seeded) and 6 RE3 cases (two per system, seeded). The RE1 cases are metrics only; the RE3 cases have logs and traces.
- **Run:** the deployed model, `annotated`, plus a dry run of every condition's text.
- **Purpose:** check parsing, schema keys, `finish_reason`, prompt length (Train Ticket), and log and trace handling.
- **Use of results:** pilot accuracy is not used to change any threshold or prompt. Code defects found in the pilot are fixed before the freeze and listed.

**RE2 before the freeze** is read only by:
- `01_inspect.py`: folder and column names, normal-window ranges, window lengths;
- `00_manifest.py`;
- `02_select_subsets.py`.

No detector, baseline or model touches RE2's anomalous windows before the
freeze. Every pre-freeze run is listed in `prefreeze_log.md` with date and
command.

## 9. Failures and exclusions

No case is excluded.

| Failure | Handling |
|---|---|
| Our pipeline cannot build a case | a stub record keeps it in every denominator, scored as chance for our methods |
| An RCAEval baseline fails on a case | scored as chance for that baseline |
| An API error on one case | written as an error record; the run continues; error cases are retried on the next run. A case still failing after the final rerun is scored as chance and listed. |
| A request too large for the provider | recorded, not retried; reported per model |
| A model becomes unavailable | completed cases are kept, and the gap is reported in an amendment. No model is substituted. |

## 10. Threats known in advance

**Construct.**
- The decoy NOTE is an artificial manipulation. It measures susceptibility to pipeline text, not how often such text is wrong in practice. The placebo separates a claim from the mere mention of a service.
- The natural NOTE types differ from those of the live study (section 1).

**Internal.**
- A1–A14 change the system.
- Two triggers cannot fire (A5, A6).
- The baseline window is 10 min (20 points) instead of 60.
- The prompt loses dependency information (B1).
- One vote per call (B4).
- Trace analysis follows Jaeger's whole-trace semantics, so a delay flags every service on the trace path. This is faithful, but it weakens trace localisation.

**External.**
- Three open-source systems with injected faults.
- Three open-weight models from one provider.

**Contamination.**
- The benchmark systems are public.
- RQ4 tests the name channel only, and some names remain in raw log text (leak rate reported).
- Case identifiers never reach a prompt.

**Statistical.** Cluster-level inference addresses the repeated faults.
Section 7 states the smallest detectable differences.

**Author bias.** The system and the study are ours. The predictions come from
our earlier study and are written down before the data are seen.

## 11. Materials

The materials will be archived on Zenodo with a new DOI, linked from
10.5281/zenodo.23107449:
- `rcastudy/`, `original/` and `scripts/`
- this protocol and its amendments
- `prefreeze_log.md` and the data manifests
- `contexts.jsonl`
- all model responses, with prompt hashes
- all rankings
- `results.json`

RCAEval data are not redistributed.
