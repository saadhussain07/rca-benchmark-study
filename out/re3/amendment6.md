# Amendment 6 analyses (17_amendment6.py)

Deployed model; AC@1 on all cases (unflagged cases ranked by chance, as everywhere in the study). p = cluster sign-flip permutation (10,000), exact = enumeration or 10^6 flips; H6b uses a cluster-label permutation between suites. Holm over H6a, H6b, H6c-1, H6c-2.

## 0. Manipulation checks

| suite | model | condition | records | check value > 0 | answers with no resolvable service |
|---|---|---|---|---|---|
| re2 | gpt-oss-120b | nolog | 245 | 0 | 0 |
| re2 | gpt-oss-120b | permuted | 245 | 0 | 0 |
| re3 | gpt-oss-120b | nolog | 78 | 3 | 0 |
| re3 | gpt-oss-120b | permuted | 78 | 0 | 0 |
| re3 | gpt-oss-20b | nolog | 78 | 3 | 0 |
| re3 | gpt-oss-20b | permuted | 78 | 0 | 0 |
| re3 | qwen3.8-27b | nolog | 78 | 3 | 0 |
| re3 | qwen3.8-27b | permuted | 78 | 0 | 0 |

`nolog`: check value = raw log strings left in the prompt. `permuted`: check value = prompts whose name-free skeleton differs from the original's. Both must be 0.

## Primary: all 90 RE3 cases (RE2: 270)

| test | diff [95% CI] | p | p Holm | exact p | exact p Holm |
|---|---|---|---|---|---|
| H6a RE3 annotated - nolog | +0.244 [+0.107, +0.409] | 0.0052 | 0.0156 | 0.0039 | 0.0117 |
| H6b (annotated - nolog): RE3 minus RE2 | +0.230 [+0.069, +0.394] | 0.0012 | 0.0048 | - | 0.0048 |
| H6c-1 RE3 permuted - anon_full | +0.011 [-0.066, +0.080] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| H6c-2 RE3 annotated - permuted | +0.200 [+0.056, +0.363] | 0.0247 | 0.0494 | 0.0225 | 0.0449 |

- **H6a**: supported: raw log text raises RE3 accuracy
- **H6b**: supported: log text matters more on RE3 than on RE2
- **H6c-2**: names that mean the right service help (correct meaning matters)
- **H6c-1**: no difference between wrong names and labels detected

## Sensitivity: 84 RE3 cases outside the pilot

| test | diff [95% CI] | p | p Holm | exact p | exact p Holm |
|---|---|---|---|---|---|
| H6a RE3 annotated - nolog | +0.238 [+0.098, +0.403] | 0.0063 | 0.0189 | 0.0059 | 0.0176 |
| H6b (annotated - nolog): RE3 minus RE2 | +0.223 [+0.064, +0.390] | 0.0017 | 0.0068 | - | 0.0068 |
| H6c-1 RE3 permuted - anon_full | +0.000 [-0.074, +0.061] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| H6c-2 RE3 annotated - permuted | +0.202 [+0.065, +0.362] | 0.0182 | 0.0364 | 0.0176 | 0.0352 |

- **H6a**: supported: raw log text raises RE3 accuracy
- **H6b**: supported: log text matters more on RE3 than on RE2
- **H6c-2**: names that mean the right service help (correct meaning matters)
- **H6c-1**: no difference between wrong names and labels detected

## Secondary and descriptive

### Accuracy by condition (AC@1, all cases)

| suite | model | annotated | nolog | permuted | anon_full |
|---|---|---|---|---|---|
| re2 | gpt-oss-120b | 0.441 | 0.426 | 0.474 | 0.470 |
| re2 | gpt-oss-20b | 0.441 | - | - | 0.526 |
| re2 | qwen3.8-27b | 0.393 | - | - | 0.444 |
| re3 | gpt-oss-120b | 0.600 | 0.356 | 0.400 | 0.389 |
| re3 | gpt-oss-20b | 0.544 | 0.300 | 0.378 | 0.378 |
| re3 | qwen3.8-27b | 0.633 | 0.411 | 0.367 | 0.467 |

### Paired differences, every model and suite (descriptive except the four tests above)

| suite | model | annotated - nolog | permuted - anon_full | annotated - permuted |
|---|---|---|---|---|
| re2 | gpt-oss-120b | +0.015 [-0.041, +0.070], p 0.692 | +0.004 [-0.044, +0.052], p 1.000 | -0.033 [-0.085, +0.026], p 0.289 |
| re2 | gpt-oss-20b | - | - | - |
| re2 | qwen3.8-27b | - | - | - |
| re3 | gpt-oss-120b | +0.244 [+0.107, +0.409], p 0.005 | +0.011 [-0.066, +0.080], p 1.000 | +0.200 [+0.056, +0.363], p 0.025 |
| re3 | gpt-oss-20b | +0.244 [+0.108, +0.407], p 0.005 | +0.000 [-0.070, +0.067], p 1.000 | +0.167 [+0.023, +0.322], p 0.054 |
| re3 | qwen3.8-27b | +0.222 [+0.107, +0.372], p 0.005 | -0.100 [-0.194, -0.032], p 0.028 | +0.267 [+0.122, +0.438], p 0.004 |

### Without log text, against the detector count (deployed)

| suite | annotated - detector_count | nolog - detector_count |
|---|---|---|
| re2 | -0.156 [-0.219, -0.093], p 0.000 | -0.170 [-0.241, -0.096], p 0.000 |
| re3 | +0.222 [+0.049, +0.414], p 0.035 | -0.022 [-0.132, +0.080], p 0.848 |

### RE3 strata: do the log samples name the root? (flagged cases, deployed)

| stratum | n | annotated | nolog | annotated - nolog [95% CI] | permuted | anon_full |
|---|---|---|---|---|---|---|
| root named in log samples | 37 | 0.622 | 0.297 | +0.324 [+0.086, +0.595] | 0.459 | 0.459 |
| root not named | 41 | 0.756 | 0.512 | +0.244 [+0.053, +0.462] | 0.463 | 0.439 |

### Pull of the root's real name under `permuted`

How often the model's top-1 is the service now *shown* under the root's real name (a wrong service), against the count expected if that service were picked at chance among the candidates.

| suite | model | flagged cases | top-1 = service shown with the root's name | expected at chance | top-1 = true root |
|---|---|---|---|---|---|
| re2 | gpt-oss-120b | 245 | 10 | 15.0 | 124 |
| re3 | gpt-oss-120b | 78 | 18 | 5.1 | 36 |
| re3 | gpt-oss-20b | 78 | 20 | 5.1 | 34 |
| re3 | qwen3.8-27b | 78 | 17 | 5.1 | 33 |

### Run-to-run on RE3 (deployed, annotated, second run)

Top-1 changed in 7/78 flagged cases; AC@1 0.567 vs 0.600, difference -0.033 [-0.116, +0.023], p 0.753.
