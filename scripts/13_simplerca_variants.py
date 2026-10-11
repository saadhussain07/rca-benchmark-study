"""Amendment 4 (exploratory): SimpleRCA-style heuristic, pre-registered form and
four variants, to show how far its accuracy rests on three implementation
choices. No model is called.

  V0  as pre-registered (baselines.simplerca): one alert per metric column;
      '-db' columns count for their owner; a column constant before the
      injection alerts on any change (sigma = 0 rule)
  V1  V0 without the sigma = 0 rule
  V2  V0 counting only the service's own columns ('-db' columns ignored)
  V3  at most one alert per signal type per service (metric, trace, log),
      the per-modality form of Fang et al.
  V4  V1 + V2 + V3

usage (from ~/rca/RCAEval):
  python ~/rca/rcastudy/scripts/13_simplerca_variants.py --root data --suite re2 --ctx ~/rca/rcastudy/out/re2
  python ... --suite re2 --ctx ~/rca/rcastudy/out/re2_shift120 --onset-shift 120
writes <ctx>/ranks_simplerca_variants.json  ({"simplerca:V0": {case_id: [services]}, ...})
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import baselines as B  # noqa: E402
from rcastudy import config as C  # noqa: E402
from rcastudy import data as D  # noqa: E402

VARIANTS = {"V0": dict(sd0=True, fold=True, cap=False),
            "V1": dict(sd0=False, fold=True, cap=False),
            "V2": dict(sd0=True, fold=False, cap=False),
            "V3": dict(sd0=True, fold=True, cap=True),
            "V4": dict(sd0=False, fold=False, cap=True)}


def signals(case, mdf, tdf, ldf, candidates, inj):
    """Per service: list of (metric column raw prefix, sd==0 flag) that alert,
    plus trace and log alerts. Same rules and windows as baselines.simplerca."""
    nb = mdf[(mdf["time"] >= inj - C.NORMAL_WINDOW_S) & (mdf["time"] < inj)]
    an = mdf[(mdf["time"] >= inj) & (mdf["time"] < inj + C.ANOMAL_WINDOW_S)]
    met = {s: [] for s in candidates}
    for col in mdf.columns:
        if col == "time" or "_" not in col:
            continue
        raw = col.split("_")[0]
        s = D.canonical(raw)
        if s not in met:
            continue
        mu, sd, a = nb[col].mean(), nb[col].std(), an[col].mean()
        if pd.notna(mu) and pd.notna(a) and pd.notna(sd):
            if sd > 0 and abs(a - mu) > B.SIMPLE_SIGMA * sd:
                met[s].append((raw, False))
            elif sd == 0 and a != mu:
                met[s].append((raw, True))
    tr = {s: 0 for s in candidates}
    if tdf is not None and not tdf.empty:
        own = D.owner_map(tdf["serviceName"].unique(), candidates)
        towner = tdf["serviceName"].astype(str).map(own)
        for s in candidates:
            sp = tdf[towner == s]
            b = sp[(sp["ts"] >= inj - C.NORMAL_WINDOW_S) & (sp["ts"] < inj)]["duration"]
            x = sp[(sp["ts"] >= inj) & (sp["ts"] < inj + C.ANOMAL_WINDOW_S)]["duration"]
            if len(b) and len(x) and b.quantile(0.95) > 0 and x.quantile(0.95) >= B.SIMPLE_LAT_MULT * b.quantile(0.95):
                tr[s] = 1
    lg = {s: 0 for s in candidates}
    if ldf is not None and not ldf.empty and "container_name" in ldf.columns:
        txt = ldf.get("message", pd.Series([""] * len(ldf))).astype(str).str.lower()
        err = txt.str.contains("error|fail|exception")
        own = D.owner_map(ldf["container_name"].unique(), candidates)
        lowner = ldf["container_name"].astype(str).map(own)
        for s in candidates:
            mine = (lowner == s) & err
            b = int((mine & (ldf["ts"] >= inj - C.NORMAL_WINDOW_S) & (ldf["ts"] < inj)).sum())
            x = int((mine & (ldf["ts"] >= inj) & (ldf["ts"] < inj + C.ANOMAL_WINDOW_S)).sum())
            if x >= B.SIMPLE_LOG_MIN and x >= B.SIMPLE_LOG_MULT * max(b, 1):
                lg[s] = 1
    return met, tr, lg


def score(met, tr, lg, sd0, fold, cap):
    out = {}
    for s in met:
        cols = [r for r, z in met[s] if (sd0 or not z) and (fold or r == s)]
        m = min(len(cols), 1) if cap else len(cols)
        out[s] = float(m + tr[s] + lg[s])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--suite", default="re2")
    ap.add_argument("--ctx", required=True)
    ap.add_argument("--onset-shift", type=int, default=0)
    a = ap.parse_args()
    cases = D.discover(a.root, a.suite)
    res = {f"simplerca:{v}": {} for v in VARIANTS}
    for i, case in enumerate(cases, 1):
        mdf, ldf, tdf = D.load_metrics(case), D.load_logs(case), D.load_traces(case)
        cands = D.candidates(mdf)
        met, tr, lg = signals(case, mdf, tdf, ldf, cands, case.inject_time + a.onset_shift)
        for v, kw in VARIANTS.items():
            # V0 uses the pre-registered tie-break tag, so it reproduces baselines.simplerca
            res[f"simplerca:{v}"][case.case_id] = B._rank_by(score(met, tr, lg, **kw), case.case_id, "simplerca")
        print(f"[{i}/{len(cases)}] {case.case_id}", flush=True)
    os.makedirs(a.ctx, exist_ok=True)
    with open(os.path.join(a.ctx, "ranks_simplerca_variants.json"), "w") as f:
        json.dump(res, f)
    print("wrote", os.path.join(a.ctx, "ranks_simplerca_variants.json"))


if __name__ == "__main__":
    main()
