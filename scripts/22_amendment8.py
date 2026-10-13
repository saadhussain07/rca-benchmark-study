"""Amendment 8 analyses (PROTOCOL_V3_AMENDMENT_8.md).

Part A, 2x2 on the deployed agent's flagged cases (RE2 + RE3 pooled), deployed model:
  evidence  E_d = the deployed agent's user message, E_g = the generic user message
  prompt    P_d = the deployed system prompt,        P_g = the generic system prompt
  cells: E_d P_d = annotated; E_g P_g = g_full; E_g P_d = x_dsys_guser; E_d P_g = x_gsys_duser
  H8a  evidence effect  ((E_g P_g + E_g P_d) - (E_d P_g + E_d P_d)) / 2  > 0
  H8b  prompt effect    ((E_g P_g + E_d P_g) - (E_g P_d + E_d P_d)) / 2  (two-sided)
Part B, onset in the generic pipeline (RE2 + RE3, all cases):
  H8c  g_full at the given onset - g_full with the onset 120 s late  > 0
Holm over H8a, H8b, H8c. Everything else is descriptive.

usage: python scripts/22_amendment8.py --out out --pilot out/pilot_re3.txt
writes out/re3/amendment8.md and .json
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
CELLS = (("EdPd", "agent", "annotated"), ("EgPg", "generic", "g_full"),
         ("EgPd", "agent", "x_dsys_guser"), ("EdPg", "agent", "x_gsys_duser"))


def rank(d):
    return {k: v["ranking"] for k, v in d.items()}


def run_of(runs, m, cond, tag="main"):
    return runs.get((tag, f"{m}__{cond}"), {})


def cells(S, suites, model, pilot=frozenset()):
    """Per-case 0/1 correctness in the four cells, on flagged cases that have all four."""
    cs, y = [], {k: {} for k, _, _ in CELLS}
    for s in suites:
        c, _, r = S[s]
        _, _, rg = S[s + "g"]
        fl = [x for x in c if x["flagged"] and x["case_id"] not in pilot]
        runs = {k: (run_of(r, model, cond) if src == "agent" else run_of(rg, model, cond)) for k, src, cond in CELLS}
        keep = [x for x in fl if all(x["case_id"] in runs[k] for k in runs)]
        cs += keep
        for k in runs:
            y[k].update(EV.top1(keep, rank(runs[k])))
    return cs, y


def effects(cs, y):
    ids = [c["case_id"] for c in cs]
    ev_g = {i: (y["EgPg"][i] + y["EgPd"][i]) / 2 for i in ids}
    ev_d = {i: (y["EdPg"][i] + y["EdPd"][i]) / 2 for i in ids}
    pr_g = {i: (y["EgPg"][i] + y["EdPg"][i]) / 2 for i in ids}
    pr_d = {i: (y["EgPd"][i] + y["EdPd"][i]) / 2 for i in ids}
    inter_a = {i: y["EgPg"][i] - y["EdPg"][i] for i in ids}
    inter_b = {i: y["EgPd"][i] - y["EdPd"][i] for i in ids}
    return (A6.paired(cs, ev_g, ev_d), A6.paired(cs, pr_g, pr_d), A6.paired(cs, inter_a, inter_b))


def onset(S, model, shift, pilot=frozenset()):
    cs, a, b = [], {}, {}
    for s in ("re2", "re3"):
        c0, _, r0 = S[s + "g"]
        key = f"{s}g{shift:+d}"
        if key not in S:
            continue
        c1, _, r1 = S[key]
        R0, R1 = run_of(r0, model, "g_full"), run_of(r1, model, "g_full")
        if not R0 or not R1:
            continue
        c0 = [x for x in c0 if x["case_id"] not in pilot]
        cs += c0
        by1 = {x["case_id"]: x for x in c1}
        a.update(EV.top1(c0, rank(R0)))
        b.update(EV.top1([by1[x["case_id"]] for x in c0 if x["case_id"] in by1], rank(R1)))
    return cs, a, b


def family(S, pilot=frozenset()):
    out = {}
    cs, y = cells(S, ("re2", "re3"), DEP, pilot)
    e, p, _ = effects(cs, y)
    out["H8a evidence effect (generic - deployed user message), RE2+RE3 flagged"] = e
    out["H8b prompt effect (generic - deployed system prompt), RE2+RE3 flagged"] = p
    oc, a, b = onset(S, DEP, 120, pilot)
    out["H8c generic g_full: given onset - onset +120 s, RE2+RE3"] = A6.paired(oc, a, b)
    keys = list(out)
    for k, h in zip(keys, EV.holm([out[k]["p_perm"] for k in keys])):
        out[k]["p_holm"] = h
    for k, h in zip(keys, EV.holm([out[k]["p_exact"] for k in keys])):
        out[k]["p_holm_exact"] = h
    v = {}
    sig = lambda k: out[k]["p_holm"] < 0.05  # noqa: E731
    ka, kb, kc = keys
    v["H8a"] = "supported" if sig(ka) and out[ka]["diff"] > 0 else ("contradicted" if sig(ka) else "not supported")
    v["H8b"] = ("generic prompt better" if out[kb]["diff"] > 0 else "deployed prompt better") if sig(kb) else "no prompt effect detected"
    v["H8c"] = "supported" if sig(kc) and out[kc]["diff"] > 0 else ("contradicted" if sig(kc) else "not supported")
    return out, v, cs, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--pilot", default="out/pilot_re3.txt")
    a = ap.parse_args()
    S = {}
    for key, d in (("re2", "re2"), ("re3", "re3"), ("re2g", "re2_generic"), ("re3g", "re3_generic"),
                   ("re2g+120", "re2_generic_shift120"), ("re3g+120", "re3_generic_shift120"),
                   ("re2g-120", "re2_generic_shift-120"), ("re3g-120", "re3_generic_shift-120")):
        if os.path.exists(os.path.join(a.out, d, "contexts.jsonl")):
            S[key] = A3.load(os.path.join(a.out, d))
    pilot = {l.strip() for l in open(a.pilot) if l.strip()} if a.pilot and os.path.exists(a.pilot) else set()
    L = ["# Amendment 8 analyses (22_amendment8.py)\n",
         f"Deployed model {DEP}. Part A on the deployed agent's flagged cases that have all four cells; "
         "Part B on all cases. Holm over H8a, H8b, H8c.\n"]
    J = {}
    for label, pl in (("Primary", frozenset()), (f"Sensitivity: without {len(pilot)} RE3 pilot cases", frozenset(pilot))):
        q, v, cs, y = family(S, pl)
        L.append(f"## {label}\n")
        L.append(f"Part A cases: {len(cs)}\n")
        L.append("| test | diff [95% CI] | p | p Holm | exact p Holm |")
        L.append("|---|---|---|---|---|")
        for k, r in q.items():
            L.append(f"| {k} | {A6.fmt(r)} | {r['p_perm']:.4f} | {r['p_holm']:.4f} | {r['p_holm_exact']:.4f} |")
        L.append("")
        for k, s in v.items():
            L.append(f"- **{k}**: {s}")
        L.append("")
        J[label] = {"tests": q, "verdicts": v}

    L.append("## Descriptive\n")
    L.append("### 2x2 cell accuracy (AC@1 on flagged cases with all four cells)\n")
    L.append("| suite | n | E_d P_d (annotated) | E_d P_g | E_g P_d | E_g P_g (g_full) | evidence effect | prompt effect | interaction |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for suites, lab in ((("re2",), "re2"), (("re3",), "re3"), (("re2", "re3"), "both")):
        cs, y = cells(S, suites, DEP)
        if not cs:
            continue
        m = {k: np.mean([y[k][c["case_id"]] for c in cs]) for k in y}
        e, p, i = effects(cs, y)
        L.append(f"| {lab} | {len(cs)} | {m['EdPd']:.3f} | {m['EdPg']:.3f} | {m['EgPd']:.3f} | {m['EgPg']:.3f} | "
                 f"{A6.fmt(e)} | {A6.fmt(p)} | {A6.fmt(i)} |")

    L.append("\n### Generic pipeline under onset shifts (g_full, all cases)\n")
    L.append("| suite | given onset | -120 s | +120 s |")
    L.append("|---|---|---|---|")
    for s in ("re2", "re3"):
        cells_ = []
        for key in (s + "g", s + "g-120", s + "g+120"):
            if key in S and run_of(S[key][2], DEP, "g_full"):
                c, _, r = S[key]
                cells_.append(f"{np.mean(list(EV.top1(c, rank(run_of(r, DEP, 'g_full'))).values())):.3f}")
            else:
                cells_.append("-")
        L.append(f"| {s} | " + " | ".join(cells_) + " |")
    for sh in (-120, 120):
        oc, a_, b_ = onset(S, DEP, sh)
        if oc:
            r = A6.paired(oc, a_, b_)
            L.append(f"\ng_full given onset minus onset {sh:+d} s (RE2+RE3): {A6.fmt(r)}, p {r['p_perm']:.4f}")

    L.append("\n### Checks\n")
    for s in ("re2", "re3"):
        c, _, r = S[s]
        fl = sum(1 for x in c if x["flagged"])
        for cond in ("x_dsys_guser", "x_gsys_duser"):
            d = run_of(r, DEP, cond)
            none = sum(1 for v in d.values() if v["votes"] and v["votes"][0].get("n_listed", 1) == 0)
            L.append(f"- {s} {cond}: {len(d)}/{fl} flagged cases run; answers with no candidate named: {none}")
    for key in ("re2g+120", "re2g-120", "re3g+120", "re3g-120"):
        if key in S:
            c = S[key][0]
            L.append(f"- {key}: {len(c)} cases, build failures {sum(1 for x in c if x.get('build_failed'))}")
    path = os.path.join(a.out, "re3", "amendment8.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(a.out, "re3", "amendment8.json"), "w") as f:
        json.dump(J, f, indent=1, default=float)
    print("wrote", path)


if __name__ == "__main__":
    main()
