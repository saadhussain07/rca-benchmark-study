"""Describe the format of an RCAEval suite without looking at any outcome.

Reads only (a) folder names, (b) column names, (c) value ranges in the NORMAL
window (before injection), and (d) the length of data available on each side
of the injection. It never runs a detector, a baseline or a model on the
anomalous window. Send the output file back for the protocol.

usage: python scripts/01_inspect.py --root data --suite re2 --out out/inspect_re2.txt
"""
import argparse
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import data as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--suite", default="re2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-system", type=int, default=3, help="cases per system to open")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    cases = D.discover(a.root, a.suite)
    lines = [f"suite={a.suite} root={a.root} cases={len(cases)}"]
    cnt = collections.Counter((c.system, c.fault) for c in cases)
    for k in sorted(cnt):
        lines.append(f"  {k[0]} {k[1]}: {cnt[k]}")
    # every case: does its metrics file load, and how many rows lack a time?
    lines.append("\n=== all cases: metric files")
    probs = 0
    for c in cases:
        try:
            m = D.load_metrics(c)
            n = m.attrs.get("rows_without_time", 0)
            pre = int((m["time"] < c.inject_time).sum())
            post = int((m["time"] >= c.inject_time).sum())
            if n or pre < 600 or post < 600:
                probs += 1
                lines.append(f"  {c.case_id}: rows_without_time={n} rows_before={pre} rows_after={post}  ({c.path})")
        except Exception as e:  # noqa: BLE001
            probs += 1
            lines.append(f"  {c.case_id}: UNREADABLE {type(e).__name__}: {e}  ({c.path})")
    lines.append(f"  cases with a note: {probs} of {len(cases)}")
    by_sys = collections.defaultdict(list)
    for c in cases:
        by_sys[c.system].append(c)
    unit = {"cpu_medians": [], "cpu_values_max": [], "mem_median": [], "dur_median": [], "steps": []}
    for sysname, cs in sorted(by_sys.items()):
        lines.append(f"\n=== system {sysname}: {len(cs)} cases")
        lines.append(f"  files in first case: {sorted(os.listdir(cs[0].path))}")
        pre, post = [], []
        for c in cs[: a.per_system]:
            try:
                m = D.load_metrics(c)
            except Exception as e:  # noqa: BLE001
                lines.append(f"  case {c.case_id}: METRICS UNREADABLE: {type(e).__name__}: {e}")
                continue
            if m.attrs.get("rows_without_time"):
                lines.append(f"  case {c.case_id}: {m.attrs['rows_without_time']} metric rows without a timestamp (dropped)")
            pre.append(int((m['time'] < c.inject_time).sum()))
            post.append(int((m['time'] >= c.inject_time).sum()))
            nb = m[m["time"] < c.inject_time]
            suffix = collections.Counter(col.split("_", 1)[1] for col in m.columns if "_" in col)
            svcs = D.services_from_metrics(m)
            dt = np.diff(m["time"].values)
            unit["steps"].append(float(np.median(dt)) if len(dt) else None)
            ccols = [col for col in m.columns if col.endswith("_cpu")]
            if ccols:
                unit["cpu_medians"] += [float(x) for x in nb[ccols].median().dropna().values]
                unit["cpu_values_max"].append(float(np.nanmax(nb[ccols].values)))
            mcols = [col for col in m.columns if col.endswith("_mem")]
            if mcols:
                unit["mem_median"].append(float(np.nanmedian(nb[mcols].values)))
            lines.append(f"  case {c.case_id}: services={len(svcs)} metric_cols={m.shape[1]-1} "
                         f"median_step_s={np.median(dt) if len(dt) else None}")
            lines.append(f"    services: {svcs}")
            lines.append(f"    metric suffixes: {dict(suffix)}")
            for kind in ("cpu", "mem"):
                cols = [col for col in m.columns if col.endswith('_' + kind)]
                if cols:
                    v = nb[cols].stack()
                    lines.append(f"    normal-window {kind}: n={len(v)} min={v.min():.4g} "
                                 f"p50={v.median():.4g} p95={v.quantile(.95):.4g} max={v.max():.4g}")
            lg = D.load_logs(c)
            if lg is not None:
                lines.append(f"    logs columns: {list(lg.columns)} rows={len(lg)}")
                nl = lg[lg["ts"] < c.inject_time] if "ts" in lg.columns else lg.head(0)
                if "container_name" in lg.columns:
                    lines.append(f"    log container names: {sorted(map(str, lg['container_name'].unique()))[:40]}")
                if "level" in nl.columns:
                    lines.append(f"    normal-window log levels: {nl['level'].value_counts().head(8).to_dict()}")
                lines.append(f"    log ts range vs inject (s): "
                             f"{(lg['ts'].min()-c.inject_time):.0f} .. {(lg['ts'].max()-c.inject_time):.0f}")
            else:
                lines.append("    logs: none")
            tr = D.load_traces(c)
            if tr is not None:
                lines.append(f"    traces columns: {list(tr.columns)} rows={len(tr)}")
                nt = tr[tr["ts"] < c.inject_time]
                if "statusCode" in nt.columns:
                    lines.append(f"    normal-window statusCode: {nt['statusCode'].value_counts(dropna=False).head(8).to_dict()}")
                lines.append(f"    trace service names: {sorted(map(str, tr['serviceName'].unique()))[:40]}")
                lines.append(f"    normal-window span duration (raw unit) p50={nt['duration'].median()} p99={nt['duration'].quantile(.99)}")
                unit["dur_median"].append(float(nt["duration"].median()))
            else:
                lines.append("    traces: none")
        lines.append(f"  metric rows before injection (first cases): {pre}; after: {post}")
    # ---- unit checks (PROTOCOL_V3.md section 8 rules)
    lines.append("\n=== unit checks")
    steps = [x for x in unit["steps"] if x is not None]
    lines.append(f"  metric step: {sorted(set(steps))}  -> rule: must be 1.0 s")
    cm = np.array(unit["cpu_medians"])
    if len(cm):
        share_gt1 = float((cm > 1.0).mean())
        lines.append(f"  CPU per-service normal medians: n={len(cm)} p50={np.median(cm):.4g} p95={np.percentile(cm,95):.4g} "
                     f"share>1.0={share_gt1:.2f} max value={max(unit['cpu_values_max']):.4g}")
        if np.percentile(cm, 95) > 1.0 and max(unit["cpu_values_max"]) <= 800:
            sug = "percent of one core -> CPU_TO_CORES = 0.01"
        elif np.percentile(cm, 95) <= 4.0:
            sug = "cores -> CPU_TO_CORES = 1.0"
        else:
            sug = "ambiguous -> CPU_TO_CORES = None (relative floor only)"
        lines.append(f"  CPU rule suggests: {sug}")
    if unit["mem_median"]:
        mm = float(np.median(unit["mem_median"]))
        lines.append(f"  memory normal median={mm:.4g} -> {'bytes (as assumed)' if mm > 1e5 else 'NOT bytes: set MEM_BYTES_PER_MB = 1'}")
    if unit["dur_median"]:
        dm = float(np.median(unit["dur_median"]))
        verdict = ("microseconds (as assumed)" if 10 <= dm <= 1e7 else
                   "nanoseconds: set TRACE_DURATION_TO_US = 0.001" if dm > 1e7 else "unclear")
        lines.append(f"  span duration median={dm:.4g} -> {verdict}")
    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
