#!/usr/bin/env bash
# Amendment 6: log-text ablation and name permutation. Run from ~/rca/rcastudy
# with the env active and GROQ_API_KEY set. Uses existing contexts only (no
# rebuild, no RCAEval). Resumable: rerun the same command after any stop.
# Order = priority: the confirmatory runs come first.
set -u
export PYTHONUNBUFFERED=1
run() { echo "=== $* $(date '+%F %T')"; python scripts/04_run_llm.py "$@"; }
D=gpt-oss-120b
# 1. confirmatory, RE3, deployed model (H6a, H6c)
run --ctx out/re3 --model $D --condition nolog
run --ctx out/re3 --model $D --condition permuted
# 2. confirmatory, RE2, deployed model (H6b)
run --ctx out/re2 --model $D --condition nolog
# 3. descriptive: the other two models on RE3
for M in gpt-oss-20b qwen3.8-27b; do
  run --ctx out/re3 --model $M --condition nolog
  run --ctx out/re3 --model $M --condition permuted
done
# 4. descriptive: permuted on RE2, deployed model
run --ctx out/re2 --model $D --condition permuted
# 5. descriptive: a second annotated run on RE3 (run-to-run variation)
run --ctx out/re3 --model $D --condition annotated --tag a6rep
echo "=== amendment 6 runs finished $(date '+%F %T')"
