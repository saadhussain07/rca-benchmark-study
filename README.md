# rcastudy

Code for the pre-registered benchmark study in `PROTOCOL_V3.md`: the deployed
AIOps agent's detectors, context builder and prompt, run on RCAEval RE2 against
established RCA methods, with NOTE ablation, decoy NOTEs, anonymised names and
same-feature classifiers.

| Step | Script |
|---|---|
| data hashes | `scripts/00_manifest.py` |
| format inspection (normal windows only) | `scripts/01_inspect.py` |
| seeded subsets (RE1 pilot, vote check) | `scripts/02_select_subsets.py` |
| detectors + deployed context + non-LLM rankings | `scripts/03_build_contexts.py` |
| model runs (resumable) | `scripts/04_run_llm.py` |
| same-feature classifiers | `scripts/05_classifiers.py` |
| scoring and pre-registered tests | `scripts/06_evaluate.py` |
| RCAEval baselines | `scripts/run_rcaeval_baselines.sh`, `scripts/07_collect_rcaeval.py` |

`original/` holds the deployed `context_builder.py` and `runtime_anomaly_agent.py`
byte for byte (hashes in the protocol). Start with `RUN_GUIDE.md`.
