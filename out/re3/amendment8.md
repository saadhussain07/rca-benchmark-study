# Amendment 8 analyses (22_amendment8.py)

Deployed model gpt-oss-120b. Part A on the deployed agent's flagged cases that have all four cells; Part B on all cases. Holm over H8a, H8b, H8c.

## Primary

Part A cases: 323

| test | diff [95% CI] | p | p Holm | exact p Holm |
|---|---|---|---|---|
| H8a evidence effect (generic - deployed user message), RE2+RE3 flagged | +0.296 [+0.225, +0.370] | 0.0001 | 0.0003 | 0.0000 |
| H8b prompt effect (generic - deployed system prompt), RE2+RE3 flagged | +0.051 [+0.020, +0.083] | 0.0028 | 0.0028 | 0.0025 |
| H8c generic g_full: given onset - onset +120 s, RE2+RE3 | +0.583 [+0.510, +0.653] | 0.0001 | 0.0003 | 0.0000 |

- **H8a**: supported
- **H8b**: generic prompt better
- **H8c**: supported

## Sensitivity: without 6 RE3 pilot cases

Part A cases: 318

| test | diff [95% CI] | p | p Holm | exact p Holm |
|---|---|---|---|---|
| H8a evidence effect (generic - deployed user message), RE2+RE3 flagged | +0.294 [+0.224, +0.368] | 0.0001 | 0.0003 | 0.0000 |
| H8b prompt effect (generic - deployed system prompt), RE2+RE3 flagged | +0.052 [+0.022, +0.084] | 0.0017 | 0.0017 | 0.0018 |
| H8c generic g_full: given onset - onset +120 s, RE2+RE3 | +0.582 [+0.508, +0.651] | 0.0001 | 0.0003 | 0.0000 |

- **H8a**: supported
- **H8b**: generic prompt better
- **H8c**: supported

## Descriptive

### 2x2 cell accuracy (AC@1 on flagged cases with all four cells)

| suite | n | E_d P_d (annotated) | E_d P_g | E_g P_d | E_g P_g (g_full) | evidence effect | prompt effect | interaction |
|---|---|---|---|---|---|---|---|---|
| re2 | 245 | 0.469 | 0.547 | 0.808 | 0.865 | +0.329 [+0.254, +0.404] | +0.067 [+0.032, +0.102] | -0.020 [-0.090, +0.054] |
| re3 | 78 | 0.692 | 0.692 | 0.885 | 0.885 | +0.192 [+0.014, +0.378] | +0.000 [-0.061, +0.064] | +0.000 [-0.114, +0.130] |
| both | 323 | 0.523 | 0.582 | 0.827 | 0.870 | +0.296 [+0.225, +0.370] | +0.051 [+0.020, +0.083] | -0.015 [-0.075, +0.047] |

### Generic pipeline under onset shifts (g_full, all cases)

| suite | given onset | -120 s | +120 s |
|---|---|---|---|
| re2 | 0.870 | 0.852 | 0.267 |
| re3 | 0.889 | 0.711 | 0.367 |

g_full given onset minus onset -120 s (RE2+RE3): +0.058 [+0.014, +0.108], p 0.0217

g_full given onset minus onset +120 s (RE2+RE3): +0.583 [+0.510, +0.653], p 0.0001

### Checks

- re2 x_dsys_guser: 245/245 flagged cases run; answers with no candidate named: 0
- re2 x_gsys_duser: 245/245 flagged cases run; answers with no candidate named: 0
- re3 x_dsys_guser: 78/78 flagged cases run; answers with no candidate named: 0
- re3 x_gsys_duser: 78/78 flagged cases run; answers with no candidate named: 0
- re2g+120: 270 cases, build failures 0
- re2g-120: 270 cases, build failures 0
- re3g+120: 90 cases, build failures 0
- re3g-120: 90 cases, build failures 0
