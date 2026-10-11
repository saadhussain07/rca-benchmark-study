#!/usr/bin/env bash
# Amendment 4 (exploratory), part A: SimpleRCA variants and onset-shifted
# pipeline runs. Run from ~/rca/rcastudy with the env active and GROQ_API_KEY
# set. Does not touch RCAEval's output/ folder, so it can run alongside the
# RE3 baselines. Resumable.
set -u
export PYTHONUNBUFFERED=1
R=~/rca/RCAEval; H=~/rca/rcastudy
variants() { # suite ctx shift
  if [ ! -s "$2/ranks_simplerca_variants.json" ]; then
    echo "=== variants $1 $2 shift=$3 $(date '+%F %T')"
    (cd $R && python $H/scripts/13_simplerca_variants.py --root data --suite "$1" --ctx "$2" --onset-shift "$3" > "$2/variants.log" 2>&1)
    tail -n 1 "$2/variants.log"
  fi
}
variants re2 $H/out/re2 0
variants re3 $H/out/re3 0
for S in -120 120; do
  CTX=$H/out/re2_shift$S
  mkdir -p $CTX
  if [ ! -s $CTX/contexts.jsonl ] || [ "$(wc -l < $CTX/contexts.jsonl)" -lt 270 ]; then
    echo "=== build re2 shift $S $(date '+%F %T')"
    (cd $R && python $H/scripts/03_build_contexts.py --root data --suite re2 --out $CTX --onset-shift $S > $CTX/build.log 2>&1)
    tail -n 1 $CTX/build.log
  fi
  python scripts/05_classifiers.py --ctx $CTX
  variants re2 $CTX $S
  echo "=== gpt-oss-120b annotated shift $S $(date '+%F %T')"
  python scripts/04_run_llm.py --ctx $CTX --model gpt-oss-120b --condition annotated
done
echo "=== amendment 4 part A finished $(date '+%F %T')"
