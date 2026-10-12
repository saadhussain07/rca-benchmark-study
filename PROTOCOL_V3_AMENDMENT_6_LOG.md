# Amendment 6 execution log

- 2026-10-12 14:51-15:46 UTC: run_amendment6.sh, all 1,036 runs completed; analysis by 17_amendment6.py.
- Manipulation check `nolog`: 3 of 78 RE3 prompts (re3ob_adservice_f5_1/2/3) kept one mined log template ("failed to retrieve ads") in the summary's LOG ANOMALIES reason line; strip_log_text did not treat that line as part of the log section. Sample error lines and the anomalous-logs JSON fields were removed in these cases as elsewhere. The code was not changed after the runs.
- Sensitivity without the three cases: H6a +0.253 (p_H 0.0093), H6b +0.238 (p_H 0.0044), H6c-1 +0.011 (p_H 1.0), H6c-2 +0.207 (p_H 0.0414). No verdict changes.
- `permuted`: skeleton check passed in every prompt; no answer failed to map back.
