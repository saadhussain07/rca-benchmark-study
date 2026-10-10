#!/usr/bin/env bash
# Every pre-registered model run for one model, in a fixed order.
# Usage (from ~/rca/rcastudy, GROQ_API_KEY set):  bash scripts/run_llm_model.sh gpt-oss-120b out/re2
# Each step resumes where it stopped, so the script can simply be run again.
set -u
M="$1"; CTX="${2:-out/re2}"
run() { echo "=== $M $* $(date '+%F %T')"; python scripts/04_run_llm.py --ctx "$CTX" --model "$M" "$@"; }
run --condition annotated
run --condition stripped
run --condition decoy
run --condition annotated --tag rep2 --note-only
if [ "$M" = "gpt-oss-120b" ]; then
  run --condition placebo
  run --condition anon
  run --condition annotated --votes 5 --subset "$CTX/../vote_check_cases.txt" --tag votecheck
fi
echo "=== $M finished $(date '+%F %T')"
