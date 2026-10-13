# Amendment 7 analyses (20_amendment7.py); M = qwen3.8-27b

Generic pipeline, deployed model unless stated; AC@1 on all cases; decoy tests on cases with a decoy. Holm over H7a-H7d. The second model is descriptive.

## Primary

| test | diff [95% CI] | p | p Holm | exact p Holm | verdict |
|---|---|---|---|---|---|
| H7a RE2+RE3 decoy first: g_decoy - g_full | +0.586 [+0.529, +0.643] | 0.0001 | 0.0004 | 0.0000 | supported |
| H7b RE3 g_full - g_nolog | +0.067 [-0.011, +0.148] | 0.1836 | 0.5288 | 0.5288 | not supported |
| H7c (g_full - g_nolog): RE3 minus RE2 | +0.059 [-0.021, +0.150] | 0.1763 | 0.5288 | 0.5288 | not supported |
| H7d RE2 summary_count - g_full | -0.044 [-0.104, +0.015] | 0.1831 | 0.5288 | 0.5288 | not supported |

## Sensitivity: RE3 without 6 pilot cases

| test | diff [95% CI] | p | p Holm | exact p Holm | verdict |
|---|---|---|---|---|---|
| H7a RE2+RE3 decoy first: g_decoy - g_full | +0.582 [+0.523, +0.639] | 0.0001 | 0.0004 | 0.0000 | supported |
| H7b RE3 g_full - g_nolog | +0.071 [-0.011, +0.160] | 0.1836 | 0.3687 | 0.3720 | not supported |
| H7c (g_full - g_nolog): RE3 minus RE2 | +0.064 [-0.020, +0.161] | 0.1229 | 0.3687 | 0.3687 | not supported |
| H7d RE2 summary_count - g_full | -0.044 [-0.104, +0.015] | 0.1831 | 0.3687 | 0.3720 | not supported |

## Descriptive

### AC@1, all cases

| suite | pipeline | model | annotated | stripped | decoy | nolog |
|---|---|---|---|---|---|---|
| re2 | deployed agent | gpt-oss-120b | 0.441 | 0.456 | 0.370 | 0.426 |
| re2 | deployed agent | qwen3.8-27b | 0.393 | 0.370 | 0.378 | nan |
| re3 | deployed agent | gpt-oss-120b | 0.600 | 0.578 | 0.556 | 0.356 |
| re3 | deployed agent | qwen3.8-27b | 0.633 | 0.622 | 0.578 | 0.411 |

| suite | pipeline | model | g_full | g_nolog | g_decoy |
|---|---|---|---|---|---|
| re2 | generic | gpt-oss-120b | 0.870 | 0.863 | 0.341 |
| re2 | generic | qwen3.8-27b | 0.893 | 0.922 | 0.704 |
| re3 | generic | gpt-oss-120b | 0.889 | 0.822 | 0.411 |
| re3 | generic | qwen3.8-27b | 0.889 | 0.811 | 0.711 |

### Decoy named first (cases with a decoy)

| suite | pipeline | model | with decoy | without | n | harm (correct without, decoy first with) |
|---|---|---|---|---|---|---|
| re2 | deployed agent | gpt-oss-120b | 83 | 9 | 245 | 24/119 |
| re2 | deployed agent | qwen3.8-27b | 52 | 9 | 245 | 8/96 |
| re3 | deployed agent | gpt-oss-120b | 15 | 4 | 78 | 3/52 |
| re3 | deployed agent | qwen3.8-27b | 12 | 3 | 78 | 4/56 |
| re2 | generic | gpt-oss-120b | 168 | 3 | 270 | 144/235 |
| re2 | generic | qwen3.8-27b | 65 | 1 | 270 | 49/241 |
| re3 | generic | gpt-oss-120b | 48 | 2 | 90 | 41/80 |
| re3 | generic | qwen3.8-27b | 26 | 2 | 90 | 17/80 |

### Paired differences (descriptive)

| comparison | diff [95% CI] | p |
|---|---|---|
| RE3 summary_count - g_full (gpt-oss-120b) | -0.089 [-0.196, +0.000] | 0.1440 |
| RE2 g_full - g_nolog (gpt-oss-120b) | +0.007 [-0.026, +0.044] | 0.8421 |
| RE3 g_full - g_nolog (gpt-oss-120b) | +0.067 [-0.011, +0.148] | 0.1836 |
| RE3 g_nolog - summary_count (gpt-oss-120b) | +0.022 [-0.101, +0.155] | 0.8763 |
| RE2 g_full (gpt-oss-120b) - deployed agent annotated (gpt-oss-120b) | +0.430 [+0.348, +0.511] | 0.0001 |
| RE3 g_full (gpt-oss-120b) - deployed agent annotated (gpt-oss-120b) | +0.289 [+0.106, +0.466] | 0.0103 |
| RE3 summary_count - g_full (qwen3.8-27b) | -0.089 [-0.200, +0.011] | 0.1590 |
| RE2 g_full - g_nolog (qwen3.8-27b) | -0.030 [-0.063, +0.000] | 0.1147 |
| RE3 g_full - g_nolog (qwen3.8-27b) | +0.078 [-0.034, +0.209] | 0.3091 |
| RE3 g_nolog - summary_count (qwen3.8-27b) | +0.011 [-0.120, +0.136] | 1.0000 |
| RE2 g_full (qwen3.8-27b) - deployed agent annotated (qwen3.8-27b) | +0.500 [+0.407, +0.589] | 0.0001 |
| RE3 g_full (qwen3.8-27b) - deployed agent annotated (qwen3.8-27b) | +0.256 [+0.108, +0.386] | 0.0046 |
| RE2 summary_count - g_full (qwen3.8-27b) | -0.067 [-0.119, -0.015] | 0.0261 |
| RE2 g_full (gpt-oss-120b) - rcaeval:nsigma | +0.070 [+0.000, +0.144] | 0.0808 |
| RE2 g_full (gpt-oss-120b) - simplerca | +0.059 [-0.004, +0.122] | 0.0860 |
| RE2 g_full (gpt-oss-120b) - detector_count | +0.274 [+0.196, +0.348] | 0.0001 |
| RE2 summary_count - rcaeval:nsigma | +0.026 [-0.048, +0.104] | 0.5830 |
| RE3 g_full (gpt-oss-120b) - rcaeval:nsigma | +0.156 [+0.012, +0.302] | 0.0640 |
| RE3 g_full (gpt-oss-120b) - simplerca | +0.056 [-0.034, +0.161] | 0.4091 |
| RE3 g_full (gpt-oss-120b) - detector_count | +0.511 [+0.402, +0.629] | 0.0001 |
| RE3 summary_count - rcaeval:nsigma | +0.067 [-0.080, +0.202] | 0.4519 |

summary_count AC@1: RE2 0.826, RE3 0.800

### Checks

- re2g gpt-oss-120b g_nolog: prompts with an example log line left: 0/270
- re2g qwen3.8-27b g_nolog: prompts with an example log line left: 0/270
- re2g: cases 270, build failures 0
- re3g gpt-oss-120b g_nolog: prompts with an example log line left: 0/90
- re3g qwen3.8-27b g_nolog: prompts with an example log line left: 0/90
- re3g: cases 90, build failures 0
