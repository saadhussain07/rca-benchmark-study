#!/usr/bin/env bash
# Amendment 7: the generic pipeline. Run from ~/rca/rcastudy with the env active
# and GROQ_API_KEY set. Resumable: rerun the same command after any stop.
set -u
export PYTHONUNBUFFERED=1
R=~/rca/RCAEval; H=~/rca/rcastudy
# 1. build the generic summaries (reads RCAEval data, calls no model)
for S in re3 re2; do
  if [ ! -s $H/out/${S}_generic/contexts.jsonl ]; then
    echo "=== build ${S}_generic $(date '+%F %T')"
    (cd $R && python $H/scripts/18_generic_contexts.py --root data --suite $S --out $H/out/${S}_generic > $H/out/build_${S}_generic.log 2>&1)
    tail -n 1 $H/out/build_${S}_generic.log
  fi
done
rung() { echo "=== $* $(date '+%F %T')"; python scripts/19_run_generic.py "$@"; }
# 2. confirmatory: deployed model
for S in re3 re2; do for C in g_full g_nolog g_decoy; do rung --ctx out/${S}_generic --model gpt-oss-120b --condition $C; done; done
# 3. descriptive: qwen3.8-27b
for S in re3 re2; do for C in g_full g_nolog g_decoy; do rung --ctx out/${S}_generic --model qwen3.8-27b --condition $C; done; done
echo "=== amendment 7 runs finished $(date '+%F %T')"
