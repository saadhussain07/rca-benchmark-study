"""Find RCAEval cases on disk and cut the study windows.

Supports both published layouts:
  * Hugging Face Parquet: <root>/re2ob_<service>_<fault>_<n>/metrics.parquet ...
  * Zenodo/Figshare files: any directory holding inject_time.txt, named either
    <suite>_<service>_<fault>_<n> or <service>_<fault>/<n>.

Ground truth comes from the directory name or cases.parquet. It is used only
for scoring and never reaches a prompt or a feature.
"""
import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd


try:  # RCAEval's own readers accept both layouts
    from RCAEval.utility import read_metrics, read_logs, read_traces
except Exception:  # pragma: no cover - fallback used only without RCAEval
    read_metrics = read_logs = read_traces = None

# RCAEval's Zenodo layout names the RE1 folders after the system
RE1_DIRS = {"online-boutique": "re1ob", "sock-shop-2": "re1ss", "train-ticket": "re1tt"}
METRIC_FILES = ("metrics.parquet", "metrics.json", "data.csv", "simple_metrics.csv", "metrics.csv")

SUITE_RE = re.compile(r"^(re[123])(ob|ss|tt)_(.+)_([a-z]+)_(\d+)$")


@dataclass
class Case:
    case_id: str          # e.g. re2ob_cartservice_mem_2
    path: str
    suite: str            # re1 / re2 / re3
    system: str           # ob / ss / tt
    root_service: str
    fault: str
    rep: int
    inject_time: int = None


def _parse_name(path):
    base = os.path.basename(os.path.normpath(path))
    m = SUITE_RE.match(base)
    if m:
        suite, system, service, fault, rep = m.groups()
        return base, suite, system, service, fault, int(rep)
    # <...>/RE2-OB/<service>_<fault>/<n>
    parts = re.split(r"[\\/]", os.path.normpath(path))
    if base.isdigit() and len(parts) >= 3:
        sf = parts[-2]
        parent = parts[-3].lower()
        suite_sys = RE1_DIRS.get(parent, parent.replace("-", ""))
        if "_" not in sf or not re.match(r"^re[123](ob|ss|tt)$", suite_sys):
            return None
        suite, system = suite_sys[:3], suite_sys[3:5]
        # Amendment 3: RE3-TT holds a second batch of one service/fault in a
        # folder named <service>_<fault>_<k> (ts-route-service_f3_1). Its cases
        # get ids <service>_<fault>_b<k>r<n>, same fault, so they share the
        # (system, root, fault) cluster. No RE1/RE2 folder has this form.
        mb = re.match(r"^(.+)_(f\d+)_(\d+)$", sf)
        if mb:
            service, fault, batch = mb.groups()
            return (f"{suite}{system}_{service}_{fault}_b{batch}r{base}", suite, system, service, fault,
                    int(base))
        service, fault = sf.rsplit("_", 1)
        return f"{suite}{system}_{service}_{fault}_{base}", suite, system, service, fault, int(base)
    return None


def _read_inject_time(path, index_row=None):
    f = os.path.join(path, "inject_time.txt")
    if os.path.exists(f):
        with open(f) as fh:
            return int(fh.read().strip().split()[0])
    if index_row is not None:
        for col in ("inject_time", "injection_time", "inject_ts"):
            if col in index_row and pd.notna(index_row[col]):
                return int(index_row[col])
    raise FileNotFoundError(f"no injection time for {path}")


def discover(root, suite="re2"):
    """Return all cases of one suite under root, sorted by case_id."""
    index = None
    idx_file = os.path.join(root, "cases.parquet")
    if os.path.exists(idx_file):
        index = pd.read_parquet(idx_file)
    cases = []
    for dirpath, dirnames, filenames in os.walk(root):
        if not any(f in METRIC_FILES for f in filenames):
            continue
        parsed = _parse_name(dirpath)
        if parsed is None:
            continue
        case_id, s, system, service, fault, rep = parsed
        if s != suite:
            continue
        row = None
        if index is not None and "case" in index.columns:
            hit = index[index["case"] == case_id]
            if len(hit):
                row = hit.iloc[0]
                if "root_cause_service" in hit.columns:
                    service = str(row["root_cause_service"])
        cases.append(Case(case_id, dirpath, s, system, service, fault, rep,
                          _read_inject_time(dirpath, row)))
    cases.sort(key=lambda c: c.case_id)
    return cases


def _to_seconds(series):
    """Convert a timestamp column of unknown unit to unix seconds."""
    s = pd.to_numeric(series, errors="coerce")
    med = np.nanmedian(s.values) if len(s) else 0
    if med > 1e17:
        return s / 1e9      # ns
    if med > 1e14:
        return s / 1e6      # us
    if med > 1e11:
        return s / 1e3      # ms
    return s


def load_metrics(case):
    """Metrics as a wide frame. Prefers data.csv, the file RCAEval main.py
    reads, so every method sees the same numbers."""
    df = None
    for name in ("data.csv", "simple_metrics.csv", "metrics.csv"):
        f = os.path.join(case.path, name)
        if os.path.exists(f):
            df = pd.read_csv(f)
            break
    if df is not None and not any(c.endswith("_cpu") for c in df.columns):
        # RE1 Sock Shop and Train Ticket ship raw cAdvisor names in data.csv;
        # their simple_data.csv carries the <service>_cpu/_mem form. Used for
        # the RE1 pilot only (RE2 cases all have _cpu columns).
        for name in ("simple_data.csv", "simple_metrics.csv"):
            f = os.path.join(case.path, name)
            if os.path.exists(f):
                alt = pd.read_csv(f)
                if any(c.endswith("_cpu") for c in alt.columns):
                    df = alt
                    df.attrs["metrics_file"] = name
                    break
    if df is None:
        df = read_metrics(case.path)  # Parquet / JSON layouts
    if "time.1" in df.columns:
        df = df.drop(columns=["time.1"])
    t = _to_seconds(df["time"])
    bad = ~np.isfinite(t.astype(float))
    # Rows without a usable timestamp cannot fall in any window; RCAEval's
    # time comparisons drop them too. Their number is recorded.
    df = df.loc[~bad].copy()
    df["time"] = t.loc[~bad].astype("int64")
    df.attrs["rows_without_time"] = int(bad.sum())
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def ts_ok(df, min_share=0.95):
    """True when at least min_share of the rows have a usable timestamp."""
    return df is not None and len(df) > 0 and df["ts"].notna().mean() >= min_share


def load_logs(case):
    if read_logs is None:
        return None
    df = read_logs(case.path)
    if df is None:
        return None
    df = df.copy()
    if "timestamp" in df.columns:
        df["ts"] = _to_seconds(df["timestamp"])
    elif "time" in df.columns:
        df["ts"] = _to_seconds(df["time"])
    return df


def load_traces(case):
    if read_traces is None:
        return None
    df = read_traces(case.path)
    if df is None:
        return None
    df = df.copy()
    if "startTime" in df.columns:
        df["ts"] = _to_seconds(df["startTime"])
    elif "startTimeMillis" in df.columns:
        df["ts"] = _to_seconds(df["startTimeMillis"])
    df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
    return df


def services_from_metrics(df):
    """Every metric-column prefix (the entities RCAEval ranks)."""
    svcs = set()
    for c in df.columns:
        if c == "time" or "_" not in c:
            continue
        svcs.add(c.split("_")[0])
    return sorted(svcs)


def detector_services(df):
    """Services the metric detector monitors: those with a _cpu column (A12)."""
    return sorted(c[: -len("_cpu")] for c in df.columns if c.endswith("_cpu"))


def candidates(df):
    """Candidate set for ranking and scoring: every metric prefix, '-db'
    folded into its owner, as RCAEval main.py folds names when scoring."""
    return sorted({canonical(s) for s in services_from_metrics(df)})


def canonical(service):
    return service.replace("-db", "")


def owner_map(raw_names, services):
    """Map each raw log/trace name (e.g. 'frontendservice', 'carts-db-7f9c')
    to the detector service it belongs to: the longest service name that is a
    prefix of it. Names with no owner map to None."""
    by_len = sorted(services, key=len, reverse=True)
    out = {}
    for raw in set(map(str, raw_names)):
        out[raw] = next((s for s in by_len if raw.startswith(s)), None)
    return out
