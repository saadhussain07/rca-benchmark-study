# Review numbers (16_review_numbers.py)

Computed from existing outputs; no model call, no baseline run. Exploratory unless a section says otherwise.

## 1. RE3 replication: exact p and the non-pilot sensitivity

MC p = the pre-registered 10,000-flip permutation p; exact = full enumeration (<= 22 non-zero clusters) or 10^6 flips. Holm within the same families as Amendment 3 (13 RQ1/RQ2 tests; 3 P3b tests; decoy vs placebo single). 'borderline' = the two Holm values fall on different sides of 0.05 (Amendment 1 rule).

### all 90 cases

| quantity | diff [95% CI] | MC p | MC p Holm | exact p | exact p Holm | non-zero clusters | note |
|---|---|---|---|---|---|---|---|
| RQ1/RQ2 deployed - lr_visible | +0.178 [-0.040, +0.412] | 0.1593 | 0.3186 | 0.1552 | 0.3105 | 17 |  |
| RQ1/RQ2 deployed - detector_count | +0.222 [+0.049, +0.414] | 0.0353 | 0.1412 | 0.0334 | 0.1335 | 16 |  |
| RQ1/RQ2 deployed - first_affected | +0.333 [+0.149, +0.529] | 0.0037 | 0.0222 | 0.0037 | 0.0220 | 13 |  |
| RQ1/RQ2 deployed - simplerca | -0.233 [-0.376, -0.082] | 0.0105 | 0.0525 | 0.0110 | 0.0549 | 14 |  |
| RQ1/RQ2 deployed - largest_anomaly | +0.367 [+0.163, +0.563] | 0.0029 | 0.0203 | 0.0025 | 0.0178 | 23 |  |
| RQ1/RQ2 deployed - rcaeval:nsigma | -0.133 [-0.273, +0.000] | 0.0945 | 0.2835 | 0.0968 | 0.2905 | 16 |  |
| RQ1/RQ2 deployed - rcaeval:baro | +0.344 [+0.160, +0.547] | 0.0023 | 0.0184 | 0.0019 | 0.0151 | 17 |  |
| RQ1/RQ2 deployed - rcaeval:circa | +0.156 [-0.078, +0.371] | 0.2243 | 0.3186 | 0.2237 | 0.3105 | 21 |  |
| RQ1/RQ2 deployed - rcaeval:e_diagnosis | +0.578 [+0.416, +0.736] | 0.0001 | 0.0013 | 0.0000 | 0.0000 | 21 |  |
| RQ1/RQ2 deployed - rcaeval:microcause | +0.389 [+0.211, +0.554] | 0.0005 | 0.0045 | 0.0005 | 0.0048 | 19 |  |
| RQ1/RQ2 deployed - rcaeval:mmnsigma | +0.522 [+0.362, +0.682] | 0.0001 | 0.0013 | 0.0000 | 0.0001 | 22 |  |
| RQ1/RQ2 deployed - rcaeval:mmbaro | +0.522 [+0.362, +0.682] | 0.0001 | 0.0013 | 0.0000 | 0.0001 | 22 |  |
| RQ1/RQ2 deployed - rcaeval:mmcirca | +0.522 [+0.362, +0.682] | 0.0001 | 0.0013 | 0.0000 | 0.0001 | 22 |  |
| P2 lr_visible - deployed | -0.178 [-0.412, +0.040] | 0.1593 | - | 0.1552 | - | 17 | inconclusive |
| P2 lr_visible_re2train - deployed | -0.133 [-0.352, +0.070] | 0.2693 | - | 0.2637 | - | 12 | inconclusive |
| P3b gpt-oss-120b | +0.141 [+0.039, +0.259] | 0.0411 | 0.0411 | 0.0391 | 0.0391 | 8 |  |
| P3b gpt-oss-20b | +0.295 [+0.165, +0.434] | 0.0002 | 0.0006 | 0.0002 | 0.0007 | 13 |  |
| P3b qwen3.8-27b | +0.115 [+0.040, +0.195] | 0.0144 | 0.0288 | 0.0156 | 0.0312 | 7 |  |
| decoy vs placebo (deployed) | +0.128 [+0.027, +0.241] | 0.0495 | 0.0495 | 0.0469 | 0.0469 | 8 |  |

### 84 non-pilot cases

| quantity | diff [95% CI] | MC p | MC p Holm | exact p | exact p Holm | non-zero clusters | note |
|---|---|---|---|---|---|---|---|
| RQ1/RQ2 deployed - lr_visible | +0.190 [-0.023, +0.419] | 0.1250 | 0.3750 | 0.1190 | 0.3570 | 17 |  |
| RQ1/RQ2 deployed - detector_count | +0.226 [+0.046, +0.417] | 0.0343 | 0.1372 | 0.0325 | 0.1299 | 15 |  |
| RQ1/RQ2 deployed - first_affected | +0.345 [+0.151, +0.551] | 0.0039 | 0.0273 | 0.0039 | 0.0265 | 13 |  |
| RQ1/RQ2 deployed - simplerca | -0.214 [-0.360, -0.064] | 0.0170 | 0.0850 | 0.0176 | 0.0879 | 13 |  |
| RQ1/RQ2 deployed - largest_anomaly | +0.369 [+0.158, +0.573] | 0.0044 | 0.0273 | 0.0038 | 0.0265 | 23 |  |
| RQ1/RQ2 deployed - rcaeval:nsigma | -0.107 [-0.241, +0.022] | 0.1653 | 0.3750 | 0.1655 | 0.3570 | 15 |  |
| RQ1/RQ2 deployed - rcaeval:baro | +0.357 [+0.176, +0.560] | 0.0018 | 0.0144 | 0.0014 | 0.0115 | 16 |  |
| RQ1/RQ2 deployed - rcaeval:circa | +0.167 [-0.064, +0.378] | 0.1979 | 0.3750 | 0.1933 | 0.3570 | 21 |  |
| RQ1/RQ2 deployed - rcaeval:e_diagnosis | +0.583 [+0.412, +0.747] | 0.0001 | 0.0013 | 0.0000 | 0.0001 | 21 |  |
| RQ1/RQ2 deployed - rcaeval:microcause | +0.405 [+0.224, +0.575] | 0.0005 | 0.0045 | 0.0005 | 0.0041 | 18 |  |
| RQ1/RQ2 deployed - rcaeval:mmnsigma | +0.536 [+0.378, +0.692] | 0.0001 | 0.0013 | 0.0000 | 0.0001 | 21 |  |
| RQ1/RQ2 deployed - rcaeval:mmbaro | +0.536 [+0.378, +0.692] | 0.0001 | 0.0013 | 0.0000 | 0.0001 | 21 |  |
| RQ1/RQ2 deployed - rcaeval:mmcirca | +0.536 [+0.378, +0.692] | 0.0001 | 0.0013 | 0.0000 | 0.0001 | 21 |  |
| P2 lr_visible - deployed | -0.190 [-0.419, +0.023] | 0.1250 | - | 0.1190 | - | 17 | inconclusive |
| P2 lr_visible_re2train - deployed | -0.155 [-0.370, +0.042] | 0.1915 | - | 0.1865 | - | 12 | inconclusive |
| P3b gpt-oss-120b | +0.123 [+0.029, +0.231] | 0.0495 | 0.0495 | 0.0469 | 0.0469 | 8 |  |
| P3b gpt-oss-20b | +0.288 [+0.162, +0.430] | 0.0002 | 0.0006 | 0.0002 | 0.0007 | 13 |  |
| P3b qwen3.8-27b | +0.110 [+0.041, +0.187] | 0.0144 | 0.0288 | 0.0156 | 0.0312 | 7 |  |
| decoy vs placebo (deployed) | +0.123 [+0.029, +0.231] | 0.0495 | 0.0495 | 0.0469 | 0.0469 | 8 |  |

## 2. RE2 RQ1/RQ2 family with the first-run (pre-Amendment-2) RCAEval rankings

Tests in the 11-test family (methods with >= 1 ranked case in the first run): 11.

| comparator | first run: ranked | first run: diff [95% CI] | Holm (11) | Holm (13, chance) | rerun (confirmatory): diff | rerun Holm (13) | verdict changes? |
|---|---|---|---|---|---|---|---|
| lr_visible | 270 | -0.185 [-0.256, -0.119] | 0.0011 | 0.0013 | -0.185 [-0.256, -0.119] | 0.0013 | no |
| detector_count | 270 | -0.156 [-0.219, -0.093] | 0.0011 | 0.0013 | -0.156 [-0.219, -0.093] | 0.0013 | no |
| first_affected | 270 | +0.033 [-0.044, +0.119] | 1.0000 | 1.0000 | +0.033 [-0.044, +0.119] | 1.0000 | no |
| simplerca | 270 | -0.370 [-0.463, -0.274] | 0.0011 | 0.0013 | -0.370 [-0.463, -0.274] | 0.0013 | no |
| largest_anomaly | 270 | +0.248 [+0.167, +0.330] | 0.0011 | 0.0013 | +0.248 [+0.167, +0.330] | 0.0013 | no |
| rcaeval:nsigma | 270 | -0.359 [-0.441, -0.274] | 0.0011 | 0.0013 | -0.359 [-0.441, -0.274] | 0.0013 | no |
| rcaeval:baro | 270 | +0.148 [+0.044, +0.256] | 0.0356 | 0.0356 | +0.148 [+0.044, +0.256] | 0.0445 | no |
| rcaeval:circa | 181 | -0.048 [-0.163, +0.067] | 1.0000 | 1.0000 | -0.048 [-0.163, +0.067] | 1.0000 | no |
| rcaeval:e_diagnosis | 0 | +0.367 [+0.278, +0.459] | not in family | 0.0013 | +0.378 [+0.281, +0.478] | 0.0013 | no |
| rcaeval:microcause | 0 | +0.367 [+0.278, +0.459] | not in family | 0.0013 | +0.370 [+0.285, +0.459] | 0.0013 | no |
| rcaeval:mmnsigma | 249 | -0.322 [-0.415, -0.222] | 0.0011 | 0.0013 | -0.363 [-0.448, -0.274] | 0.0013 | no |
| rcaeval:mmbaro | 249 | +0.174 [+0.070, +0.278] | 0.0115 | 0.0115 | +0.133 [+0.030, +0.237] | 0.0612 | YES |
| rcaeval:mmcirca | 185 | +0.048 [-0.056, +0.156] | 1.0000 | 1.0000 | +0.048 [-0.056, +0.156] | 1.0000 | no |

## 3. RQ0 coverage per system and fault

### RE2

| system | cpu flagged / NOTE | delay flagged / NOTE | disk flagged / NOTE | loss flagged / NOTE | mem flagged / NOTE | socket flagged / NOTE |
|---|---|---|---|---|---|---|
| ob | 8/15 / 0 | 5/15 / 2 | 15/15 / 7 | 14/15 / 12 | 15/15 / 4 | 9/15 / 0 |
| ss | 15/15 / 0 | 15/15 / 0 | 15/15 / 3 | 15/15 / 9 | 15/15 / 2 | 15/15 / 0 |
| tt | 14/15 / 0 | 15/15 / 0 | 15/15 / 8 | 15/15 / 0 | 15/15 / 3 | 15/15 / 0 |
| all | 37/45 / 0 | 35/45 / 2 | 45/45 / 18 | 44/45 / 21 | 45/45 / 9 | 39/45 / 0 |

### RE3

| system | f1 flagged / NOTE | f2 flagged / NOTE | f3 flagged / NOTE | f4 flagged / NOTE | f5 flagged / NOTE |
|---|---|---|---|---|---|
| ob | 9/9 / 6 | 3/3 / 3 | 6/6 / 1 | 6/6 / 6 | 6/6 / 6 |
| ss | 10/10 / 0 | 3/3 / 0 | 7/10 / 0 | 7/7 / 1 | - |
| tt | 4/7 / 0 | 6/7 / 0 | 8/10 / 0 | 3/6 / 0 | - |
| all | 23/26 / 6 | 12/13 / 3 | 21/26 / 1 | 16/19 / 7 | 6/6 / 6 |

## 4. Position: does the top-1 follow the first listed service when the order is permuted?

Multi-service flagged cases. 'old first' = first service in the frozen order; 'new first' = first service after the seeded permutation used by 04_run_llm.py.

| run | cases | first changed | top-1 = new first | top-1 = old first | (of changed) top-1 = new first | (of changed) top-1 = old first | (of changed) frozen run top-1 = old first |
|---|---|---|---|---|---|---|---|
| order1 | 176 | 101 | 73 | 102 | 24/101 | 53/101 | 52/101 |
| order2 | 176 | 92 | 70 | 101 | 19/92 | 50/92 | 46/92 |

## 5. Always-on alarms: flagged with and without the baseline-aware filter (E3)

| system | service | flagged (frozen) | still flagged with filter | dropped by filter (alarm not above 2x its pre-injection level) |
|---|---|---|---|---|
| ss | queue-master | 90/90 | 3 | 87 |
| tt | ts-inside-payment-service | 79/90 | 4 | 75 |
| ob | emailservice | 17/72 | 17 | 0 |

## 6. epsilon-Diagnosis on Train Ticket

TT cases with a ranking: 90/90; mean ranking length 3.0; candidates per case 68.1.
Root found in ranking: 0/90; positions (found): []
Most common top-1: [('ts-inside-payment-service', 7), ('ts-notification-mongo', 7), ('ts-ticket-office-mongo', 5), ('ts-ticket-office-service', 4), ('ts-contacts-service', 4), ('ts-security-service', 4), ('ts-consign-price-service', 4), ('ts-admin-travel-service', 4)]
- raw `ts-auth-service_cpu_1.json`: {'0': ['ts-ticket-office-service_mem', 'ts-station-service_mem', 'ts-food-map-service_mem']}
- raw `ts-auth-service_cpu_2.json`: {'0': ['ts-contacts-service_mem', 'ts-inside-payment-service_mem', 'ts-news-service_mem']}
- raw `ts-auth-service_cpu_3.json`: {'0': ['ts-news-service_mem', 'ts-order-other-service_mem', 'ts-order-service_mem']}
- re2tt_ts-auth-service_cpu_1: root ts-auth-service; ranking[:5] ['ts-ticket-office-service', 'ts-station-service', 'ts-food-map-service']
- re2tt_ts-auth-service_cpu_2: root ts-auth-service; ranking[:5] ['ts-contacts-service', 'ts-inside-payment-service', 'ts-news-service']
- re2tt_ts-auth-service_cpu_3: root ts-auth-service; ranking[:5] ['ts-news-service', 'ts-order-other-service', 'ts-order-service']

## 7. RE3 anon_full: root service in the log samples

| system | root named in log samples, label kept | named, label absent | not named |
|---|---|---|---|
| ob | 18 | 0 | 12 |
| ss | 19 | 0 | 8 |
| tt | 0 | 0 | 21 |
| all | 37 | 0 | 41 |

## 8. Calls and tokens

Calls count every API request (a schema retry is a second call; its tokens are those of the retained response only, so token totals are lower bounds when retries occurred).

| directory | files | records | errors | votes | retries | calls | prompt tokens | completion tokens | finish=length |
|---|---|---|---|---|---|---|---|---|---|
| pilot_re1/llm | 1 | 6 | 0 | 6 | 0 | 6 | 6,335 | 5,833 | 0 |
| pilot_re3/llm | 1 | 5 | 0 | 5 | 0 | 5 | 6,727 | 6,294 | 0 |
| re2/llm | 22 | 4743 | 156 | 4695 | 47 | 4742 | 7,222,221 | 6,477,145 | 2 |
| re2_chronic/llm | 1 | 203 | 0 | 203 | 0 | 203 | 267,534 | 236,621 | 0 |
| re2_shift-120/llm | 1 | 496 | 248 | 248 | 2 | 250 | 374,158 | 349,681 | 0 |
| re2_shift120/llm | 1 | 454 | 227 | 227 | 2 | 229 | 339,112 | 337,086 | 0 |
| re3/llm | 16 | 1083 | 0 | 1083 | 10 | 1093 | 2,299,165 | 1,315,193 | 0 |
| re3_chronic/llm | 1 | 73 | 0 | 73 | 0 | 73 | 153,976 | 82,416 | 0 |
| re3_shift-120/llm | 1 | 80 | 0 | 80 | 0 | 80 | 173,818 | 97,228 | 0 |
| re3_shift120/llm | 1 | 62 | 0 | 62 | 0 | 62 | 86,972 | 79,095 | 0 |
| **total** | 46 | 7205 | 631 | 6682 | 61 | 6743 | 10,930,018 | 8,986,592 | 2 |

Error records were retried by the resumable runner; the evaluation keeps the last successful record.

