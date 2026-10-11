"""Amendment 3 analyses (PROTOCOL_V3_AMENDMENT_3.md).

B  RE3 replication: the confirmatory quantities of RE2, recomputed on RE3 and
   set beside the RE2 estimates, with the replication verdict fixed in the
   amendment. Run 06_evaluate.py on out/re3 as well; it gives the full tables.
C  Full anonymisation (exploratory): anon_full vs annotated per model on RE2,
   and vs the original anon condition for the deployed model.

usage:
  python scripts/11_amendment3.py --ctx-re2 out/re2 --ctx-re3 out/re3 --pilot out/pilot_re3.txt
writes out/re3/amendment3.md
"""
import argparse
import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from rcastudy import config as C  # noqa: E402

spec = importlib.util.spec_from_file_location("ev", os.path.join(HERE, "06_evaluate.py"))
EV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EV)

DEP = C.DEPLOYED_MODEL
MODELS = sorted(C.MODELS)
COMPARATORS = EV.OUR_COMPARATORS + [f"rcaeval:{m}" for m in EV.PRIMARY_RCAEVAL]


def load(ctx):
    cases = EV.load_jsonl(os.path.join(ctx, "contexts.jsonl"))
    meth = {}
    for f in ("ranks_nonllm.json", "ranks_classifiers.json", "ranks_rcaeval.json", "ranks_transfer.json"):
        p = os.path.join(ctx, f)
        if os.path.exists(p):
            meth.update(json.load(open(p)))
    runs = {}
    for p in glob.glob(os.path.join(ctx, "llm", "*.jsonl")):
        tag, name = os.path.basename(p)[:-6].split("__", 1)
        runs[(tag, name)] = EV.load_llm(p)
    return cases, meth, runs


def rank(d):
    return {k: v["ranking"] for k, v in d.items()}


def fmt(r):
    return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]"


def quantities(cases, meth, runs):
    """Every confirmatory quantity of the protocol that RE3 can carry.
    Methods without any ranking are scored as chance (protocol section 6)."""
    R = lambda m, c: runs.get(("main", f"{m}__{c}"), {})  # noqa: E731
    out = {}
    dep = rank(R(DEP, "annotated"))
    if not dep:
        return out
    t_dep = EV.top1(cases, dep)
    rq = []
    for m in COMPARATORS:
        r = EV.paired(cases, t_dep, EV.top1(cases, meth.get(m, {})))
        r["covered"] = sum(1 for c in cases if c["case_id"] in meth.get(m, {}))
        rq.append((m, r))
    for (m, r), h in zip(rq, EV.holm([r["p_perm"] for _, r in rq])):
        r["p_holm"] = h
        out[f"RQ1/RQ2 deployed - {m}"] = r
    for clf in ("lr_visible", "lr_visible_re2train"):
        if clf in meth:
            r = EV.paired(cases, EV.top1(cases, meth[clf]), t_dep)
            r["verdict"] = ("supported" if r["ci"][0] > -EV.NI_MARGIN else
                            "contradicted" if (r["ci"][1] < 0 and r["p_perm"] < 0.05) else "inconclusive")
            out[f"P2 {clf} - deployed"] = r
    p3b = []
    for m in MODELS:
        D_, S_ = R(m, "decoy"), R(m, "stripped")
        ids = [c for c in cases if c["case_id"] in D_ and c["case_id"] in S_ and c["decoy"]["service"]]
        if not ids:
            continue
        fol = {c["case_id"]: int(D_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
        base = {c["case_id"]: int(S_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
        r = EV.paired(ids, fol, base)
        r["rate"] = r["a"] / r["n"] if r["n"] else float("nan")
        p3b.append((m, r))
    for (m, r), h in zip(p3b, EV.holm([r["p_perm"] for _, r in p3b])):
        r["p_holm"] = h
        out[f"P3b {m}"] = r
    P_, D_ = R(DEP, "placebo"), R(DEP, "decoy")
    ids = [c for c in cases if c["case_id"] in P_ and c["case_id"] in D_ and c["decoy"]["service"]]
    if ids:
        fol = {c["case_id"]: int(D_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
        plc = {c["case_id"]: int(P_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
        out["decoy vs placebo (deployed)"] = EV.paired(ids, fol, plc)
    return out


def significant(key, r):
    if key.startswith("P2"):
        return r.get("verdict") == "supported"
    p = r.get("p_holm", r["p_perm"])
    return p < 0.05


def replication(key, r2, r3):
    """Verdict rule fixed in Amendment 3, section B4."""
    if r3 is None or r3["n"] == 0:
        return "not estimable"
    if key.startswith("P2"):
        return {"supported": "replicated" if r2.get("verdict") == "supported" else "supported on RE3 only",
                "inconclusive": "not replicated (inconclusive)",
                "contradicted": "contradicted"}[r3["verdict"]]
    sig2, sig3 = significant(key, r2), significant(key, r3)
    same = r3["diff"] != 0 and (r2["diff"] > 0) == (r3["diff"] > 0)
    if not sig2:
        return "RE2 not significant; RE3 " + (("significant, " + ("same sign" if same else "opposite sign"))
                                               if sig3 else "not significant")
    if same and sig3:
        return "replicated"
    if same:
        return "same direction, not significant"
    return "opposite direction" + (" (significant)" if sig3 else "")


def part_b(a, L):
    c2, m2, r2 = load(a.ctx_re2)
    c3, m3, r3 = load(a.ctx_re3)
    pilot = {l.strip() for l in open(a.pilot) if l.strip()} if a.pilot and os.path.exists(a.pilot) else set()
    L.append("## B. RE3 replication\n")
    sysn = sorted({c["system"] for c in c3})
    L.append("| system | cases | flagged | with NOTE | pilot cases |")
    L.append("|---|---|---|---|---|")
    for s in sysn + ["all"]:
        cs = [c for c in c3 if s == "all" or c["system"] == s]
        L.append(f"| {s} | {len(cs)} | {sum(c['flagged'] for c in cs)} | {sum(c['n_notes'] > 0 for c in cs)} | "
                 f"{sum(c['case_id'] in pilot for c in cs)} |")
    q2 = quantities(c2, m2, r2)
    q3 = quantities(c3, m3, r3)
    q3x = quantities([c for c in c3 if c["case_id"] not in pilot], m3, r3) if pilot else {}
    n_out = sum(c["case_id"] not in pilot for c in c3)
    L.append(f"\nRE3 estimates use all {len(c3)} cases (primary) and, in the last column, the {n_out} cases "
             "outside the pilot (sensitivity). Methods without a ranking on a case are scored as chance. "
             "p is the cluster permutation p; Holm within each family as in the protocol.\n")
    L.append("| quantity | RE2 | RE3 | RE3 p (Holm) | RE3 ranked cases | verdict | RE3 without pilot |")
    L.append("|---|---|---|---|---|---|---|")
    for k in list(q3) or list(q2):
        x2, x3, xx = q2.get(k), q3.get(k), q3x.get(k)
        p = f"{x3['p_perm']:.4f} ({x3['p_holm']:.4f})" if x3 and "p_holm" in x3 else (f"{x3['p_perm']:.4f}" if x3 else "-")
        cov = x3.get("covered", "") if x3 else ""
        extra = ""
        if k.startswith("P3b") and x3:
            extra = f"; decoy first {x3['a']}/{x3['n']}"
        if k.startswith("P2") and x3:
            extra = f"; {x3['verdict']}"
        L.append(f"| {k} | {fmt(x2) if x2 else '-'} | {fmt(x3) if x3 else '-'}{extra} | {p} | {cov} | "
                 f"{replication(k, x2, x3) if x2 else 'no RE2 counterpart'} | {fmt(xx) if xx else '-'} |")
    return q3


def part_c(a, L):
    cases, meth, runs = load(a.ctx_re2)
    L.append("\n## C. Full anonymisation on RE2 (exploratory)\n")
    L.append("anon_full minus annotated, AC@1, 90% cluster-bootstrap interval; equivalence margin +-0.05 "
             "(the RQ4 rule, applied here descriptively).\n")
    L.append("| model | system | n | AC@1 annotated | AC@1 anon_full | diff [90% CI] | p perm | within +-0.05 | "
             "prompts with any leak | answers naming a real service |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        F_ = runs.get(("main", f"{m}__anon_full"), {})
        A_ = runs.get(("main", f"{m}__annotated"), {})
        if not F_ or not A_:
            continue
        for s in sorted({c["system"] for c in cases}) + ["all"]:
            ids = [c for c in cases if c["case_id"] in F_ and c["case_id"] in A_ and (s == "all" or c["system"] == s)]
            if not ids:
                continue
            r = EV.paired(ids, EV.top1(ids, rank(F_)), EV.top1(ids, rank(A_)), level=0.90)
            eq = r["ci"][0] > -EV.NI_MARGIN and r["ci"][1] < EV.NI_MARGIN
            leak = sum(1 for c in ids if (F_[c["case_id"]].get("anon_leaks") or 0) > 0)
            real = 0
            for c in ids:
                names = {x.lower() for x in c["candidates"]}
                parsed = (F_[c["case_id"]]["votes"][0].get("parsed") or {})
                said = parsed.get("ranked_root_cause_services") or []
                said = said if isinstance(said, list) else [said]
                said = said + [parsed.get("root_cause_service")]
                real += int(any(isinstance(x, str) and x.strip().lower() in names for x in said))
            L.append(f"| {m} | {s} | {r['n']} | {r['b'] / r['n']:.3f} | {r['a'] / r['n']:.3f} | {fmt(r)} | "
                     f"{r['p_perm']:.4f} | {eq} | {leak}/{r['n']} | {real}/{r['n']} |")
    F_ = runs.get(("main", f"{DEP}__anon_full"), {})
    O_ = runs.get(("main", f"{DEP}__anon"), {})
    if F_ and O_:
        ids = [c for c in cases if c["case_id"] in F_ and c["case_id"] in O_]
        r = EV.paired(ids, EV.top1(ids, rank(F_)), EV.top1(ids, rank(O_)), level=0.90)
        L.append(f"\n{DEP}: anon_full minus anon (original RQ4 condition), all systems: {fmt(r)} (90% CI), "
                 f"p perm {r['p_perm']:.4f}, n {r['n']}.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx-re2", required=True)
    ap.add_argument("--ctx-re3", required=True)
    ap.add_argument("--pilot", default=None)
    a = ap.parse_args()
    L = ["# Amendment 3 analyses (11_amendment3.py)\n",
         "B is the pre-specified RE3 replication. C is exploratory. Neither changes a RE2 confirmatory verdict.\n"]
    q3 = part_b(a, L)
    part_c(a, L)
    with open(os.path.join(a.ctx_re3, "amendment3.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(a.ctx_re3, "amendment3.json"), "w") as f:
        json.dump(q3, f, indent=1, default=float)
    print("\n".join(L))


if __name__ == "__main__":
    main()
