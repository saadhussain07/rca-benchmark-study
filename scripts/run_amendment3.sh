#!/usr/bin/env bash
# Amendment 3 model runs (PROTOCOL_V3_AMENDMENT_3.md, B2 and C).
# Run from ~/rca/rcastudy with the env active and GROQ_API_KEY set.
# Resumable: rerun the same command after any stop.
set -u
export PYTHONUNBUFFERED=1
run() { M="$1"; CTX="$2"; shift 2; echo "=== $M $CTX $* $(date '+%F %T')"; python scripts/04_run_llm.py --ctx "$CTX" --model "$M" "$@"; }
# B: build RE3 (once), classifiers, transfer classifier
if [ ! -s out/re3/contexts.jsonl ] || [ "$(wc -l < out/re3/contexts.jsonl)" -lt 90 ]; then
  echo "=== building out/re3 $(date '+%F %T')"
  (cd ~/rca/RCAEval && python ~/rca/rcastudy/scripts/03_build_contexts.py --root data --suite re3 \
      --out ~/rca/rcastudy/out/re3 > ~/rca/rcastudy/out/build_re3.log 2>&1)
  tail -n 2 out/build_re3.log
fi
python scripts/05_classifiers.py --ctx out/re3
python scripts/12_transfer_classifier.py --train-ctx out/re2 --test-ctx out/re3
# B: model runs on RE3
for M in gpt-oss-120b gpt-oss-20b qwen3.8-27b; do
  run $M out/re3 --condition annotated
  run $M out/re3 --condition stripped
  run $M out/re3 --condition decoy
  run $M out/re3 --condition annotated --tag rep2 --note-only
done
run gpt-oss-120b out/re3 --condition placebo
# C: full anonymisation on RE2
for M in gpt-oss-120b gpt-oss-20b qwen3.8-27b; do
  run $M out/re2 --condition anon_full
done
echo "=== amendment 3 model runs finished $(date '+%F %T')"
