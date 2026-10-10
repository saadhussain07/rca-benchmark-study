"""Offline ports of the deployed detectors.

Each function returns a dict in the same schema the live collector returned
(metric_collector.run(), trace_analyser.run(), log_parser.run()), so the
deployed ContextBuilder can consume it unchanged. Differences from the live
code are only those forced by offline data and are listed in PROTOCOL_V3.md
section 4 (A1-A14).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from . import config as C
from .data import owner_map


# ====================================================================== metrics
def _col(df, service, kind):
    """Find the CPU or memory column for a service."""
    name = f"{service}_{kind}"
    return name if name in df.columns else None


def _resample(series_df, start, end):
    """Mean over 30-s steps in [start, end), the analogue of a Prometheus
    range query with step=30s."""
    w = series_df[(series_df["time"] >= start) & (series_df["time"] < end)]
    if w.empty:
        return w
    bins = ((w["time"] - start) // C.RESAMPLE_STEP_S).astype(int)
    return w.groupby(bins).mean(numeric_only=True)


def metric_detector(mdf, services, inject_time):
    """Fit one Isolation Forest per service on the normal window and score the
    cycle at inject_time + CYCLE_OFFSET_S."""
    t_cycle = inject_time + C.CYCLE_OFFSET_S
    base_start, base_end = inject_time - C.NORMAL_WINDOW_S, inject_time
    look_start = t_cycle - C.METRIC_LOOKBACK_S

    all_metrics, anomalies = [], []
    for svc in services:
        cpu_c, mem_c = _col(mdf, svc, "cpu"), _col(mdf, svc, "mem")
        m = {"service": svc, "pod_age_seconds": None, "recently_restarted": False,
             "cpu_pct_of_limit": None, "cpu_limit_cores": None,
             "memory_pct_of_limit": None, "memory_limit_mb": None,
             "error_rate": C.ERROR_RATE_CONSTANT}
        if cpu_c is None:
            m.update({"avg_cpu": 0.0, "max_cpu": 0.0, "cpu_std": 0.0, "memory_mb": 0.0,
                      "metrics_present": False, "anomaly_score": None, "is_anomaly": False,
                      "scoring_status": "NO_CPU_COLUMN", "cpu_vs_baseline_ratio": None,
                      "memory_vs_baseline_ratio": None})
            all_metrics.append(m)
            continue
        cols = ["time", cpu_c] + ([mem_c] if mem_c else [])
        sub = mdf[cols].copy()
        scale = C.CPU_TO_CORES or 1.0
        sub[cpu_c] = sub[cpu_c] * scale
        if mem_c:
            sub[mem_c] = sub[mem_c] / C.MEM_BYTES_PER_MB

        # ---- per-cycle values (collect_all_metrics)
        look = _resample(sub, look_start, t_cycle)
        cpu_vals = look[cpu_c].dropna().values if not look.empty else np.array([])
        if len(cpu_vals):
            avg_cpu, max_cpu, cpu_std = float(np.mean(cpu_vals)), float(np.max(cpu_vals)), float(np.std(cpu_vals))
        else:
            avg_cpu = max_cpu = cpu_std = 0.0
        mem_now = 0.0
        if mem_c:
            before = sub[(sub["time"] < t_cycle) & sub[mem_c].notna()]
            if len(before):
                mem_now = float(before[mem_c].iloc[-1])
        m.update({"avg_cpu": round(avg_cpu, 4), "max_cpu": round(max_cpu, 4),
                  "cpu_std": round(cpu_std, 4), "memory_mb": round(mem_now, 2),
                  "metrics_present": bool(len(cpu_vals))})

        # ---- baseline fit (fit_baseline): the samples the range queries
        # return (no filling), truncated to equal length.
        base = _resample(sub, base_start, base_end)
        bcpu = base[cpu_c].dropna().values if not base.empty else np.array([])
        if mem_c:
            bmem = base[mem_c].dropna().values if not base.empty else np.array([])
        else:
            # A14: no memory series -> memory feature 0, so CPU is still scored
            bmem = np.zeros(len(bcpu))
        n = min(len(bcpu), len(bmem))
        if n < C.MIN_BASELINE_SAMPLES:
            m.update({"anomaly_score": None, "is_anomaly": False,
                      "scoring_status": "NO_BASELINE_MODEL",
                      "cpu_vs_baseline_ratio": None, "memory_vs_baseline_ratio": None})
            all_metrics.append(m)
            continue
        bcpu, bmem = bcpu[:n], bmem[:n]
        # verbatim from metric_collector.fit_baseline (np.std, ddof=0)
        roll = np.array([np.std(bcpu[max(0, i - (C.ROLLING_STD_SAMPLES - 1)):i + 1])
                         for i in range(len(bcpu))])
        X = np.column_stack([bcpu, roll, bmem, np.full(n, C.ERROR_RATE_CONSTANT)])
        model = IsolationForest(contamination=C.IF_CONTAMINATION, random_state=C.IF_RANDOM_STATE)
        model.fit(X)
        thr = float(np.percentile(-model.score_samples(X), C.THRESHOLD_PERCENTILE))
        base_cpu_mean, base_mem_mean = float(np.mean(bcpu)), float(np.mean(bmem))
        base_p95 = float(np.percentile(bcpu, 95))

        # relative fields (collect_all_metrics)
        m["cpu_vs_baseline_ratio"] = round(avg_cpu / base_cpu_mean, 1) if base_cpu_mean > 0 else None
        m["memory_vs_baseline_ratio"] = (round(m["memory_mb"] / base_mem_mean, 2)
                                         if (mem_c and base_mem_mean > 0) else None)

        # ---- scoring (score_against_baseline)
        x = np.array([[m["avg_cpu"], m["cpu_std"], m["memory_mb"], m["error_rate"]]])
        raw = float(-model.score_samples(x)[0])
        m["anomaly_score"] = round(raw / thr if thr > 0 else raw, 3)
        abs_floor = C.MIN_MEANINGFUL_CPU_CORES if C.CPU_TO_CORES else 0.0
        floor = max(abs_floor, base_p95 * C.CPU_FLOOR_P95_MULT)
        crosses, meets = raw > thr, m["avg_cpu"] >= floor
        m["is_anomaly"] = bool(crosses and meets)
        m["suppressed_low_cpu_noise"] = bool(crosses and not meets)
        m["effective_cpu_floor"] = round(floor, 5)
        m["scoring_status"] = "OK"
        all_metrics.append(m)
        if m["is_anomaly"]:
            anomalies.append(m)
    return {"total_services": len(all_metrics), "anomaly_count": len(anomalies),
            "all_metrics": all_metrics, "anomalies": anomalies}


# ======================================================================= traces
def _is_error_span(code):
    """Jaeger `error` tag analogue (A8). RCAEval's statusCode mixes gRPC codes
    (0 = OK, 1-16 = error) and HTTP codes (>= 100). A span is an error when it
    carries a non-OK gRPC code or an HTTP code of 500 or more; empty = no error."""
    if code is None or (isinstance(code, float) and np.isnan(code)):
        return False
    try:
        c = float(code)
    except (TypeError, ValueError):
        return str(code).upper() in {"ERROR", "STATUS_CODE_ERROR"}
    if np.isnan(c):
        return False
    return (1 <= c <= 16) or c >= 500


def trace_detector(tdf, services, inject_time):
    t_cycle = inject_time + C.CYCLE_OFFSET_S
    results, anomalies = [], []
    empty = {"trace_count": 0, "avg_latency_ms": 0, "p99_latency_ms": 0, "max_latency_ms": 0,
             "error_count": 0, "error_rate": 0.0, "slowest_operation": None,
             "is_anomaly": False, "anomaly_reason": None}
    if tdf is None or tdf.empty:
        for svc in services:
            results.append({"service": svc, **empty})
        return {"traces_available": False, "trace_analysis": results, "anomalies": anomalies}

    own = owner_map(tdf["serviceName"].unique(), services)
    full = tdf[tdf["ts"] < t_cycle]  # spans that exist at query time
    full = full.assign(_owner=full["serviceName"].astype(str).map(own))
    w = full[(full["ts"] >= t_cycle - C.TRACE_LOOKBACK_S) & (full["ts"] < t_cycle)]
    for svc in services:
        # Jaeger returns up to `limit` traces in which the service appears,
        # most recent first, with all of their spans.
        mine = w[w["_owner"] == svc]
        if mine.empty:
            results.append({"service": svc, **empty})
            continue
        last = mine.groupby("traceID")["ts"].max().sort_values(ascending=False)
        ids = set(last.index[: C.TRACE_LIMIT])
        # Jaeger returns whole traces, including spans outside the window
        spans = full[full["traceID"].isin(ids)]
        d_ms = (spans["duration"] * C.TRACE_DURATION_TO_US / 1000.0).dropna().sort_values().values
        if len(d_ms) == 0:
            results.append({"service": svc, **empty, "trace_count": len(ids)})
            continue
        status = spans["statusCode"] if "statusCode" in spans.columns else pd.Series([np.nan] * len(spans))
        err = int(sum(_is_error_span(v) for v in status.values))
        total = len(d_ms)
        p99 = float(d_ms[min(int(total * 0.99), total - 1)])
        er = err / total
        ops = spans.assign(d=spans["duration"] * C.TRACE_DURATION_TO_US / 1000.0).groupby("operationName")["d"].mean()
        r = {"service": svc, "trace_count": len(ids), "avg_latency_ms": round(float(d_ms.mean()), 2),
             "p99_latency_ms": round(p99, 2), "max_latency_ms": round(float(d_ms.max()), 2),
             "error_count": err, "error_rate": round(er, 4),
             "slowest_operation": (str(ops.idxmax()) if len(ops) else None),
             "is_anomaly": False, "anomaly_reason": None}
        if p99 > C.LATENCY_THRESHOLD_MS:
            r["is_anomaly"] = True
            r["anomaly_reason"] = f"p99 latency {p99:.0f}ms exceeds threshold {C.LATENCY_THRESHOLD_MS}ms"
        elif er > C.ERROR_RATE_THRESHOLD:
            r["is_anomaly"] = True
            r["anomaly_reason"] = f"Error rate {er:.1%} exceeds threshold {C.ERROR_RATE_THRESHOLD:.1%}"
        results.append(r)
        if r["is_anomaly"]:
            anomalies.append(r)
    return {"traces_available": True, "trace_analysis": results, "anomalies": anomalies}


# ========================================================================= logs
def _log_text(row):
    msg = str(row.get("message", "") or "")
    lvl = str(row.get("level", "") or "")
    err = str(row.get("error", "") or "")
    parts = [p for p in (lvl, msg, err) if p and p.lower() != "nan"]
    return " ".join(parts)


def _simple_patterns(lines):
    """log_parser.extract_patterns_simple, verbatim logic."""
    patterns = {}
    for log in lines:
        low = log.lower()
        if "error" in low:
            k = "ERROR pattern"
        elif "warn" in low:
            k = "WARN pattern"
        elif "exception" in low:
            k = "EXCEPTION pattern"
        elif "timeout" in low:
            k = "TIMEOUT pattern"
        elif "refused" in low:
            k = "CONNECTION REFUSED pattern"
        elif "failed" in low:
            k = "FAILED pattern"
        else:
            k = "OTHER"
        patterns[k] = patterns.get(k, 0) + 1
    return patterns


def _patterns(miner, lines, err):
    """log_parser: Drain3 on error lines if there are any, else the simple
    parser on all lines."""
    if err:
        out = {}
        for l in err:
            r = miner.add_log_message(l)
            if r:
                out[r["template_mined"]] = out.get(r["template_mined"], 0) + 1
        return out
    return _simple_patterns(lines)


def _new_miner():
    from drain3 import TemplateMiner
    from drain3.template_miner_config import TemplateMinerConfig
    cfg = TemplateMinerConfig()
    cfg.profiling_enabled = False
    return TemplateMiner(config=cfg)


def _service_logs(ldf, svc, start, end):
    w = ldf[(ldf["ts"] >= start) & (ldf["ts"] < end)]
    w = w[w["_owner"] == svc]
    # Loki returns the most recent `limit` lines (direction=backward).
    w = w.sort_values("ts").tail(C.LOG_LIMIT)
    return [_log_text(r) for r in w.to_dict("records")]


def _errors(lines):
    err, warn = [], []
    for l in lines:
        low = l.lower()
        if any(wd in low for wd in C.ERROR_WORDS):
            err.append(l)
        elif "warn" in low:
            warn.append(l)
    return err, warn


def log_detector(ldf, services, inject_time, chronic_filter=False):
    """chronic_filter=False is the frozen, deployed behaviour. True is the
    exploratory baseline-aware variant (PROTOCOL_V3_AMENDMENT_1.md, E3): an
    error-count alarm needs more than twice the errors of the same-length
    window just before injection, and a dependency hint is dropped if it
    already appeared in that window."""
    t_cycle = inject_time + C.CYCLE_OFFSET_S
    results, anomalies = [], []
    if ldf is None or ldf.empty or "container_name" not in ldf.columns:
        for svc in services:
            results.append({"service": svc, "total_logs": 0, "error_count": 0, "warn_count": 0,
                            "top_patterns": [], "new_patterns": [], "dependency_hints": [],
                            "sample_error_log": None, "is_anomaly": False, "anomaly_reasons": []})
        return {"logs_available": False, "log_analysis": results, "anomalies": anomalies}

    own = owner_map(ldf["container_name"].unique(), services)
    ldf = ldf.assign(_owner=ldf["container_name"].astype(str).map(own))
    miner = _new_miner()
    seen = set()
    # Prime the miner and the seen-pattern set with the normal window, the
    # offline analogue of the patterns a long-running process has already
    # seen before the fault (log_parser.seen_patterns).
    for svc in services:
        lines = _service_logs(ldf, svc, inject_time - C.NORMAL_WINDOW_S, inject_time)
        err, _ = _errors(lines)
        seen.update(_patterns(miner, lines, err))

    base_err, base_hints = {}, {}
    if chronic_filter:
        for svc in services:
            bl = _service_logs(ldf, svc, inject_time - C.LOG_LOOKBACK_S, inject_time)
            be, _ = _errors(bl)
            base_err[svc] = len(be)
            base_hints[svc] = {dep for l in be for dep, kws in C.DEPENDENCY_KEYWORDS.items()
                               if any(k in l.lower() for k in kws)}

    for svc in services:
        lines = _service_logs(ldf, svc, t_cycle - C.LOG_LOOKBACK_S, t_cycle)
        err, warn = _errors(lines)
        hints = set()
        for l in err:
            low = l.lower()
            for dep, kws in C.DEPENDENCY_KEYWORDS.items():
                if any(k in low for k in kws):
                    hints.add(dep)
        if chronic_filter:
            hints -= base_hints.get(svc, set())
        patterns = _patterns(miner, lines, err)
        reasons, new = [], []
        chronic_ok = (not chronic_filter) or len(err) > 2 * base_err.get(svc, 0)
        if len(err) > C.LOG_ERROR_THRESHOLD and chronic_ok:
            reasons.append(f"High error count: {len(err)} errors in last 5 minutes")
        if hints:
            reasons.append(f"Error logs mention possible failed dependency: {', '.join(sorted(hints))}")
        for p in patterns:
            if p not in seen and p != "OTHER":
                new.append(p)
                reasons.append(f"New log pattern detected: {p}")
            seen.add(p)
        top = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        r = {"service": svc, "total_logs": len(lines), "error_count": len(err),
             "warn_count": len(warn), "top_patterns": [{"pattern": p, "count": c} for p, c in top],
             "new_patterns": new, "dependency_hints": sorted(hints),
             "sample_error_log": err[0][:300] if err else None,
             "is_anomaly": bool(reasons), "anomaly_reasons": reasons}
        results.append(r)
        if r["is_anomaly"]:
            anomalies.append(r)
    return {"logs_available": True, "log_analysis": results, "anomalies": anomalies}
