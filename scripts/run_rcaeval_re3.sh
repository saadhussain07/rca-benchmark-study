#!/usr/bin/env bash
# Amendment 3 (B2): the 5 single-source primary RCAEval baselines on RE3.
# Run from ~/rca/RCAEval, env active, after run_rcaeval_a2.sh has finished and
# scripts/rcaeval_patch_a3.py (P4) has been applied. Resumable.
set -u
# mmnsigma, mmbaro, mmcirca are not run: RE3 has no logts.csv / tracets_*.csv, which main.py
# reads for them before its per-case try block (PROTOCOL_V3_AMENDMENT_3.md B2).
PRIMARY="nsigma baro e_diagnosis circa microcause"
DATASETS="re3-ob re3-ss re3-tt"
mkdir -p output/kept logs_baselines
for m in $PRIMARY; do
  for d in $DATASETS; do
    tag="${m}__${d}"
    if [ -f "output/kept/$tag/STATUS" ]; then echo "skip $tag"; continue; fi
    rm -rf "output/kept/$tag" output/results; mkdir -p output/results
    echo "=== $tag  $(date '+%F %T')"
    timeout 7200 python main.py --method "$m" --dataset "$d" --length 20 --report-chance > "logs_baselines/$tag.txt" 2>&1
    rc=$?
    mkdir -p "output/kept/$tag" && mv output/results/*.json "output/kept/$tag/" 2>/dev/null
    echo "exit=$rc a3" > "output/kept/$tag/STATUS"
    n_all=$(ls "output/kept/$tag" | grep -c '\.json$'); n_fail=$(ls "output/kept/$tag" | grep -c '_failed\.json$')
    echo "    exit=$rc  results=$((n_all - n_fail))  failed_cases=$n_fail"
  done
done
echo "=== RE3 baselines finished $(date '+%F %T')"
