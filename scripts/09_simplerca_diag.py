"""Exploratory diagnostic (post hoc, not part of the frozen analysis): why does
the SimpleRCA-style heuristic score far above the value Fang et al. publish
for RE2-SS? Recomputes the per-service alert counts and reports

  * ties at the top (where the seeded tie-break decides the answer),
  * the root's alert count against the best other service,
  * which metric suffixes alert for the root (does any column encode the
    injected fault itself rather than its effect?),
  * accuracy when ties are broken by a different seed.

usage (from ~/rca/RCAEval):
  python ~/rca/rcastudy/scripts/09_simplerca_diag.py --root data --ctx ~/rca/rcastudy/out/re2
writes <ctx>/simplerca_diag.txt
"""
import argparse
import collections
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import baselines as B  # noqa: E402
from rcastudy import config as C  # noqa: E402
from rcastudy import data as D  # noqa: E402


def alert_detail(case, mdf, tdf, ldf, candidates):
    """Same rules as baselines.simplerca, but returns counts and the alerting
    metric suffixes per service."""
    inj = case.inject_time
    nb = mdf[(mdf["time"] >= inj - C.NORMAL_WINDOW_S) & (mdf["time"] < inj)]
    an = mdf[(mdf["time"] >= inj) & (mdf["time"] < inj + C.ANOMAL_WINDOW_S)]
    alerts = {s: 0 for s in candidates}
    why = {s: [] for s in candidates}
    for col in mdf.columns:
        if col == "time" or "_" not in col:
            continue
        s = D.canonical(col.split("_")[0])
        if s not in alerts:
            continue
        mu, sd, a = nb[col].mean(), nb[col].std(), an[col].mean()
        if pd.notna(mu) and pd.notna(a) and pd.notna(sd):
            if (sd > 0 and abs(a - mu) > B.SIMPLE_SIGMA * sd) or (sd == 0 and a != mu):
                alerts[s] += 1
                why[s].append("metric:" + col.split("_", 1)[1] + ("(sd=0)" if sd == 0 else ""))
    if tdf is not None and not tdf.empty:
        own = D.owner_map(tdf["serviceName"].unique(), candidates)
        towner = tdf["serviceName"].astype(str).map(own)
        for s in candidates:
            sp = tdf[towner == s]
            b = sp[(sp["ts"] >= inj - C.NORMAL_WINDOW_S) & (sp["ts"] < inj)]["duration"]
            x = sp[(sp["ts"] >= inj) & (sp["ts"] < inj + C.ANOMAL_WINDOW_S)]["duration"]
            if len(b) and len(x) and b.quantile(0.95) > 0 and x.quantile(0.95) >= B.SIMPLE_LAT_MULT * b.quantile(0.95):
                alerts[s] += 1
                why[s].append("trace:p95x3")
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
                alerts[s] += 1
                why[s].append("log:errors")
    return alerts, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--ctx", required=True)
    a = ap.parse_args()
    cases = D.discover(a.root, "re2")
    out, rows = [], []
    root_suffix = collections.Counter()
    for i, case in enumerate(cases, 1):
        mdf, ldf, tdf = D.load_metrics(case), D.load_logs(case), D.load_traces(case)
        cands = D.candidates(mdf)
        root = D.canonical(case.root_service)
        alerts, why = alert_detail(case, mdf, tdf, ldf, cands)
        top = max(alerts.values())
        winners = [s for s, v in alerts.items() if v == top]
        other = max([v for s, v in alerts.items() if s != root] or [0])
        rows.append({"case": case.case_id, "system": case.system, "fault": case.fault,
                     "root_alerts": alerts.get(root, 0), "best_other": other,
                     "n_top": len(winners), "root_in_top": root in winners, "n_candidates": len(cands)})
        for w in why.get(root, []):
            root_suffix[(case.system, case.fault, w)] += 1
        print(f"[{i}/{len(cases)}] {case.case_id}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(a.ctx, "simplerca_diag.csv"), index=False)
    out.append("=== root strictly ahead / tied at top / behind, by system")
    for s, g in df.groupby("system"):
        ahead = int(((g.root_alerts > g.best_other)).sum())
        tied = int(((g.root_alerts == g.best_other) & (g.root_alerts > 0)).sum())
        behind = int((g.root_alerts < g.best_other).sum())
        zero = int(((g.root_alerts == 0) & (g.best_other == 0)).sum())
        out.append(f"  {s}: ahead {ahead}, tied {tied}, behind {behind}, all-zero {zero}  (n={len(g)}, "
                   f"median candidates {int(g.n_candidates.median())})")
    out.append("\n=== expected AC@1 if every tie at the top were broken uniformly at random")
    exp = df.apply(lambda r: (1.0 / r.n_top) if r.root_in_top else 0.0, axis=1)
    for s, g in df.assign(e=exp).groupby("system"):
        out.append(f"  {s}: {g.e.mean():.3f}")
    out.append(f"  all: {exp.mean():.3f}")
    out.append("\n=== alert sources for the root service (count of cases), by system and fault")
    for (s, f, w), n in sorted(root_suffix.items()):
        out.append(f"  {s} {f:7s} {w:40s} {n}")
    txt = "\n".join(out)
    with open(os.path.join(a.ctx, "simplerca_diag.txt"), "w") as fh:
        fh.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
