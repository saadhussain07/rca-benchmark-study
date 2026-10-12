# Amendment 5: pre-registered tests on RE3 (15_amendment5.py)

## Primary: all 90 RE3 cases

- **H5a** flagged cases with the filter: 73/90 (without: 78). Deployed AC@1 0.600 -> 0.711: +0.111 [+0.011, +0.242], p 0.1264. Detector count 0.378 -> 0.433. Difference in differences +0.056 [-0.036, +0.165], p 0.3788.
- **H5b** gpt-oss-120b: anon_full minus annotated -0.211 [-0.379, -0.065], p 0.0174; lower bound > -0.05: not supported.
- H5b (descriptive) gpt-oss-20b: anon_full minus annotated -0.167 [-0.333, -0.021], p 0.0684; lower bound > -0.05: not supported.
- H5b (descriptive) qwen3.8-27b: anon_full minus annotated -0.167 [-0.326, -0.033], p 0.0455; lower bound > -0.05: not supported.
- **H5c-1** rcaeval:nsigma: AC@1 0.733 -> 0.089; deployed 0.600 -> 0.389. Loss of rcaeval:nsigma minus loss of the model +0.433 [+0.258, +0.607], p 0.0001.
- **H5c-2** simplerca: AC@1 0.833 -> 0.267; deployed 0.600 -> 0.389. Loss of simplerca minus loss of the model +0.356 [+0.253, +0.464], p 0.0001.
  - H5a_did: Holm p 0.3788 -> **not supported** (predicted direction: positive)
  - H5c-1: Holm p 0.0003 -> **supported** (predicted direction: positive)
  - H5c-2: Holm p 0.0003 -> **supported** (predicted direction: positive)

## Sensitivity: 84 cases outside the pilot

- **H5a** flagged cases with the filter: 68/84 (without: 73). Deployed AC@1 0.607 -> 0.714: +0.107 [+0.012, +0.241], p 0.1264. Detector count 0.381 -> 0.429. Difference in differences +0.060 [-0.013, +0.159], p 0.3788.
- **H5b** gpt-oss-120b: anon_full minus annotated -0.202 [-0.378, -0.046], p 0.0315; lower bound > -0.05: not supported.
- H5b (descriptive) gpt-oss-20b: anon_full minus annotated -0.179 [-0.346, -0.034], p 0.0501; lower bound > -0.05: not supported.
- H5b (descriptive) qwen3.8-27b: anon_full minus annotated -0.167 [-0.330, -0.034], p 0.0631; lower bound > -0.05: not supported.
- **H5c-1** rcaeval:nsigma: AC@1 0.714 -> 0.095; deployed 0.607 -> 0.393. Loss of rcaeval:nsigma minus loss of the model +0.405 [+0.226, +0.584], p 0.0001.
- **H5c-2** simplerca: AC@1 0.821 -> 0.250; deployed 0.607 -> 0.393. Loss of simplerca minus loss of the model +0.357 [+0.247, +0.469], p 0.0001.
  - H5a_did: Holm p 0.3788 -> **not supported** (predicted direction: positive)
  - H5c-1: Holm p 0.0003 -> **supported** (predicted direction: positive)
  - H5c-2: Holm p 0.0003 -> **supported** (predicted direction: positive)

## Descriptive: onset shifts on RE3

| method | -120 s | 0 s | +120 s |
|---|---|---|---|
| llm:gpt-oss-120b__annotated | 0.611 | 0.600 | 0.389 |
| detector_count | 0.389 | 0.378 | 0.089 |
| lr_visible | 0.467 | 0.422 | 0.233 |
| simplerca | 0.711 | 0.833 | 0.267 |
| simplerca:V3 | 0.444 | 0.500 | 0.178 |
| rcaeval:nsigma | 0.667 | 0.733 | 0.089 |
| rcaeval:baro | 0.211 | 0.256 | 0.356 |
