"""Non-LLM rankers that use the same detector output as the agent, plus a
SimpleRCA-style heuristic on the raw telemetry.

  detector_count   : services ranked by number of signals that flagged them,
                     ties by the Isolation Forest score ratio as shown in the
                     prompt (0 for unflagged services), then seeded order.
  first_affected   : the order of the prompt's AFFECTED SERVICES line.
  largest_anomaly  : services ranked by Isolation Forest score ratio alone.
  lr_visible / rf_visible : classifiers on the per-service features the
                     agent sees (values of unflagged services are masked,
                     as they are absent from the prompt).
  lr_all           : logistic regression on the same features, unmasked.
  simplerca        : 3-sigma / 3x-latency / error-keyword alert counting on raw
                     telemetry, after Fang et al. (FSE 2026); our
                     reimplementation, thresholds in PROTOCOL_V3.md 5.5.
"""
import random

import numpy as np
import pandas as pd

from . import config as C
from .data import canonical, owner_map

VISIBLE_FEATURES = [
    "metric_flag", "if_score", "cpu_ratio", "mem_ratio", "mem_trigger",
    "trace_flag", "p99_ms", "trace_err_rate",
    "log_flag", "log_errors", "dep_hint", "new_patterns", "n_signals",
]


def _merge(analyses, kind):
    """Fold '-db' siblings into their owner: OR of flags, max of numbers,
    union of hints and patterns."""
    out = {}
    for a in analyses:
        k = canonical(a["service"])
        if k not in out:
            out[k] = dict(a)
            continue
        o = out[k]
        o["is_anomaly"] = bool(o.get("is_anomaly")) or bool(a.get("is_anomaly"))
        if kind == "trace":
            for f in ("p99_latency_ms", "error_rate"):
                o[f] = max(float(o.get(f) or 0), float(a.get(f) or 0))
        else:
            o["error_count"] = max(int(o.get("error_count") or 0), int(a.get("error_count") or 0))
            o["dependency_hints"] = sorted(set(o.get("dependency_hints") or []) | set(a.get("dependency_hints") or []))
            o["new_patterns"] = list(o.get("new_patterns") or []) + list(a.get("new_patterns") or [])
    return out


def service_rows(ctx, case, candidates, visible=True):
    """One feature row per candidate service (canonical names)."""
    m_by = {}
    for m in ctx["anomaly_details"]["metric_anomalies"]:
        m_by.setdefault(canonical(m["service"]), []).append(m)
    full_m = {}
    for m in ctx.get("_all_metrics", []):
        full_m.setdefault(canonical(m["service"]), []).append(m)
    t_by = _merge(ctx.get("_trace_analysis", []), "trace")
    l_by = _merge(ctx.get("_log_analysis", []), "log")
    rows = []
    for s in candidates:
        flagged_m = m_by.get(s, [])
        src_m = flagged_m if (visible and flagged_m) else full_m.get(s, [])
        if visible and not flagged_m:
            src_m = []
        t = t_by.get(s, {})
        l = l_by.get(s, {})
        t_vis = (not visible) or t.get("is_anomaly", False)
        l_vis = (not visible) or l.get("is_anomaly", False)

        def mx(key):
            vals = [x.get(key) for x in src_m if x.get(key) is not None]
            return float(max(vals)) if vals else 0.0

        r = {
            "case_id": case.case_id, "system": case.system, "fault": case.fault,
            "service": s, "label": int(s == canonical(case.root_service)),
            "metric_flag": int(bool(flagged_m)),
            "if_score": mx("anomaly_score"),
            "cpu_ratio": mx("cpu_vs_baseline_ratio"),
            "mem_ratio": mx("memory_vs_baseline_ratio"),
            "mem_trigger": int(any(x.get("trigger") == "memory_pressure" for x in flagged_m)),
            "trace_flag": int(t.get("is_anomaly", False)),
            "p99_ms": float(t.get("p99_latency_ms", 0) or 0) if t_vis else 0.0,
            "trace_err_rate": float(t.get("error_rate", 0) or 0) if t_vis else 0.0,
            "log_flag": int(l.get("is_anomaly", False)),
            "log_errors": float(l.get("error_count", 0) or 0) if l_vis else 0.0,
            "dep_hint": int(bool(l.get("dependency_hints"))) if l_vis else 0,
            "new_patterns": float(len(l.get("new_patterns", []))) if l_vis else 0.0,
        }
        r["n_signals"] = r["metric_flag"] + r["trace_flag"] + r["log_flag"]
        rows.append(r)
    return rows


def _rank_by(scores, case_id, tag):
    """Descending by score; ties broken by a seeded random order."""
    items = list(scores.items())
    rng = random.Random(f"{C.SEED}|{tag}|{case_id}")
    rng.shuffle(items)
    items.sort(key=lambda kv: kv[1], reverse=True)  # stable sort keeps shuffle among ties
    return [k for k, _ in items]


def rank_detector_count(rows):
    return _rank_by({r["service"]: (r["n_signals"], r["if_score"]) for r in rows},
                    rows[0]["case_id"], "detcount")


def rank_first_affected(ctx, candidates, case_id):
    """Services in the order of the prompt's AFFECTED SERVICES line, then the
    rest in a seeded order: a position-only comparator (no calls)."""
    first = []
    for a in ctx.get("affected_services", []):
        c = canonical(a)
        if c in candidates and c not in first:
            first.append(c)
    rest = sorted(c for c in candidates if c not in first)
    random.Random(f"{C.SEED}|firstaff|{case_id}").shuffle(rest)
    return first + rest


def rank_largest_anomaly(rows_all):
    return _rank_by({r["service"]: r["if_score"] for r in rows_all},
                    rows_all[0]["case_id"], "largest")


def cv_rank(df, model_name="lr", group_cols=("system", "service_gt", "fault"), n_splits=5):
    """Grouped cross-validated probabilities -> ranking per case.

    Groups keep the three repetitions of the same (system, root service,
    fault) together, so a test case never has a twin in training.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    df = df.copy()
    gt = df[df["label"] == 1].set_index("case_id")["service"]
    df["service_gt"] = df["case_id"].map(gt)
    groups = df[list(group_cols)].astype(str).agg("|".join, axis=1)
    X, y = df[VISIBLE_FEATURES].values.astype(float), df["label"].values
    prob = np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        if model_name == "lr":
            mdl = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        else:
            mdl = RandomForestClassifier(n_estimators=300, random_state=C.SEED % (2**31),
                                         class_weight="balanced", min_samples_leaf=2)
        mdl.fit(X[tr], y[tr])
        prob[te] = mdl.predict_proba(X[te])[:, 1]
    df["p"] = prob
    out = {}
    for cid, g in df.groupby("case_id"):
        out[cid] = _rank_by(dict(zip(g["service"], g["p"])), cid, f"cv-{model_name}")
    return out


def loso_rank(df, model_name="lr"):
    """Leave-one-system-out: train on two systems, rank the third."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    out = {}
    for sysname in sorted(df["system"].unique()):
        tr, te = df[df["system"] != sysname], df[df["system"] == sysname]
        mdl = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        mdl.fit(tr[VISIBLE_FEATURES].values.astype(float), tr["label"].values)
        p = mdl.predict_proba(te[VISIBLE_FEATURES].values.astype(float))[:, 1]
        te = te.assign(p=p)
        for cid, g in te.groupby("case_id"):
            out[cid] = _rank_by(dict(zip(g["service"], g["p"])), cid, f"loso-{model_name}")
    return out


# ================================================================ SimpleRCA-style
SIMPLE_SIGMA = 3.0
SIMPLE_LAT_MULT = 3.0
SIMPLE_LOG_MULT = 3.0
SIMPLE_LOG_MIN = 5


def simplerca(case, mdf, tdf, ldf, candidates):
    inj = case.inject_time
    nb = mdf[(mdf["time"] >= inj - C.NORMAL_WINDOW_S) & (mdf["time"] < inj)]
    an = mdf[(mdf["time"] >= inj) & (mdf["time"] < inj + C.ANOMAL_WINDOW_S)]
    alerts = {s: 0.0 for s in candidates}
    for col in mdf.columns:
        if col == "time" or "_" not in col:
            continue
        s = canonical(col.split("_")[0])
        if s not in alerts:
            continue
        mu, sd = nb[col].mean(), nb[col].std()
        a = an[col].mean()
        if pd.notna(mu) and pd.notna(a) and pd.notna(sd):
            if (sd > 0 and abs(a - mu) > SIMPLE_SIGMA * sd) or (sd == 0 and a != mu):
                alerts[s] += 1
    if tdf is not None and not tdf.empty:
        own = owner_map(tdf["serviceName"].unique(), candidates)
        towner = tdf["serviceName"].astype(str).map(own)
        for s in candidates:
            sp = tdf[towner == s]
            b = sp[(sp["ts"] >= inj - C.NORMAL_WINDOW_S) & (sp["ts"] < inj)]["duration"]
            x = sp[(sp["ts"] >= inj) & (sp["ts"] < inj + C.ANOMAL_WINDOW_S)]["duration"]
            if len(b) and len(x) and b.quantile(0.95) > 0 and x.quantile(0.95) >= SIMPLE_LAT_MULT * b.quantile(0.95):
                alerts[s] += 1
    if ldf is not None and not ldf.empty and "container_name" in ldf.columns:
        txt = ldf.get("message", pd.Series([""] * len(ldf))).astype(str).str.lower()
        err = txt.str.contains("error|fail|exception")
        own = owner_map(ldf["container_name"].unique(), candidates)
        lowner = ldf["container_name"].astype(str).map(own)
        for s in candidates:
            mine = (lowner == s) & err
            b = int((mine & (ldf["ts"] >= inj - C.NORMAL_WINDOW_S) & (ldf["ts"] < inj)).sum())
            x = int((mine & (ldf["ts"] >= inj) & (ldf["ts"] < inj + C.ANOMAL_WINDOW_S)).sum())
            if x >= SIMPLE_LOG_MIN and x >= SIMPLE_LOG_MULT * max(b, 1):
                alerts[s] += 1
    return _rank_by(alerts, case.case_id, "simplerca")
