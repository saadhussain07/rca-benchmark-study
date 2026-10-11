#!/usr/bin/env bash
# Amendment 4 (exploratory), part B: N-Sigma and BARO with the onset shifted by
# --tdelta. Run from ~/rca/RCAEval, env active, AFTER run_rcaeval_re3.sh has
# finished (both use output/results). Resumable.
set -u
for S in -120 120; do
  for m in nsigma baro; do
    for d in re2-ob re2-ss re2-tt; do
      tag="${m}__${d}"; K="output/kept_shift$S/$tag"
      if [ -f "$K/STATUS" ]; then echo "skip $S $tag"; continue; fi
      rm -rf "$K" output/results; mkdir -p output/results "$K"
      echo "=== $tag tdelta=$S $(date '+%F %T')"
      timeout 7200 python main.py --method "$m" --dataset "$d" --length 20 --tdelta "$S" > "logs_baselines/${tag}__shift$S.txt" 2>&1
      rc=$?
      mv output/results/*.json "$K/" 2>/dev/null
      echo "exit=$rc a4 tdelta=$S" > "$K/STATUS"
      echo "    exit=$rc results=$(ls "$K" | grep -c '\.json$')"
    done
  done
  python ~/rca/rcastudy/scripts/07_collect_rcaeval.py --kept "output/kept_shift$S" --ctx ~/rca/rcastudy/out/re2_shift$S
done
echo "=== amendment 4 part B finished $(date '+%F %T')"
