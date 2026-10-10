#!/usr/bin/env bash
# Exploratory runs E1-E3 of PROTOCOL_V3_AMENDMENT_1.md (deployed model only).
# Run from ~/rca/rcastudy with the env active and GROQ_API_KEY set.
# Resumable: rerun the same command after any stop.
set -u
M=gpt-oss-120b
run() { echo "=== $* $(date '+%F %T')"; python scripts/04_run_llm.py --model "$M" "$@"; }
# E1 repeat runs
run --ctx out/re2 --condition annotated --tag repA
run --ctx out/re2 --condition annotated --tag repB
# E2 order randomisation
run --ctx out/re2 --condition shuffled --order-seed 1 --tag order1
run --ctx out/re2 --condition shuffled --order-seed 2 --tag order2
# E3 baseline-aware log alarms (rebuild once, then one run)
if [ ! -s out/re2_chronic/contexts.jsonl ] || [ "$(wc -l < out/re2_chronic/contexts.jsonl)" -lt 270 ]; then
  echo "=== building out/re2_chronic $(date '+%F %T')"
  (cd ~/rca/RCAEval && python ~/rca/rcastudy/scripts/03_build_contexts.py --root data --suite re2 \
      --out ~/rca/rcastudy/out/re2_chronic --chronic-filter > ~/rca/rcastudy/out/build_re2_chronic.log 2>&1)
fi
run --ctx out/re2_chronic --condition annotated --tag main
echo "=== exploratory runs finished $(date '+%F %T')"
python scripts/10_exploratory.py --ctx out/re2 --ctx-chronic out/re2_chronic > /dev/null && echo "wrote out/re2/exploratory.md"
