"""Amendment 6 analyses (PROTOCOL_V3_AMENDMENT_6.md).

Confirmatory family (deployed model, Holm over four tests):
  H6a   RE3: annotated - nolog                       (raw log text helps)
  H6b   (annotated - nolog) on RE3 minus the same on RE2  (more on RE3)
  H6c-1 RE3: permuted - anon_full                    (name form vs labels)
  H6c-2 RE3: annotated - permuted                    (which service a name means)
Secondary and descriptive: the other two models, RE2, the detector count,
strata by whether the log samples name the root, the pull of the root's real
name under `permuted`, run-to-run variation, manipulation checks, and the
84 non-pilot cases.

usage (repo root, env active, RCAEval on PYTHONPATH):
  python scripts/17_amendment6.py --out out --pilot out/pilot_re3.txt
writes out/re3/amendment6.md and out/re3/amendment6.json
"""
import argparse
import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from rcastudy import config as C  # noqa: E402
from rcastudy import context as X  # noqa: E402


def _mod(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


A3 = _mod("a3", "11_amendment3.py")
RN = _mod("rn", "16_review_numbers.py")
EV = A3.EV
DEP = C.DEPLOYED_MODEL
MODELS = sorted(C.MODELS)


def rank(d):
    return {k: v["ranking"] for k, v in d.items()}


def fmt(r):
    return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]"


def run_of(runs, model, cond, tag="main"):
    return runs.get((tag, f"{model}__{cond}"), {})


def t1(cases, runs, model, cond, tag="main"):
    return EV.top1(cases, rank(run_of(runs, model, cond, tag)))


def paired(cases, a, b):
    r = EV.paired(cases, a, b)
    keys = [c for c in cases if c["case_id"] in a and c["case_id"] in b]
    r["p_exact"], r["k_nonzero"] = RN.exact_p(keys, {c["case_id"]: a[c["case_id"]] - b[c["case_id"]] for c in keys})
    return r


def _cluster_sums(cases, d):
    g = {}
    for c in cases:
        if c["case_id"] in d:
            s, n = g.get(EV.cluster_of(c), (0.0, 0))
            g[EV.cluster_of(c)] = (s + d[c["case_id"]], n + 1)
    return list(g.values())


def between_suites(c_hi, d_hi, c_lo, d_lo):
    """mean(d) on suite 'hi' minus mean(d) on suite 'lo'; clusters are
    independent between suites. Cluster bootstrap within each suite and a
    cluster-label permutation test (two-sided), both seeded."""
    g_hi, g_lo = _cluster_sums(c_hi, d_hi), _cluster_sums(c_lo, d_lo)
    stat = lambda h, l: sum(s for s, _ in h) / sum(n for _, n in h) - sum(s for s, _ in l) / sum(n for _, n in l)  # noqa: E731
    t = stat(g_hi, g_lo)
    rng = np.random.default_rng(C.SEED)
    boots = []
    for _ in range(EV.N_BOOT):
        h = [g_hi[i] for i in rng.integers(0, len(g_hi), len(g_hi))]
        l_ = [g_lo[i] for i in rng.integers(0, len(g_lo), len(g_lo))]
        boots.append(stat(h, l_))
    pool = g_hi + g_lo
    S = np.array([s for s, _ in pool], dtype=float)
    N = np.array([n for _, n in pool], dtype=float)
    k = len(g_hi)
    hits = 0
    for _ in range(EV.N_PERM):
        idx = rng.permutation(len(pool))
        hi, lo = idx[:k], idx[k:]
        ts = S[hi].sum() / N[hi].sum() - S[lo].sum() / N[lo].sum()
        hits += abs(ts) >= abs(t) - 1e-12
    return {"diff": t, "ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "p_perm": (hits + 1) / (EV.N_PERM + 1), "p_exact": float("nan"), "k_nonzero": len(pool),
            "n": sum(N)}


def diff_dict(a, b):
    return {k: a[k] - b[k] for k in a if k in b}


def family(c2, r2, c3, r3):
    a3, n3 = t1(c3, r3, DEP, "annotated"), t1(c3, r3, DEP, "nolog")
    a2, n2 = t1(c2, r2, DEP, "annotated"), t1(c2, r2, DEP, "nolog")
    p3, f3 = t1(c3, r3, DEP, "permuted"), t1(c3, r3, DEP, "anon_full")
    out = {}
    out["H6a RE3 annotated - nolog"] = paired(c3, a3, n3)
    out["H6b (annotated - nolog): RE3 minus RE2"] = between_suites(c3, diff_dict(a3, n3), c2, diff_dict(a2, n2))
    out["H6c-1 RE3 permuted - anon_full"] = paired(c3, p3, f3)
    out["H6c-2 RE3 annotated - permuted"] = paired(c3, a3, p3)
    keys = list(out)
    for k, h in zip(keys, EV.holm([out[k]["p_perm"] for k in keys])):
        out[k]["p_holm"] = h
    ex = [out[k]["p_exact"] if not np.isnan(out[k]["p_exact"]) else out[k]["p_perm"] for k in keys]
    for k, h in zip(keys, EV.holm(ex)):
        out[k]["p_holm_exact"] = h
    return out


def verdicts(q):
    """Decision rules fixed in Amendment 6 (Holm p < 0.05 on the Monte Carlo p)."""
    sig = lambda k: q[k]["p_holm"] < 0.05  # noqa: E731
    d = lambda k: q[k]["diff"]  # noqa: E731
    v = {}
    k = "H6a RE3 annotated - nolog"
    v["H6a"] = "supported: raw log text raises RE3 accuracy" if sig(k) and d(k) > 0 else (
        "contradicted: removing log text raises RE3 accuracy" if sig(k) else "not supported")
    k = "H6b (annotated - nolog): RE3 minus RE2"
    v["H6b"] = "supported: log text matters more on RE3 than on RE2" if sig(k) and d(k) > 0 else (
        "contradicted" if sig(k) else "not supported")
    k = "H6c-2 RE3 annotated - permuted"
    v["H6c-2"] = ("names that mean the right service help (correct meaning matters)" if sig(k) and d(k) > 0 else
                  "permuted names do better than true names" if sig(k) else "no effect of correct meaning detected")
    k = "H6c-1 RE3 permuted - anon_full"
    v["H6c-1"] = ("wrong but name-like names do better than labels (name form helps)" if sig(k) and d(k) > 0 else
                  "wrong names do worse than labels (misleading meaning misleads)" if sig(k) else
                  "no difference between wrong names and labels detected")
    return v


def borderline(q):
    out = []
    for k, r in q.items():
        if "p_holm_exact" in r and (r["p_holm"] < 0.05) != (r["p_holm_exact"] < 0.05):
            out.append(k)
    return out


def root_named_in_logs(c):
    import json as _j
    logs = _j.dumps([l for l in c["context"].get("full_logs", []) if l.get("is_anomaly")])
    rx = X._forms_regex({f.lower() for f in X.name_forms(c["gt"]["root_service"])})
    return bool(rx.findall(logs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--pilot", default="out/pilot_re3.txt")
    a = ap.parse_args()
    c2, m2, r2 = A3.load(os.path.join(a.out, "re2"))
    c3, m3, r3 = A3.load(os.path.join(a.out, "re3"))
    pilot = {l.strip() for l in open(a.pilot) if l.strip()} if a.pilot and os.path.exists(a.pilot) else set()
    L = ["# Amendment 6 analyses (17_amendment6.py)\n",
         "Deployed model; AC@1 on all cases (unflagged cases ranked by chance, as everywhere in the study). "
         "p = cluster sign-flip permutation (10,000), exact = enumeration or 10^6 flips; H6b uses a "
         "cluster-label permutation between suites. Holm over H6a, H6b, H6c-1, H6c-2.\n"]
    J = {}

    # ---------------------------------------------------- manipulation checks
    L.append("## 0. Manipulation checks\n")
    L.append("| suite | model | condition | records | check value > 0 | answers with no resolvable service |")
    L.append("|---|---|---|---|---|---|")
    for suite, runs in (("re2", r2), ("re3", r3)):
        for m in MODELS:
            for cond in ("nolog", "permuted"):
                d = run_of(runs, m, cond)
                if not d:
                    continue
                bad = sum(1 for v in d.values() if (v.get("anon_leaks") or 0) > 0)
                none = sum(1 for v in d.values() if v["votes"] and v["votes"][0].get("n_listed", 1) == 0)
                L.append(f"| {suite} | {m} | {cond} | {len(d)} | {bad} | {none} |")
    L.append("\n`nolog`: check value = raw log strings left in the prompt. `permuted`: check value = prompts whose "
             "name-free skeleton differs from the original's. Both must be 0.\n")

    # ---------------------------------------------------- confirmatory
    for label, cs3 in (("Primary: all 90 RE3 cases (RE2: 270)", c3),
                       (f"Sensitivity: {sum(c['case_id'] not in pilot for c in c3)} RE3 cases outside the pilot",
                        [c for c in c3 if c["case_id"] not in pilot])):
        q = family(c2, r2, cs3, r3)
        v = verdicts(q)
        L.append(f"## {label}\n")
        L.append("| test | diff [95% CI] | p | p Holm | exact p | exact p Holm |")
        L.append("|---|---|---|---|---|---|")
        for k, r in q.items():
            ex = "-" if np.isnan(r["p_exact"]) else f"{r['p_exact']:.4f}"
            L.append(f"| {k} | {fmt(r)} | {r['p_perm']:.4f} | {r['p_holm']:.4f} | {ex} | {r['p_holm_exact']:.4f} |")
        L.append("")
        for k_, s in v.items():
            L.append(f"- **{k_}**: {s}")
        bl = borderline(q)
        if bl:
            L.append(f"- borderline (Monte Carlo and exact Holm on different sides of 0.05): {', '.join(bl)}")
        L.append("")
        J[label] = {"tests": q, "verdicts": v}

    # ---------------------------------------------------- secondary
    L.append("## Secondary and descriptive\n")
    L.append("### Accuracy by condition (AC@1, all cases)\n")
    L.append("| suite | model | annotated | nolog | permuted | anon_full |")
    L.append("|---|---|---|---|---|---|")
    for suite, cs, runs in (("re2", c2, r2), ("re3", c3, r3)):
        for m in MODELS:
            cells = []
            for cond in ("annotated", "nolog", "permuted", "anon_full"):
                d = run_of(runs, m, cond)
                cells.append(f"{np.mean(list(EV.top1(cs, rank(d)).values())):.3f}" if d else "-")
            L.append(f"| {suite} | {m} | " + " | ".join(cells) + " |")
    L.append("\n### Paired differences, every model and suite (descriptive except the four tests above)\n")
    L.append("| suite | model | annotated - nolog | permuted - anon_full | annotated - permuted |")
    L.append("|---|---|---|---|---|")
    for suite, cs, runs in (("re2", c2, r2), ("re3", c3, r3)):
        for m in MODELS:
            row = []
            for x, y in (("annotated", "nolog"), ("permuted", "anon_full"), ("annotated", "permuted")):
                if run_of(runs, m, x) and run_of(runs, m, y):
                    r = EV.paired(cs, t1(cs, runs, m, x), t1(cs, runs, m, y))
                    row.append(f"{fmt(r)}, p {r['p_perm']:.3f}")
                else:
                    row.append("-")
            L.append(f"| {suite} | {m} | " + " | ".join(row) + " |")

    L.append("\n### Without log text, against the detector count (deployed)\n")
    L.append("| suite | annotated - detector_count | nolog - detector_count |")
    L.append("|---|---|---|")
    for suite, cs, runs, meth in (("re2", c2, r2, m2), ("re3", c3, r3, m3)):
        det = EV.top1(cs, meth.get("detector_count", {}))
        row = []
        for cond in ("annotated", "nolog"):
            if run_of(runs, DEP, cond):
                r = EV.paired(cs, t1(cs, runs, DEP, cond), det)
                row.append(f"{fmt(r)}, p {r['p_perm']:.3f}")
            else:
                row.append("-")
        L.append(f"| {suite} | " + " | ".join(row) + " |")

    L.append("\n### RE3 strata: do the log samples name the root? (flagged cases, deployed)\n")
    L.append("| stratum | n | annotated | nolog | annotated - nolog [95% CI] | permuted | anon_full |")
    L.append("|---|---|---|---|---|---|---|")
    fl = [c for c in c3 if c["flagged"]]
    for name, cs in (("root named in log samples", [c for c in fl if root_named_in_logs(c)]),
                     ("root not named", [c for c in fl if not root_named_in_logs(c)])):
        if not cs or not run_of(r3, DEP, "nolog"):
            continue
        acc = lambda cond: np.mean(list(t1(cs, r3, DEP, cond).values())) if run_of(r3, DEP, cond) else float("nan")  # noqa: E731
        r = EV.paired(cs, t1(cs, r3, DEP, "annotated"), t1(cs, r3, DEP, "nolog"))
        L.append(f"| {name} | {len(cs)} | {acc('annotated'):.3f} | {acc('nolog'):.3f} | {fmt(r)} | "
                 f"{acc('permuted'):.3f} | {acc('anon_full'):.3f} |")

    L.append("\n### Pull of the root's real name under `permuted`\n")
    L.append("How often the model's top-1 is the service now *shown* under the root's real name (a wrong service), "
             "against the count expected if that service were picked at chance among the candidates.\n")
    L.append("| suite | model | flagged cases | top-1 = service shown with the root's name | expected at chance | "
             "top-1 = true root |")
    L.append("|---|---|---|---|---|---|")
    for suite, cs, runs in (("re2", c2, r2), ("re3", c3, r3)):
        for m in MODELS:
            d = run_of(runs, m, "permuted")
            if not d:
                continue
            hit = exp = right = n = 0
            for c in cs:
                if c["case_id"] not in d:
                    continue
                names = sorted(set(c["candidates"]) | set(c["detector_services"]))
                fwd = X.permuter(c["case_id"], c["candidates"], names)[3]
                root = c["gt"]["root_service"]
                imp = next((x for x, s in fwd.items() if s == root), None)
                top = d[c["case_id"]]["ranking"][0]
                n += 1
                hit += int(imp is not None and top == imp)
                right += int(top == root)
                exp += 1 / max(len(c["candidates"]), 1)
            L.append(f"| {suite} | {m} | {n} | {hit} | {exp:.1f} | {right} |")

    rep = run_of(r3, DEP, "annotated", "a6rep")
    if rep:
        main_ = run_of(r3, DEP, "annotated")
        ids = [c for c in c3 if c["case_id"] in rep and c["case_id"] in main_]
        ch = sum(rep[c["case_id"]]["ranking"][0] != main_[c["case_id"]]["ranking"][0] for c in ids)
        r = EV.paired(c3, EV.top1(c3, rank(rep)), EV.top1(c3, rank(main_)))
        L.append(f"\n### Run-to-run on RE3 (deployed, annotated, second run)\n\nTop-1 changed in {ch}/{len(ids)} flagged "
                 f"cases; AC@1 {r['a'] / r['n']:.3f} vs {r['b'] / r['n']:.3f}, difference {fmt(r)}, p {r['p_perm']:.3f}.")
        J["rerun"] = {"changed": ch, "n": len(ids), "diff": r}

    path = os.path.join(a.out, "re3", "amendment6.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(a.out, "re3", "amendment6.json"), "w") as f:
        json.dump(J, f, indent=1, default=float)
    print("wrote", path)


if __name__ == "__main__":
    main()
