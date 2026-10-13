#!/usr/bin/env bash
# Amendment 8: (A) evidence x prompt 2x2, (B) the generic pipeline under onset shifts.
# Run from ~/rca/rcastudy with the env active and GROQ_API_KEY set. Resumable.
set -u
export PYTHONUNBUFFERED=1
R=~/rca/RCAEval; H=~/rca/rcastudy; D=gpt-oss-120b
# 1. build shifted generic summaries (reads RCAEval data, calls no model)
for S in re3 re2; do for SH in 120 -120; do
  O=$H/out/${S}_generic_shift$SH
  if [ ! -s $O/contexts.jsonl ]; then
    echo "=== build ${S}_generic_shift$SH $(date '+%F %T')"
    (cd $R && python $H/scripts/18_generic_contexts.py --root data --suite $S --out $O --onset-shift $SH > $H/out/build_${S}_generic_shift$SH.log 2>&1)
    tail -n 1 $H/out/build_${S}_generic_shift$SH.log
  fi
done; done
# 2. part A: the two crossed cells (deployed agent's flagged cases)
for S in re3 re2; do for C in x_dsys_guser x_gsys_duser; do
  echo "=== 21 $S $C $(date '+%F %T')"; python scripts/21_run_crossed.py --suite $S --model $D --condition $C
done; done
# 3. part B: g_full under onset shifts (+120 is confirmatory, -120 descriptive)
for SH in 120 -120; do for S in re3 re2; do
  echo "=== 19 ${S}_generic_shift$SH $(date '+%F %T')"; python scripts/19_run_generic.py --ctx out/${S}_generic_shift$SH --model $D --condition g_full
done; done
echo "=== amendment 8 runs finished $(date '+%F %T')"
