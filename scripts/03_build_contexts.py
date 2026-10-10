"""Run the deployed detectors and context builder on every case of a suite,
and compute every non-LLM ranking. No model is called here.

Outputs (in --out):
  contexts.jsonl        one record per case: detector output, deployed context,
                        the four prompt variants' summaries, decoy assignment
  features_visible.csv  per-service features as the agent sees them
  features_all.csv      the same features without masking
  ranks_nonllm.json     {method: {case_id: [ranked services]}}
  build_log.txt         per-case timing and any failure

usage: python scripts/03_build_contexts.py --root data --suite re2 --out out/re2
"""
import argparse
import json
import os
import sys

# The deployed ContextBuilder orders AFFECTED SERVICES with list(set(...)),
# which depends on Python's string-hash seed. Fix the seed so the same case
# always yields the same text (PROTOCOL_V3.md A13).
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)
import time
import traceback

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import baselines as B  # noqa: E402
from rcastudy import config as C  # noqa: E402
from rcastudy import context as X  # noqa: E402
from rcastudy import data as D  # noqa: E402
from rcastudy import detectors as T  # noqa: E402


def process(case):
    mdf = D.load_metrics(case)
    ldf = D.load_logs(case)
    tdf = D.load_traces(case)
    warnings = []
    if ldf is not None and not D.ts_ok(ldf):
        warnings.append("log timestamps unusable")
    if tdf is not None and not D.ts_ok(tdf):
        warnings.append("trace timestamps unusable")
    det_services = D.detector_services(mdf)
    candidates = D.candidates(mdf)
    root = D.canonical(case.root_service)
    if root not in candidates:
        warnings.append(f"root {root} not among candidates")
    metric_res = T.metric_detector(mdf, det_services, case.inject_time)
    trace_res = T.trace_detector(tdf, det_services, case.inject_time)
    log_res = T.log_detector(ldf, det_services, case.inject_time)
    cycle_ts = case.inject_time + C.CYCLE_OFFSET_S
    ctx = X.build(metric_res, trace_res, log_res, cycle_ts)
    flagged = ctx["severity"] != "NORMAL"

    annotated = ctx["summary_for_llm"]
    stripped, n_notes = X.strip_notes(annotated)
    decoy_svc, decoy_tpl = X.decoy_assignment(case.case_id, candidates, root)
    summaries = {"annotated": annotated, "stripped": stripped,
                 "decoy": X.add_decoy(stripped, decoy_svc, decoy_tpl),
                 "placebo": X.add_placebo(stripped, decoy_svc)}

    # detector outputs kept beside the context for the feature tables only
    ctx_feat = dict(ctx)
    ctx_feat["_all_metrics"] = metric_res["all_metrics"]
    ctx_feat["_trace_analysis"] = trace_res["trace_analysis"]
    ctx_feat["_log_analysis"] = log_res["log_analysis"]
    vis = B.service_rows(ctx_feat, case, candidates, visible=True)
    allr = B.service_rows(ctx_feat, case, candidates, visible=False)
    ranks = {
        "detector_count": B.rank_detector_count(vis),
        "first_affected": B.rank_first_affected(ctx, candidates, case.case_id),
        "largest_anomaly": B.rank_largest_anomaly(allr),
        "simplerca": B.simplerca(case, mdf, tdf, ldf, candidates),
    }
    rec = {
        "case_id": case.case_id, "system": case.system, "fault": case.fault, "rep": case.rep,
        "gt": {"root_service": root, "fault": case.fault},
        "candidates": candidates, "detector_services": det_services,
        "build_failed": False, "warnings": warnings,
        "flagged": flagged, "severity": ctx["severity"], "n_notes": n_notes,
        "signals": {**ctx["total_anomalies"],
                    "if_flags": len(metric_res["anomalies"]),
                    "traces_available": trace_res["traces_available"],
                    "logs_available": log_res["logs_available"]},
        "summary": summaries,
        "decoy": {"service": decoy_svc, "template": decoy_tpl},
        "context": ctx,
    }
    return rec, vis, allr, ranks


def stub(case):
    """Record for a case the pipeline could not build: it stays in every
    denominator and is scored as chance (PROTOCOL_V3.md section 9)."""
    try:
        cands = D.candidates(D.load_metrics(case))
    except Exception:  # noqa: BLE001
        cands = []
    return {"case_id": case.case_id, "system": case.system, "fault": case.fault, "rep": case.rep,
            "gt": {"root_service": D.canonical(case.root_service), "fault": case.fault},
            "candidates": cands, "detector_services": [], "build_failed": True, "warnings": [],
            "flagged": False, "severity": None, "n_notes": 0, "signals": {}, "summary": {},
            "decoy": {"service": None, "template": None}, "context": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--suite", default="re2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", default=None, help="comma-separated case ids")
    ap.add_argument("--subset", default=None, help="file with one case id per line")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cases = D.discover(a.root, a.suite)
    if a.only:
        keep = set(a.only.split(","))
        cases = [c for c in cases if c.case_id in keep]
    if a.subset:
        keep = {l.strip() for l in open(a.subset) if l.strip()}
        cases = [c for c in cases if c.case_id in keep]
    if a.limit:
        cases = cases[: a.limit]
    print(f"{len(cases)} cases")
    vis_rows, all_rows = [], []
    ranks = {"detector_count": {}, "first_affected": {}, "largest_anomaly": {}, "simplerca": {}}
    with open(os.path.join(a.out, "contexts.jsonl"), "w", encoding="utf-8") as fo, \
            open(os.path.join(a.out, "build_log.txt"), "w") as flog:
        for i, c in enumerate(cases, 1):
            t0 = time.time()
            try:
                rec, vis, allr, rk = process(c)
            except Exception:  # noqa: BLE001
                flog.write(f"FAIL {c.case_id}\n{traceback.format_exc()}\n")
                print(f"[{i}/{len(cases)}] FAIL {c.case_id} (kept as a stub, scored as chance)")
                fo.write(json.dumps(stub(c), default=str) + "\n")
                continue
            for w in rec["warnings"]:
                flog.write(f"WARN {c.case_id}: {w}\n")
                print(f"  WARN {c.case_id}: {w}")
            fo.write(json.dumps(rec, default=str) + "\n")
            vis_rows += vis
            all_rows += allr
            for k, v in rk.items():
                ranks[k][c.case_id] = v
            msg = f"[{i}/{len(cases)}] {c.case_id} {time.time()-t0:.1f}s"
            flog.write(msg + "\n")
            print(msg)
    pd.DataFrame(vis_rows).to_csv(os.path.join(a.out, "features_visible.csv"), index=False)
    pd.DataFrame(all_rows).to_csv(os.path.join(a.out, "features_all.csv"), index=False)
    with open(os.path.join(a.out, "ranks_nonllm.json"), "w") as f:
        json.dump(ranks, f)
    print("done")


if __name__ == "__main__":
    main()
