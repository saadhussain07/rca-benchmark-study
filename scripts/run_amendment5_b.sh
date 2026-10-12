#!/usr/bin/env bash
# Amendment 5, part B: N-Sigma and BARO on RE3 with the onset shifted by --tdelta.
# Run from ~/rca/RCAEval, env active; nothing else may be using output/results. Resumable.
set -u
for S in -120 120; do
  for m in nsigma baro; do
    for d in re3-ob re3-ss re3-tt; do
      tag="${m}__${d}"; K="output/kept_re3_shift$S/$tag"
      if [ -f "$K/STATUS" ]; then echo "skip $S $tag"; continue; fi
      rm -rf "$K" output/results; mkdir -p output/results "$K"
      echo "=== $tag tdelta=$S $(date '+%F %T')"
      timeout 7200 python main.py --method "$m" --dataset "$d" --length 20 --tdelta "$S" > "logs_baselines/${tag}__shift$S.txt" 2>&1
      rc=$?
      mv output/results/*.json "$K/" 2>/dev/null
      echo "exit=$rc a5 tdelta=$S" > "$K/STATUS"
      echo "    exit=$rc results=$(ls "$K" | grep -c '\.json$')"
    done
  done
  python ~/rca/rcastudy/scripts/07_collect_rcaeval.py --kept "output/kept_re3_shift$S" --ctx ~/rca/rcastudy/out/re3_shift$S
done
echo "=== amendment 5 part B finished $(date '+%F %T')"
