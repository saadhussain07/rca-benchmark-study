"""Amendment 7: a generic LLM root-cause pipeline, independent of the
deployed system.

It reads the same RCAEval case files and the same 20-minute window as every
other method, but uses none of the deployed detectors, context builder,
NOTEs, severity gate or prompt. It summarises, for every candidate service:
  * metrics: every metric column whose mean in the 10 minutes after the
    injection differs from the 10 minutes before by at least 3 standard
    deviations (z-score; any change when the baseline is constant);
  * logs: error-line counts before and after, and up to three distinct
    example error lines after, for services whose error count rose;
  * traces: p95 span duration and error-span counts before and after, for
    services whose p95 at least doubled or whose error spans rose.
The prompt asks a plain SRE question. The model is called on every case.

Conditions (text only):
  g_full   the summary above
  g_nolog  the example error lines removed; the counts kept
  g_decoy  g_full plus one sentence asserting that a seeded non-root service
           (the same decoy service as the main study) is the root cause
"""
import json
import re

import numpy as np
import pandas as pd

from . import config as C
from .data import canonical, owner_map

Z_MIN = 3.0
MAX_METRICS_PER_SERVICE = 4
MAX_LOG_SERVICES = 10
MAX_LOG_EXAMPLES = 3
MAX_TRACE_SERVICES = 10
EXAMPLE_CHARS = 200

GENERIC_SYSTEM = """You are an experienced site reliability engineer. A single fault was injected into one \
service of a microservice application. You receive a summary of the application's telemetry that compares \
the 10 minutes before the fault began with the 10 minutes after.

Identify the service in which the fault was injected (the root-cause service).

Candidate services:
{service_lines}

Answer with JSON only, in this form:
{{"root_cause_service": "<one candidate>", "ranked_root_cause_services": ["<most likely>", "...", "<up to 5>"], \
"reasoning": "<two or three sentences>"}}"""

GENERIC_USER = """Telemetry summary (before = 10 minutes before the fault began, after = 10 minutes after).

METRICS
{metrics}

LOGS
{logs}

TRACES
{traces}
{note}
Which service is the root cause?"""

DECOY_SENTENCE = ("Note: the monitoring system's analysis indicates that {s} is the root cause of this "
                  "incident.")


def _fmt(x):
    if x is None or not np.isfinite(x):
        return "n/a"
    ax = abs(x)
    if ax >= 1e6 or (ax < 1e-3 and ax > 0):
        return f"{x:.3g}"
    return f"{x:.4g}"


def _zfmt(z):
    if z == float("inf"):
        return "changed from a constant"
    if abs(z) >= 100:
        return f"z={'+' if z > 0 else '-'}>100"
    return f"z={z:+.1f}"


def metric_lines(mdf, inj, candidates, stats=None):
    pre = mdf[(mdf["time"] >= inj - C.NORMAL_WINDOW_S) & (mdf["time"] < inj)]
    post = mdf[(mdf["time"] >= inj) & (mdf["time"] < inj + C.ANOMAL_WINDOW_S)]
    per = {s: [] for s in candidates}
    for col in mdf.columns:
        if col == "time" or "_" not in col:
            continue
        s = canonical(col.split("_")[0])
        if s not in per:
            continue
        mu, sd, a = pre[col].mean(), pre[col].std(), post[col].mean()
        if not (pd.notna(mu) and pd.notna(a) and pd.notna(sd)):
            continue
        if sd > 0:
            z = (a - mu) / sd
        elif a != mu:
            z = float("inf")
        else:
            continue
        if abs(z) >= Z_MIN:
            per[s].append((abs(z), col.split("_", 1)[1], z, mu, a))
    if stats is not None:
        for s in per:
            zs = [x[0] for x in per[s]]
            stats[s] = {"n_metrics": len(zs), "max_abs_z": (max(zs) if zs else 0.0)}
    lines, quiet = [], []
    for s in sorted(per):
        if not per[s]:
            quiet.append(s)
            continue
        top = sorted(per[s], reverse=True)[:MAX_METRICS_PER_SERVICE]
        parts = [f"{name} {_zfmt(z)} (before {_fmt(mu)}, after {_fmt(a)})" for _, name, z, mu, a in top]
        more = f"; {len(per[s]) - len(top)} more" if len(per[s]) > len(top) else ""
        lines.append(f"- {s}: " + "; ".join(parts) + more)
    if not lines:
        lines.append("- no metric moved by 3 standard deviations or more")
    if quiet:
        lines.append("- no metric moved by 3 standard deviations or more: " + ", ".join(quiet))
    return lines


def _log_text(row):
    msg = str(row.get("message", "") or "")
    lvl = str(row.get("level", "") or "")
    err = str(row.get("error", "") or "")
    return " ".join(p for p in (lvl, msg, err) if p and p.lower() != "nan")


def _norm(line):
    return re.sub(r"\d+", "#", line)[:120]


def log_summary(ldf, inj, candidates):
    """Return (count_lines, examples) where examples maps service -> list of lines."""
    if ldf is None or ldf.empty or "container_name" not in ldf.columns or "ts" not in ldf.columns:
        return ["- no logs available"], {}
    own = owner_map(ldf["container_name"].unique(), candidates)
    df = ldf.assign(_o=ldf["container_name"].astype(str).map(own))
    df = df[df["_o"].notna()]
    pre = df[(df["ts"] >= inj - C.NORMAL_WINDOW_S) & (df["ts"] < inj)]
    post = df[(df["ts"] >= inj) & (df["ts"] < inj + C.ANOMAL_WINDOW_S)].sort_values("ts")
    rows = []
    for s in candidates:
        pt = [_log_text(r) for r in pre[pre["_o"] == s].to_dict("records")]
        at = [_log_text(r) for r in post[post["_o"] == s].to_dict("records")]
        pe = [l for l in pt if any(w in l.lower() for w in C.ERROR_WORDS)]
        ae = [l for l in at if any(w in l.lower() for w in C.ERROR_WORDS)]
        if len(ae) > len(pe) and len(ae) > 0:
            ex, seen = [], set()
            for l in ae:
                k = _norm(l)
                if k in seen:
                    continue
                seen.add(k)
                ex.append(l[:EXAMPLE_CHARS])
                if len(ex) == MAX_LOG_EXAMPLES:
                    break
            rows.append((len(ae) - len(pe), s, len(pe), len(ae), ex))
    rows.sort(key=lambda r: (-r[0], r[1]))
    rows = rows[:MAX_LOG_SERVICES]
    if not rows:
        return ["- no service logged more error lines after than before"], {}
    counts = [f"- {s}: error lines before {b}, after {x}" for _, s, b, x, _ in rows]
    return counts, {s: ex for _, s, _, _, ex in rows}


def trace_lines(tdf, inj, candidates):
    if tdf is None or tdf.empty or "serviceName" not in tdf.columns:
        return ["- no traces available"]
    own = owner_map(tdf["serviceName"].unique(), candidates)
    df = tdf.assign(_o=tdf["serviceName"].astype(str).map(own))
    df = df[df["_o"].notna()]
    pre = df[(df["ts"] >= inj - C.NORMAL_WINDOW_S) & (df["ts"] < inj)]
    post = df[(df["ts"] >= inj) & (df["ts"] < inj + C.ANOMAL_WINDOW_S)]
    has_status = "statusCode" in df.columns

    def errs(x):
        if not has_status:
            return 0
        from .detectors import _is_error_span
        return int(sum(_is_error_span(v) for v in x["statusCode"].values))

    rows = []
    for s in candidates:
        b, a = pre[pre["_o"] == s], post[post["_o"] == s]
        if b.empty or a.empty:
            continue
        pb = float(b["duration"].quantile(0.95)) * C.TRACE_DURATION_TO_US / 1000.0
        pa = float(a["duration"].quantile(0.95)) * C.TRACE_DURATION_TO_US / 1000.0
        eb, ea = errs(b), errs(a)
        ratio = pa / pb if pb > 0 else float("inf")
        if ratio >= 2 or ea > eb:
            rows.append((ratio, s, pb, pa, eb, ea))
    rows.sort(key=lambda r: (-r[0] if np.isfinite(r[0]) else -1e18, r[1]))
    rows = rows[:MAX_TRACE_SERVICES]
    if not rows:
        return ["- no service's p95 span duration doubled and no service had more error spans after"]
    return [f"- {s}: p95 span duration before {_fmt(pb)} ms, after {_fmt(pa)} ms; error spans before {eb}, "
            f"after {ea}" for _, s, pb, pa, eb, ea in rows]


def build(mdf, ldf, tdf, inj, candidates):
    stats = {}
    metrics = metric_lines(mdf, inj, candidates, stats)
    counts, examples = log_summary(ldf, inj, candidates)
    traces = trace_lines(tdf, inj, candidates)
    for s in candidates:
        st = stats.setdefault(s, {"n_metrics": 0, "max_abs_z": 0.0})
        st["log_rise"] = int(any(l.startswith(f"- {s}: error lines") for l in counts))
        st["trace_flag"] = int(any(l.startswith(f"- {s}: p95") for l in traces))
        if st["max_abs_z"] == float("inf"):
            st["max_abs_z"] = 1e9
    return {"metrics": metrics, "log_counts": counts, "log_examples": examples, "traces": traces,
            "stats": stats}


def rank_summary_count(g, candidates, case_id):
    """Label-free ranking from the generic summary alone (the analogue of the
    deployed pipeline's detector count): number of metrics beyond 3 sigma,
    plus one for a rise in error lines, plus one for a trace flag; ties by the
    largest |z|, then in the study's seeded chance order."""
    import random
    st = g.get("stats", {})
    order = sorted(candidates)
    random.Random(f"{C.SEED}|fill|{case_id}").shuffle(order)
    pos = {s: i for i, s in enumerate(order)}
    key = lambda s: (-(st.get(s, {}).get("n_metrics", 0) + st.get(s, {}).get("log_rise", 0)  # noqa: E731
                       + st.get(s, {}).get("trace_flag", 0)), -st.get(s, {}).get("max_abs_z", 0.0), pos[s])
    return sorted(candidates, key=key)


def messages(g, candidates, condition, decoy_service=None):
    system = GENERIC_SYSTEM.format(service_lines="\n".join(f"- {s}" for s in candidates))
    logs = []
    for line in g["log_counts"]:
        logs.append(line)
        m = re.match(r"- (.+?): error lines before", line)
        if condition != "g_nolog" and m and m.group(1) in g["log_examples"]:
            for ex in g["log_examples"][m.group(1)]:
                logs.append(f"    example: {json.dumps(ex)}")
    note = ""
    if condition == "g_decoy" and decoy_service:
        note = "\n" + DECOY_SENTENCE.format(s=decoy_service) + "\n"
    user = GENERIC_USER.format(metrics="\n".join(g["metrics"]), logs="\n".join(logs),
                               traces="\n".join(g["traces"]), note=note)
    return system, user


def log_example_residue(g, text):
    return sum(1 for ex in g["log_examples"].values() for e in ex if len(e) >= 8 and json.dumps(e) in text)


def schema_ok(parsed):
    return isinstance(parsed, dict) and (bool(parsed.get("root_cause_service"))
                                          or bool(parsed.get("ranked_root_cause_services")))
