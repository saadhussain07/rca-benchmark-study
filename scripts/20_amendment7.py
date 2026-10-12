"""Amendment 7 analyses (PROTOCOL_V3_AMENDMENT_7.md): do the headline findings
hold in a generic pipeline that shares nothing with the deployed agent but the
data and the window?

Confirmatory family (deployed model gpt-oss-120b, generic pipeline; Holm over four):
  H7a  RE2+RE3: decoy named first, g_decoy - g_full              (a false claim moves the answer)
  H7b  RE3: g_full - g_nolog                                     (raw log text raises RE3 accuracy)
  H7c  (g_full - g_nolog) on RE3 minus RE2                       (more on RE3 than on RE2)
  H7d  RE2: summary_count - g_full                               (the model trails the label-free
                                                                  ranking of its own summary)
Everything else, including the second model (--m7, descriptive), is descriptive.

usage: python scripts/20_amendment7.py --out out --m7 qwen3.8-27b --pilot out/pilot_re3.txt
writes out/re3/amendment7.md and .json
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


def _mod(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


A6 = _mod("a6", "17_amendment6.py")
A3, EV = A6.A3, A6.EV
DEP = C.DEPLOYED_MODEL


def rank(d):
    return {k: v["ranking"] for k, v in d.items()}


def run_of(runs, m, cond, tag="main"):
    return runs.get((tag, f"{m}__{cond}"), {})


def decoy_first(cases, run):
    return {c["case_id"]: int(run[c["case_id"]]["ranking"][0] == c["decoy"]["service"])
            for c in cases if c["case_id"] in run and c["decoy"]["service"]}


def decoy_pair(cases, runs, m, cond_d, cond_base):
    D_, B_ = run_of(runs, m, cond_d), run_of(runs, m, cond_base)
    ids = [c for c in cases if c["case_id"] in D_ and c["case_id"] in B_ and c["decoy"]["service"]]
    return ids, decoy_first(ids, D_), decoy_first(ids, B_)


def acc(cases, runs, m, cond):
    d = run_of(runs, m, cond)
    return float(np.mean(list(EV.top1(cases, rank(d)).values()))) if d else float("nan")


def summary_count(cases):
    from rcastudy import generic as G
    return {c["case_id"]: G.rank_summary_count(c["generic"], c["candidates"], c["case_id"])
            for c in cases if c.get("generic")}


def family(S):
    (c2, m2, r2), (c3, m3, r3), (g2, _, q2), (g3, _, q3) = S["re2"], S["re3"], S["re2g"], S["re3g"]
    out = {}
    i2, e2, f2 = decoy_pair(g2, q2, DEP, "g_decoy", "g_full")
    i3, e3, f3 = decoy_pair(g3, q3, DEP, "g_decoy", "g_full")
    out["H7a RE2+RE3 decoy first: g_decoy - g_full"] = A6.paired(i2 + i3, {**e2, **e3}, {**f2, **f3})
    full3, nol3 = A6.t1(g3, q3, DEP, "g_full"), A6.t1(g3, q3, DEP, "g_nolog")
    full2, nol2 = A6.t1(g2, q2, DEP, "g_full"), A6.t1(g2, q2, DEP, "g_nolog")
    out["H7b RE3 g_full - g_nolog"] = A6.paired(g3, full3, nol3)
    out["H7c (g_full - g_nolog): RE3 minus RE2"] = A6.between_suites(
        g3, A6.diff_dict(full3, nol3), g2, A6.diff_dict(full2, nol2))
    out["H7d RE2 summary_count - g_full"] = A6.paired(g2, EV.top1(g2, summary_count(g2)), full2)
    keys = list(out)
    for k, h in zip(keys, EV.holm([out[k]["p_perm"] for k in keys])):
        out[k]["p_holm"] = h
    ex = [out[k]["p_exact"] if not np.isnan(out[k]["p_exact"]) else out[k]["p_perm"] for k in keys]
    for k, h in zip(keys, EV.holm(ex)):
        out[k]["p_holm_exact"] = h
        out[k]["verdict"] = "supported" if (out[k]["p_holm"] < 0.05 and out[k]["diff"] > 0) else (
            "contradicted" if out[k]["p_holm"] < 0.05 else "not supported")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--m7", default="qwen3.8-27b", help="second model (descriptive)")
    ap.add_argument("--pilot", default="out/pilot_re3.txt")
    a = ap.parse_args()
    m7 = a.m7
    S = {k: A3.load(os.path.join(a.out, d)) for k, d in
         (("re2", "re2"), ("re3", "re3"), ("re2g", "re2_generic"), ("re3g", "re3_generic"))}
    pilot = {l.strip() for l in open(a.pilot) if l.strip()} if a.pilot and os.path.exists(a.pilot) else set()
    L = [f"# Amendment 7 analyses (20_amendment7.py); M = {m7}\n",
         "Generic pipeline, deployed model unless stated; AC@1 on all cases; decoy tests on cases with a decoy. "
         "Holm over H7a-H7d. The second model is descriptive.\n"]
    J = {}
    for label, Sx in (("Primary", S), (f"Sensitivity: RE3 without {len(pilot)} pilot cases", {
            **S, "re3": ([c for c in S["re3"][0] if c["case_id"] not in pilot], S["re3"][1], S["re3"][2]),
            "re3g": ([c for c in S["re3g"][0] if c["case_id"] not in pilot], S["re3g"][1], S["re3g"][2])})):
        q = family(Sx)
        L.append(f"## {label}\n")
        L.append("| test | diff [95% CI] | p | p Holm | exact p Holm | verdict |")
        L.append("|---|---|---|---|---|---|")
        for k, r in q.items():
            L.append(f"| {k} | {A6.fmt(r)} | {r['p_perm']:.4f} | {r['p_holm']:.4f} | {r['p_holm_exact']:.4f} | "
                     f"{r['verdict']} |")
        L.append("")
        J[label] = q

    L.append("## Descriptive\n")
    L.append("### AC@1, all cases\n")
    L.append("| suite | pipeline | model | " + " | ".join(["annotated", "stripped", "decoy", "nolog"]) + " |")
    L.append("|---|---|---|---|---|---|---|")
    for suite in ("re2", "re3"):
        c, _, r = S[suite]
        for m in (DEP, m7):
            L.append(f"| {suite} | deployed agent | {m} | " +
                     " | ".join(f"{acc(c, r, m, x):.3f}" for x in ("annotated", "stripped", "decoy", "nolog")) + " |")
    L.append("\n| suite | pipeline | model | g_full | g_nolog | g_decoy |")
    L.append("|---|---|---|---|---|---|")
    for suite in ("re2g", "re3g"):
        c, _, r = S[suite]
        for m in (DEP, m7):
            L.append(f"| {suite[:3]} | generic | {m} | " +
                     " | ".join(f"{acc(c, r, m, x):.3f}" for x in ("g_full", "g_nolog", "g_decoy")) + " |")

    L.append("\n### Decoy named first (cases with a decoy)\n")
    L.append("| suite | pipeline | model | with decoy | without | n | harm (correct without, decoy first with) |")
    L.append("|---|---|---|---|---|---|---|")
    for suite, pipe, cd, cb in (("re2", "deployed agent", "decoy", "stripped"), ("re3", "deployed agent", "decoy", "stripped"),
                                ("re2g", "generic", "g_decoy", "g_full"), ("re3g", "generic", "g_decoy", "g_full")):
        c, _, r = S[suite]
        for m in (DEP, m7):
            ids, d, b = decoy_pair(c, r, m, cd, cb)
            if not ids:
                continue
            B_ = run_of(r, m, cb)
            right = [x for x in ids if B_[x["case_id"]]["ranking"][0] == x["gt"]["root_service"]]
            harm = sum(d[x["case_id"]] for x in right)
            L.append(f"| {suite[:3]} | {pipe} | {m} | {sum(d.values())} | {sum(b.values())} | {len(ids)} | "
                     f"{harm}/{len(right)} |")

    L.append("\n### Paired differences (descriptive)\n")
    L.append("| comparison | diff [95% CI] | p |")
    L.append("|---|---|---|")
    c2, m2, r2 = S["re2"]
    c3, m3, r3 = S["re3"]
    g2, _, q2 = S["re2g"]
    g3, _, q3 = S["re3g"]

    def T(cs, runs, m, cond):
        return A6.t1(cs, runs, m, cond) if run_of(runs, m, cond) else {}

    def R(cs, meth, key):
        return EV.top1(cs, meth[key]) if meth.get(key) else {}

    sc2, sc3 = EV.top1(g2, summary_count(g2)), EV.top1(g3, summary_count(g3))
    comps = []
    for m in (DEP, m7):
        comps += [
            (f"RE3 summary_count - g_full ({m})", g3, sc3, T(g3, q3, m, "g_full")),
            (f"RE2 g_full - g_nolog ({m})", g2, T(g2, q2, m, "g_full"), T(g2, q2, m, "g_nolog")),
            (f"RE3 g_full - g_nolog ({m})", g3, T(g3, q3, m, "g_full"), T(g3, q3, m, "g_nolog")),
            (f"RE3 g_nolog - summary_count ({m})", g3, T(g3, q3, m, "g_nolog"), sc3),
            (f"RE2 g_full ({m}) - deployed agent annotated ({m})", g2, T(g2, q2, m, "g_full"), T(c2, r2, m, "annotated")),
            (f"RE3 g_full ({m}) - deployed agent annotated ({m})", g3, T(g3, q3, m, "g_full"), T(c3, r3, m, "annotated")),
        ]
    if m7 != DEP:
        comps.append((f"RE2 summary_count - g_full ({m7})", g2, sc2, T(g2, q2, m7, "g_full")))
    for suite, cs, gs, meth, qq in (("RE2", c2, g2, m2, q2), ("RE3", c3, g3, m3, q3)):
        for key in ("rcaeval:nsigma", "simplerca", "detector_count"):
            comps.append((f"{suite} g_full ({DEP}) - {key}", gs, T(gs, qq, DEP, "g_full"), R(cs, meth, key)))
        comps.append((f"{suite} summary_count - {'rcaeval:nsigma'}", gs, sc2 if suite == "RE2" else sc3,
                      R(cs, meth, "rcaeval:nsigma")))
    for lab, cs, a_, b_ in comps:
        if not a_ or not b_ or not (set(a_) & set(b_)):
            continue
        r = EV.paired(cs, a_, b_)
        L.append(f"| {lab} | {A6.fmt(r)} | {r['p_perm']:.4f} |")
    L.append(f"\nsummary_count AC@1: RE2 {np.mean(list(sc2.values())):.3f}, RE3 {np.mean(list(sc3.values())):.3f}")

    L.append("\n### Checks\n")
    for suite in ("re2g", "re3g"):
        c, _, r = S[suite]
        for m in (DEP, m7):
            d = run_of(r, m, "g_nolog")
            if d:
                L.append(f"- {suite} {m} g_nolog: prompts with an example log line left: "
                         f"{sum(1 for v in d.values() if (v.get('anon_leaks') or 0) > 0)}/{len(d)}")
        L.append(f"- {suite}: cases {len(c)}, build failures {sum(1 for x in c if x.get('build_failed'))}")
    path = os.path.join(a.out, "re3", "amendment7.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(a.out, "re3", "amendment7.json"), "w") as f:
        json.dump(J, f, indent=1, default=float)
    print("wrote", path)


if __name__ == "__main__":
    main()
