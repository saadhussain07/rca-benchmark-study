"""Amendment 7: build the generic pipeline's summaries (rcastudy/generic.py)
for every case of a suite. No model is called, and none of the deployed
detectors or context builder is used.

usage (from the RCAEval folder, as 03_build_contexts.py):
  python ~/rca/rcastudy/scripts/18_generic_contexts.py --root data --suite re3 --out ~/rca/rcastudy/out/re3_generic
writes <out>/contexts.jsonl and <out>/build_log.txt
"""
import argparse
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import context as X  # noqa: E402
from rcastudy import data as D  # noqa: E402
from rcastudy import generic as G  # noqa: E402


def record(case):
    mdf = D.load_metrics(case)
    ldf = D.load_logs(case)
    tdf = D.load_traces(case)
    cands = D.candidates(mdf)
    root = D.canonical(case.root_service)
    g = G.build(mdf, ldf, tdf, case.inject_time, cands)
    decoy_svc, _ = X.decoy_assignment(case.case_id, cands, root)
    return {"case_id": case.case_id, "system": case.system, "fault": case.fault, "rep": case.rep,
            "gt": {"root_service": root, "fault": case.fault}, "candidates": cands,
            "detector_services": [], "build_failed": False, "warnings": [] if root in cands else
            [f"root {root} not among candidates"], "flagged": True, "n_notes": 0,
            "decoy": {"service": decoy_svc, "template": "generic"}, "generic": g, "context": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cases = D.discover(a.root, a.suite)[: a.limit]
    n_fail = 0
    with open(os.path.join(a.out, "contexts.jsonl"), "w", encoding="utf-8") as fo, \
            open(os.path.join(a.out, "build_log.txt"), "w") as lg:
        for i, case in enumerate(cases, 1):
            t0 = time.time()
            try:
                rec = record(case)
            except Exception as e:  # noqa: BLE001  (a failed case is scored as chance)
                n_fail += 1
                lg.write(f"{case.case_id} FAILED {type(e).__name__}: {e}\n{traceback.format_exc()}\n")
                try:
                    cands = D.candidates(D.load_metrics(case))
                except Exception:  # noqa: BLE001
                    cands = []
                rec = {"case_id": case.case_id, "system": case.system, "fault": case.fault, "rep": case.rep,
                       "gt": {"root_service": D.canonical(case.root_service), "fault": case.fault},
                       "candidates": cands, "detector_services": [], "build_failed": True, "warnings": [],
                       "flagged": False, "n_notes": 0, "decoy": {"service": None, "template": None},
                       "generic": None, "context": None}
            fo.write(json.dumps(rec) + "\n")
            lg.write(f"{case.case_id} {time.time() - t0:.1f}s\n")
            print(f"[{i}/{len(cases)}] {case.case_id}", flush=True)
    print(f"built {len(cases)} cases, {n_fail} failed -> {a.out}")


if __name__ == "__main__":
    main()
