#!/usr/bin/env bash
# Amendment 2 reruns of RCAEval baselines (PROTOCOL_V3_AMENDMENT_2.md).
# Run from ~/rca/RCAEval, env active, AFTER scripts/rcaeval_patch_a2.py and the
# PyRCA install, and only once run_rcaeval_baselines.sh has finished (both use
# output/results).
# The first-run folder of each rerun is moved to output/kept_pre_a2/ (kept,
# reported in the paper); the rerun goes to output/kept/<method>__<dataset>/.
# Resumable: a rerun whose STATUS already says "a2" is skipped.
set -u
RUNS="e_diagnosis:re2-ob e_diagnosis:re2-ss e_diagnosis:re2-tt
microcause:re2-ob microcause:re2-ss
mmbaro:re2-tt mmnsigma:re2-tt"
mkdir -p output/kept output/kept_pre_a2 logs_baselines
for r in $RUNS; do
  m=${r%%:*}; d=${r##*:}; tag="${m}__${d}"
  if grep -qs "a2" "output/kept/$tag/STATUS"; then echo "skip $tag (a2 done)"; continue; fi
  if [ -d "output/kept/$tag" ] && [ ! -d "output/kept_pre_a2/$tag" ]; then
    mv "output/kept/$tag" "output/kept_pre_a2/$tag"
  fi
  rm -rf "output/kept/$tag" output/results; mkdir -p output/results
  echo "=== $tag  $(date '+%F %T')"
  timeout 7200 python main.py --method "$m" --dataset "$d" --length 20 --report-chance > "logs_baselines/${tag}__a2.txt" 2>&1
  rc=$?
  mkdir -p "output/kept/$tag" && mv output/results/*.json "output/kept/$tag/" 2>/dev/null
  echo "exit=$rc a2" > "output/kept/$tag/STATUS"
  n_ok=$(ls "output/kept/$tag" | grep -c '\.json$' ); n_fail=$(ls "output/kept/$tag" | grep -c '_failed\.json$')
  echo "    exit=$rc  results=$((n_ok - n_fail))  failed_cases=$n_fail"
done
echo "=== a2 reruns finished $(date '+%F %T')"
