# Verdicts and exploratory analyses (10_exploratory.py)

Section 1 restates pre-registered verdicts. Every other section is exploratory and post hoc.

## 1. Pre-registered verdicts (Monte Carlo p as pre-registered; exact p alongside)

- **P2** lr_visible minus deployed: +0.185 [+0.119, +0.256]; non-inferiority margin -0.05 -> **supported** (superior: the interval excludes 0).
- **P3a gpt-oss-120b**: +0.100 [-0.021, +0.234]; MC p 0.2365 (Holm 0.4730); exact p 2.34e-01 over 8 non-zero clusters (Holm 0.4688) -> **not supported**.
- **P3a gpt-oss-20b**: -0.020 [-0.206, +0.163]; MC p 1.0000 (Holm 1.0000); exact p 1.00e+00 over 10 non-zero clusters (Holm 1.0000) -> **not supported**.
- **P3a qwen3.8-27b**: +0.140 [+0.055, +0.250]; MC p 0.0177 (Holm 0.0531); exact p 1.56e-02 over 7 non-zero clusters (Holm 0.0469) -> **not supported** **(borderline: the exact test gives the opposite verdict; both reported)**.
- **P3b gpt-oss-120b**: +0.302 [+0.237, +0.367]; MC p 0.0001 (Holm 0.0003); exact p 0.00e+00 over 51 non-zero clusters (Holm 0.0000) -> **supported**; decoy named first in 34% of cases -> does not outweigh the evidence (rule: > 50%).
- **P3b gpt-oss-20b**: +0.376 [+0.313, +0.442]; MC p 0.0001 (Holm 0.0003); exact p 0.00e+00 over 62 non-zero clusters (Holm 0.0000) -> **supported**; decoy named first in 42% of cases -> does not outweigh the evidence (rule: > 50%).
- **P3b qwen3.8-27b**: +0.176 [+0.128, +0.229]; MC p 0.0001 (Holm 0.0003); exact p 0.00e+00 over 34 non-zero clusters (Holm 0.0000) -> **supported**; decoy named first in 21% of cases -> does not outweigh the evidence (rule: > 50%).
- **P3c**: agree annotated 36/50 vs stripped 37/50; -0.020 [-0.213, +0.167]; MC p 1.0000; exact 1.000 -> **not supported**.
- **RQ4**: anon minus named +0.045 [-0.000, +0.090] (90% CI) -> equivalence within ±0.05 **not shown**; no change detected (p 0.167).

## 2. Exploratory: paired AC@1 differences on flagged cases only (deployed minus comparator)

| comparator | all cases | flagged only |
|---|---|---|
| lr_visible | -0.185 [-0.256, -0.119] | -0.208 [-0.275, -0.142] |
| lr_visible_loso | -0.104 [-0.167, -0.041] | -0.122 [-0.188, -0.057] |
| detector_count | -0.156 [-0.219, -0.093] | -0.184 [-0.250, -0.118] |
| first_affected | +0.033 [-0.044, +0.119] | +0.033 [-0.056, +0.117] |
| simplerca | -0.370 [-0.463, -0.274] | -0.359 [-0.458, -0.258] |
| largest_anomaly | +0.248 [+0.167, +0.330] | +0.290 [+0.210, +0.372] |
| rcaeval:baro | +0.148 [+0.044, +0.256] | +0.147 [+0.032, +0.253] |
| rcaeval:causalrca | +0.359 [+0.270, +0.452] | +0.392 [+0.297, +0.488] |
| rcaeval:circa | -0.048 [-0.163, +0.067] | -0.020 [-0.145, +0.112] |
| rcaeval:e_diagnosis | +0.378 [+0.281, +0.478] | +0.400 [+0.295, +0.504] |
| rcaeval:microcause | +0.370 [+0.285, +0.459] | +0.404 [+0.312, +0.496] |
| rcaeval:mmbaro | +0.133 [+0.030, +0.237] | +0.135 [+0.024, +0.240] |
| rcaeval:mmcirca | +0.048 [-0.056, +0.156] | +0.073 [-0.043, +0.189] |
| rcaeval:mmnsigma | -0.363 [-0.448, -0.274] | -0.351 [-0.440, -0.260] |
| rcaeval:nsigma | -0.359 [-0.441, -0.274] | -0.347 [-0.435, -0.260] |

## 3. Exploratory: position in the AFFECTED SERVICES line

| model | top-1 = first listed (multi-service cases) | P(correct \| root listed first) | P(correct \| root not first) |
|---|---|---|---|
| gpt-oss-120b | 99/176 | 0.61 (n=61) | 0.28 (n=115) |
| gpt-oss-20b | 106/176 | 0.66 (n=61) | 0.25 (n=115) |
| qwen3.8-27b | 125/176 | 0.67 (n=61) | 0.13 (n=115) |

Shuffled order 1 (gpt-oss-120b): AC@1 0.469 vs deployed order 0.469; difference +0.000 [-0.036, +0.036], p 1.0000

Shuffled order 2 (gpt-oss-120b): AC@1 0.498 vs deployed order 0.469; difference +0.029 [-0.013, +0.070], p 0.2455

## 4. Exploratory: run-to-run variation on identical prompts

No-NOTE cases: the annotated and stripped prompts are byte-identical, so a change is pure run-to-run variation.

| model | top-1 changed (all) | OB | SS | TT |
|---|---|---|---|---|
| gpt-oss-120b | 39/195 | 3/41 | 13/76 | 23/78 |
| gpt-oss-20b | 41/195 | 3/41 | 20/76 | 18/78 |
| qwen3.8-27b | 6/195 | 0/41 | 0/76 | 6/78 |

Repeated runs of gpt-oss-120b (annotated, flagged cases, 3 runs): AC@1 per run 0.469, 0.482, 0.478; mean 0.476, SD 0.006; unique-plurality AC@1 0.465

## 5. Exploratory: always-on alarms

| system | most often flagged non-root service | flagged in | gpt-oss-120b names it first | gpt-oss-20b names it first | qwen3.8-27b names it first |
|---|---|---|---|---|---|
| ob | emailservice | 17/66 | 14/66 | 13/66 | 13/66 |
| ss | queue-master | 90/90 | 69/90 | 70/90 | 82/90 |
| tt | ts-inside-payment-service | 79/89 | 18/89 | 28/89 | 41/89 |

E3 baseline-aware log alarms: flagged cases 203/270 (frozen pipeline: 245/270).

| method | system | AC@1 frozen pipeline | AC@1 with alarm filter | difference [95% CI] |
|---|---|---|---|---|
| deployed model | ob | 0.689 | 0.700 | +0.011 [+0.000, +0.033] |
| deployed model | ss | 0.167 | 0.589 | +0.422 [+0.289, +0.556] |
| deployed model | tt | 0.467 | 0.511 | +0.044 [-0.011, +0.100] |
| deployed model | all | 0.441 | 0.600 | +0.159 [+0.096, +0.222] |
| detector_count | ob | 0.689 | 0.689 | +0.000 [+0.000, +0.000] |
| detector_count | ss | 0.522 | 0.533 | +0.011 [-0.022, +0.056] |
| detector_count | tt | 0.578 | 0.589 | +0.011 [+0.000, +0.033] |
| detector_count | all | 0.596 | 0.604 | +0.007 [-0.007, +0.022] |

## 6. Exploratory: decoy detail

| model | system | decoy first: decoy | placebo | stripped | decoy in top 5: decoy | placebo | stripped |
|---|---|---|---|---|---|---|---|
| gpt-oss-120b | ob | 14/66 | 1 | 1 | 54 | 40 | 25 |
| gpt-oss-120b | ss | 41/90 | 13 | 8 | 87 | 71 | 46 |
| gpt-oss-120b | tt | 28/89 | 3 | 0 | 83 | 61 | 5 |
| gpt-oss-120b | all | 83/245 | 17 | 9 | 224 | 172 | 76 |
| gpt-oss-20b | ob | 17/66 | - | 1 | 63 | - | 25 |
| gpt-oss-20b | ss | 42/90 | - | 7 | 84 | - | 41 |
| gpt-oss-20b | tt | 43/89 | - | 2 | 82 | - | 8 |
| gpt-oss-20b | all | 102/245 | - | 10 | 229 | - | 74 |
| qwen3.8-27b | ob | 8/66 | - | 0 | 48 | - | 21 |
| qwen3.8-27b | ss | 19/90 | - | 8 | 79 | - | 44 |
| qwen3.8-27b | tt | 25/89 | - | 1 | 66 | - | 6 |
| qwen3.8-27b | all | 52/245 | - | 9 | 193 | - | 71 |

## 7. Exploratory: anonymisation by system and leak status

| subset | n | named AC@1 | anonymised AC@1 | difference [95% CI] |
|---|---|---|---|---|
| OB | 66 | 0.879 | 0.924 | +0.045 [-0.048, +0.141] |
| SS | 90 | 0.167 | 0.311 | +0.144 [+0.044, +0.256] |
| TT | 89 | 0.472 | 0.416 | -0.056 [-0.136, +0.011] |
| no leaked name | 159 | 0.635 | 0.623 | -0.013 [-0.075, +0.051] |
| leaked name | 86 | 0.163 | 0.314 | +0.151 [+0.047, +0.262] |

## 8. Exploratory: what the natural NOTEs pointed at

NOTE lines mentioning the root service: 42/68
