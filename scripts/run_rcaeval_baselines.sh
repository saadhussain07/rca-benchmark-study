#!/usr/bin/env bash
# Run the pre-registered RCAEval baselines on RE2 and keep each method's
# per-case rankings. Run from inside the RCAEval folder, in its Python 3.12
# environment:   bash ../rcastudy/scripts/run_rcaeval_baselines.sh
# main.py scores every file in output/results, so the folder is emptied before
# each run and its contents moved to output/kept/<method>__<dataset>/ after.
set -u
PRIMARY="nsigma baro circa e_diagnosis microcause mmnsigma mmbaro mmcirca"
SECONDARY="${SECONDARY:-tracerca microrank causalrca}"
DATASETS="re2-ob re2-ss re2-tt"
mkdir -p output/kept logs_baselines
for m in $PRIMARY $SECONDARY; do
  for d in $DATASETS; do
    tag="${m}__${d}"
    if [ -d "output/kept/$tag" ]; then echo "skip $tag"; continue; fi
    rm -rf output/results; mkdir -p output/results
    echo "=== $tag  $(date '+%F %T')"
    # 2-hour limit per method and system (PROTOCOL_V3.md section 6)
    timeout 7200 python main.py --method "$m" --dataset "$d" --length 20 --report-chance > "logs_baselines/$tag.txt" 2>&1
    rc=$?
    # keep whatever finished, even on failure or timeout
    mkdir -p "output/kept/$tag" && mv output/results/*.json "output/kept/$tag/" 2>/dev/null
    echo "exit=$rc" > "output/kept/$tag/STATUS"
    if [ $rc -eq 0 ]; then tail -n 12 "logs_baselines/$tag.txt"
    elif [ $rc -eq 124 ]; then echo "TIMEOUT $tag (partial results kept)"
    else echo "FAILED $tag rc=$rc (partial results kept; see logs_baselines/$tag.txt)"; fi
  done
done
