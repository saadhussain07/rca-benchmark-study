#!/usr/bin/env bash
# Amendment 5, part A: RE3 rebuilds and model runs. Run from ~/rca/rcastudy with
# the env active and GROQ_API_KEY set. Does not use RCAEval's output/ folder. Resumable.
set -u
export PYTHONUNBUFFERED=1
R=~/rca/RCAEval; H=~/rca/rcastudy
build() { # out extra-args...
  local OUT=$1; shift
  mkdir -p $OUT
  if [ ! -s $OUT/contexts.jsonl ] || [ "$(wc -l < $OUT/contexts.jsonl)" -lt 90 ]; then
    echo "=== build $OUT $* $(date '+%F %T')"
    (cd $R && python $H/scripts/03_build_contexts.py --root data --suite re3 --out $OUT "$@" > $OUT/build.log 2>&1)
    tail -n 1 $OUT/build.log
  fi
}
run() { echo "=== $* $(date '+%F %T')"; python scripts/04_run_llm.py "$@"; }
# H5b: full anonymisation on RE3, all three models
for M in gpt-oss-120b gpt-oss-20b qwen3.8-27b; do run --ctx out/re3 --model $M --condition anon_full; done
# H5a: baseline-aware log alarms on RE3
build $H/out/re3_chronic --chronic-filter
run --ctx out/re3_chronic --model gpt-oss-120b --condition annotated
# H5c and descriptive onset table: shifted RE3 builds
for S in -120 120; do
  build $H/out/re3_shift$S --onset-shift $S
  python scripts/05_classifiers.py --ctx out/re3_shift$S
  if [ ! -s out/re3_shift$S/ranks_simplerca_variants.json ]; then
    (cd $R && python $H/scripts/13_simplerca_variants.py --root data --suite re3 --ctx $H/out/re3_shift$S --onset-shift $S > $H/out/re3_shift$S/variants.log 2>&1)
  fi
  run --ctx out/re3_shift$S --model gpt-oss-120b --condition annotated
done
echo "=== amendment 5 part A finished $(date '+%F %T')"
