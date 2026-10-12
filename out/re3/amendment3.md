# Amendment 3 analyses (11_amendment3.py)

B is the pre-specified RE3 replication. C is exploratory. Neither changes a RE2 confirmatory verdict.

## B. RE3 replication

| system | cases | flagged | with NOTE | pilot cases |
|---|---|---|---|---|
| ob | 30 | 30 | 22 | 2 |
| ss | 30 | 27 | 1 | 2 |
| tt | 30 | 21 | 0 | 2 |
| all | 90 | 78 | 23 | 6 |

RE3 estimates use all 90 cases (primary) and, in the last column, the 84 cases outside the pilot (sensitivity). Methods without a ranking on a case are scored as chance. p is the cluster permutation p; Holm within each family as in the protocol.

| quantity | RE2 | RE3 | RE3 p (Holm) | RE3 ranked cases | verdict | RE3 without pilot |
|---|---|---|---|---|---|---|
| RQ1/RQ2 deployed - lr_visible | -0.185 [-0.256, -0.119] | +0.178 [-0.040, +0.412] | 0.1593 (0.3186) | 90 | opposite direction | +0.190 [-0.023, +0.419] |
| RQ1/RQ2 deployed - detector_count | -0.156 [-0.219, -0.093] | +0.222 [+0.049, +0.414] | 0.0353 (0.1412) | 90 | opposite direction | +0.226 [+0.046, +0.417] |
| RQ1/RQ2 deployed - first_affected | +0.033 [-0.044, +0.119] | +0.333 [+0.149, +0.529] | 0.0037 (0.0222) | 90 | RE2 not significant; RE3 significant, same sign | +0.345 [+0.151, +0.551] |
| RQ1/RQ2 deployed - simplerca | -0.370 [-0.463, -0.274] | -0.233 [-0.376, -0.082] | 0.0105 (0.0525) | 90 | same direction, not significant | -0.214 [-0.360, -0.064] |
| RQ1/RQ2 deployed - largest_anomaly | +0.248 [+0.167, +0.330] | +0.367 [+0.163, +0.563] | 0.0029 (0.0203) | 90 | replicated | +0.369 [+0.158, +0.573] |
| RQ1/RQ2 deployed - rcaeval:nsigma | -0.359 [-0.441, -0.274] | -0.133 [-0.273, +0.000] | 0.0945 (0.2835) | 90 | same direction, not significant | -0.107 [-0.241, +0.022] |
| RQ1/RQ2 deployed - rcaeval:baro | +0.148 [+0.044, +0.256] | +0.344 [+0.160, +0.547] | 0.0023 (0.0184) | 90 | replicated | +0.357 [+0.176, +0.560] |
| RQ1/RQ2 deployed - rcaeval:circa | -0.048 [-0.163, +0.067] | +0.156 [-0.078, +0.371] | 0.2243 (0.3186) | 61 | RE2 not significant; RE3 not significant | +0.167 [-0.064, +0.378] |
| RQ1/RQ2 deployed - rcaeval:e_diagnosis | +0.378 [+0.281, +0.478] | +0.578 [+0.416, +0.736] | 0.0001 (0.0013) | 90 | replicated | +0.583 [+0.412, +0.747] |
| RQ1/RQ2 deployed - rcaeval:microcause | +0.370 [+0.285, +0.459] | +0.389 [+0.211, +0.554] | 0.0005 (0.0045) | 44 | replicated | +0.405 [+0.224, +0.575] |
| RQ1/RQ2 deployed - rcaeval:mmnsigma | -0.363 [-0.448, -0.274] | +0.522 [+0.362, +0.682] | 0.0001 (0.0013) | 0 | opposite direction (significant) | +0.536 [+0.378, +0.692] |
| RQ1/RQ2 deployed - rcaeval:mmbaro | +0.133 [+0.030, +0.237] | +0.522 [+0.362, +0.682] | 0.0001 (0.0013) | 0 | RE2 not significant; RE3 significant, same sign | +0.536 [+0.378, +0.692] |
| RQ1/RQ2 deployed - rcaeval:mmcirca | +0.048 [-0.056, +0.156] | +0.522 [+0.362, +0.682] | 0.0001 (0.0013) | 0 | RE2 not significant; RE3 significant, same sign | +0.536 [+0.378, +0.692] |
| P2 lr_visible - deployed | +0.185 [+0.119, +0.256] | -0.178 [-0.412, +0.040]; inconclusive | 0.1593 |  | not replicated (inconclusive) | -0.190 [-0.419, +0.023] |
| P2 lr_visible_re2train - deployed | - | -0.133 [-0.352, +0.070]; inconclusive | 0.2693 |  | no RE2 counterpart | -0.155 [-0.370, +0.042] |
| P3b gpt-oss-120b | +0.302 [+0.237, +0.367] | +0.141 [+0.039, +0.259]; decoy first 15/78 | 0.0411 (0.0411) |  | replicated | +0.123 [+0.029, +0.231] |
| P3b gpt-oss-20b | +0.376 [+0.313, +0.442] | +0.295 [+0.165, +0.434]; decoy first 28/78 | 0.0002 (0.0006) |  | replicated | +0.288 [+0.162, +0.430] |
| P3b qwen3.8-27b | +0.176 [+0.128, +0.229] | +0.115 [+0.040, +0.195]; decoy first 12/78 | 0.0144 (0.0288) |  | replicated | +0.110 [+0.041, +0.187] |
| decoy vs placebo (deployed) | +0.269 [+0.210, +0.331] | +0.128 [+0.027, +0.241] | 0.0495 |  | replicated | +0.123 [+0.029, +0.231] |

## C. Full anonymisation on RE2 (exploratory)

anon_full minus annotated, AC@1, 90% cluster-bootstrap interval; equivalence margin +-0.05 (the RQ4 rule, applied here descriptively).

| model | system | n | AC@1 annotated | AC@1 anon_full | diff [90% CI] | p perm | within +-0.05 | prompts with any leak | answers naming a real service |
|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-120b | ob | 66 | 0.879 | 0.909 | +0.030 [-0.045, +0.098] | 0.7535 | False | 0/66 | 0/66 |
| gpt-oss-120b | ss | 90 | 0.167 | 0.244 | +0.078 [+0.000, +0.167] | 0.2407 | False | 0/90 | 0/90 |
| gpt-oss-120b | tt | 89 | 0.472 | 0.461 | -0.011 [-0.067, +0.044] | 1.0000 | False | 0/89 | 0/89 |
| gpt-oss-120b | all | 245 | 0.469 | 0.502 | +0.033 [-0.008, +0.074] | 0.2912 | False | 0/245 | 0/245 |
| gpt-oss-20b | ob | 66 | 0.879 | 0.894 | +0.015 [-0.043, +0.071] | 1.0000 | False | 0/66 | 0/66 |
| gpt-oss-20b | ss | 90 | 0.167 | 0.356 | +0.189 [+0.100, +0.300] | 0.0059 | False | 0/90 | 0/90 |
| gpt-oss-20b | tt | 89 | 0.472 | 0.528 | +0.056 [+0.011, +0.112] | 0.1844 | False | 0/89 | 0/89 |
| gpt-oss-20b | all | 245 | 0.469 | 0.563 | +0.094 [+0.049, +0.139] | 0.0019 | False | 0/245 | 0/245 |
| qwen3.8-27b | ob | 66 | 0.894 | 0.924 | +0.030 [-0.046, +0.123] | 0.8755 | False | 0/66 | 0/66 |
| qwen3.8-27b | ss | 90 | 0.067 | 0.089 | +0.022 [+0.000, +0.044] | 0.4991 | True | 0/90 | 0/90 |
| qwen3.8-27b | tt | 89 | 0.416 | 0.528 | +0.112 [+0.044, +0.191] | 0.0411 | False | 0/89 | 0/89 |
| qwen3.8-27b | all | 245 | 0.416 | 0.473 | +0.057 [+0.021, +0.098] | 0.0232 | False | 0/245 | 0/245 |

gpt-oss-120b: anon_full minus anon (original RQ4 condition), all systems: -0.012 [-0.050, +0.025] (90% CI), p perm 0.7363, n 245.
