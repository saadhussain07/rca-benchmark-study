# Pre-freeze log

Every run before the `protocol-v3-frozen` tag, with date and command.
RE2 may appear here only with `01_inspect.py`, `00_manifest.py` or
`02_select_subsets.py`.

| Date (PKT) | Who | Command | Suite | Notes |
|---|---|---|---|---|
| 2026-10-10 | Claude | `tests/make_synthetic.py` + scripts 01–06 on synthetic data | synthetic | pipeline test, no RCAEval data |
| 2026-10-10 | Saad (EC2) | `tests/make_synthetic.py` + scripts 03, 05, 06 on synthetic data | synthetic | environment self-test; output identical to Claude's |
| 2026-10-10 | Saad (EC2) | download RE1, RE2, RE3 (RCAEval Zenodo 14590730; RE3 resumed with wget) | — | RE1 375, RE2 270, RE3 90 cases |
| 2026-10-10 | Saad (EC2) | `00_manifest.py` on data/RE1, data/RE2, data/RE3 | all | data_manifest_RE1/2/3.txt |
| 2026-10-10 | Saad (EC2) | `01_inspect.py --suite re1 / re2 / re3` | all | normal windows and file structure only; first RE2 run crashed on rows without timestamps, fixed and rerun |
| 2026-10-10 | Saad (EC2) | `02_select_subsets.py` | RE1, RE2, RE3 | pilot_re1 (15), pilot_re3 (6), vote_check_cases (30) |
| 2026-10-10 | Claude | set CPU_TO_CORES = 0.01 (section 8 rule); trace error rule = gRPC 1-16 or HTTP >= 500; RE1 pilot reads simple_data.csv when data.csv has no _cpu columns | — | decisions from inspect files; no anomalous-window data seen |
