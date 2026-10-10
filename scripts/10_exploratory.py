"""Verdicts and exploratory analyses (PROTOCOL_V3_AMENDMENT_1.md).

Everything here is labelled in the paper as either (a) a restatement of a
pre-registered verdict, with the exact permutation p-value next to the
pre-registered Monte Carlo one, or (b) exploratory and post hoc. The frozen
analysis (06_evaluate.py) is not changed.

usage: python scripts/10_exploratory.py --ctx out/re2 [--ctx-chronic out/re2_chronic]
writes <ctx>/exploratory.md
"""
import argparse
import collections
import glob
import importlib.util
import itertools
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from rcastudy import config as C  # noqa: E402

spec = importlib.util.spec_from_file_location("ev", os.path.join(HERE, "06_evaluate.py"))
EV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EV)

DEP = C.DEPLOYED_MODEL
MODELS = sorted(C.MODELS)


def exact_p(cases, diff):
    """Exact two-sided cluster sign-flip p (enumeration over non-zero
    clusters; Monte Carlo with 200,000 draws above 22 clusters)."""
    d = np.array([sum(g) for g in EV._clusters(cases, diff)], dtype=float)
    d = d[d != 0]
    if len(d) == 0:
        return 1.0, 0
    t = abs(d.sum())
    if len(d) <= 22:
        signs = np.array(list(itertools.product([-1.0, 1.0], repeat=len(d))))
        return float(np.mean(np.abs(signs @ d) >= t - 1e-12)), len(d)
    rng = np.random.default_rng(C.SEED)
    flips = rng.choice([-1.0, 1.0], size=(200000, len(d)))
    return float(np.mean(np.abs(flips @ d) >= t - 1e-12)), len(d)


def holm(ps):
    return EV.holm(ps)


def fmt(r):
    return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx", required=True)
    ap.add_argument("--ctx-chronic", default=None)
    a = ap.parse_args()
    cases = EV.load_jsonl(os.path.join(a.ctx, "contexts.jsonl"))
    flagged = [c for c in cases if c["flagged"]]
    meth = {}
    for f in ("ranks_nonllm.json", "ranks_classifiers.json", "ranks_rcaeval.json"):
        p = os.path.join(a.ctx, f)
        if os.path.exists(p):
            meth.update(json.load(open(p)))
    runs = {}
    for p in glob.glob(os.path.join(a.ctx, "llm", "*.jsonl")):
        tag, name = os.path.basename(p)[:-6].split("__", 1)
        runs[(tag, name)] = EV.load_llm(p)
    R = lambda tag, m, c: runs.get((tag, f"{m}__{c}"), {})  # noqa: E731
    rank = lambda d: {k: v["ranking"] for k, v in d.items()}  # noqa: E731
    L = ["# Verdicts and exploratory analyses (10_exploratory.py)\n",
         "Section 1 restates pre-registered verdicts. Every other section is exploratory and post hoc.\n"]

    # ------------------------------------------------ 1. verdicts with exact p
    L.append("## 1. Pre-registered verdicts (Monte Carlo p as pre-registered; exact p alongside)\n")
    dep = rank(R("main", DEP, "annotated"))
    t_dep = EV.top1(cases, dep)
    lr = EV.paired(cases, EV.top1(cases, meth["lr_visible"]), t_dep)
    verdict = "supported" if lr["ci"][0] > -0.05 else "not supported"
    sup = " (superior: the interval excludes 0)" if lr["ci"][0] > 0 else ""
    L.append(f"- **P2** lr_visible minus deployed: {fmt(lr)}; non-inferiority margin -0.05 -> **{verdict}**{sup}.")
    p3a, p3b = [], []
    for m in MODELS:
        A_, S_, Rp = R("main", m, "annotated"), R("main", m, "stripped"), R("rep2", m, "annotated")
        note = [c for c in cases if c["n_notes"] > 0 and c["case_id"] in A_ and c["case_id"] in S_ and c["case_id"] in Rp]
        ch = lambda X_, Y_, cs: {c["case_id"]: int(X_[c["case_id"]]["ranking"][0] != Y_[c["case_id"]]["ranking"][0]) for c in cs}  # noqa: E731
        a1, b1 = ch(A_, S_, note), ch(A_, Rp, note)
        r = EV.paired(note, a1, b1)
        r["exact"], r["k"] = exact_p(note, {k: a1[k] - b1[k] for k in a1})
        p3a.append((m, r))
        D_ = R("main", m, "decoy")
        ids = [c for c in cases if c["case_id"] in D_ and c["case_id"] in S_ and c["decoy"]["service"]]
        fol = {c["case_id"]: int(D_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
        base = {c["case_id"]: int(S_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
        r = EV.paired(ids, fol, base)
        r["exact"], r["k"] = exact_p(ids, {k: fol[k] - base[k] for k in fol})
        r["rate"] = r["a"] / r["n"]
        p3b.append((m, r))
    for name, fam in (("P3a", p3a), ("P3b", p3b)):
        hm = holm([r["p_perm"] for _, r in fam])
        he = holm([r["exact"] for _, r in fam])
        for (m, r), h1, h2 in zip(fam, hm, he):
            v = "supported" if (h1 < 0.05 and r["diff"] > 0) else "not supported"
            extra = ""
            if (h2 < 0.05) != (h1 < 0.05):
                extra = " **(borderline: the exact test gives the opposite verdict; both reported)**"
            half = (f"; decoy named first in {r['rate']:.0%} of cases -> "
                    f"{'outweighs' if r['rate'] > 0.5 else 'does not outweigh'} the evidence (rule: > 50%)") if name == "P3b" else ""
            L.append(f"- **{name} {m}**: {fmt(r)}; MC p {r['p_perm']:.4f} (Holm {h1:.4f}); exact p {r['exact']:.2e} "
                     f"over {r['k']} non-zero clusters (Holm {h2:.4f}) -> **{v}**{extra}{half}.")
    # P3c
    sets_a = [R("main", m, "annotated") for m in MODELS]
    sets_s = [R("main", m, "stripped") for m in MODELS]
    ids = [c for c in cases if c["n_notes"] > 0 and all(c["case_id"] in x for x in sets_a + sets_s)]
    ag = {c["case_id"]: int(len({x[c["case_id"]]["ranking"][0] for x in sets_a}) == 1) for c in ids}
    gs = {c["case_id"]: int(len({x[c["case_id"]]["ranking"][0] for x in sets_s}) == 1) for c in ids}
    r = EV.paired(ids, ag, gs)
    ex, k = exact_p(ids, {i: ag[i] - gs[i] for i in ag})
    L.append(f"- **P3c**: agree annotated {r['a']}/{r['n']} vs stripped {r['b']}/{r['n']}; {fmt(r)}; "
             f"MC p {r['p_perm']:.4f}; exact {ex:.3f} -> **{'supported' if r['p_perm'] < 0.05 and r['diff'] > 0 else 'not supported'}**.")
    an = R("main", DEP, "anon")
    ids = [c for c in cases if c["case_id"] in an and c["case_id"] in dep]
    r = EV.paired(ids, EV.top1(ids, rank(an)), EV.top1(ids, dep), level=0.90)
    eq = r["ci"][0] > -0.05 and r["ci"][1] < 0.05
    L.append(f"- **RQ4**: anon minus named {fmt(r)} (90% CI) -> equivalence within ±0.05 **{'shown' if eq else 'not shown'}**; "
             f"no change detected (p {r['p_perm']:.3f}).")

    # ------------------------------------------------ 2. flagged-only paired
    L.append("\n## 2. Exploratory: paired AC@1 differences on flagged cases only (deployed minus comparator)\n")
    comps = [m for m in ("lr_visible", "lr_visible_loso", "detector_count", "first_affected", "simplerca",
                         "largest_anomaly") if m in meth]
    comps += sorted(m for m in meth if m.startswith("rcaeval:"))
    L.append("| comparator | all cases | flagged only |\n|---|---|---|")
    tf = EV.top1(flagged, dep)
    for m in comps:
        r1 = EV.paired(cases, t_dep, EV.top1(cases, meth[m]))
        r2 = EV.paired(flagged, tf, EV.top1(flagged, meth[m]))
        L.append(f"| {m} | {fmt(r1)} | {fmt(r2)} |")

    # ------------------------------------------------ 3. position
    L.append("\n## 3. Exploratory: position in the AFFECTED SERVICES line\n")
    L.append("| model | top-1 = first listed (multi-service cases) | P(correct \\| root listed first) | P(correct \\| root not first) |")
    L.append("|---|---|---|---|")
    multi = [c for c in flagged if len(c["context"]["affected_services"]) > 1]
    for m in MODELS:
        A_ = R("main", m, "annotated")
        cs = [c for c in multi if c["case_id"] in A_]
        canon = lambda s: s.replace("-db", "")  # noqa: E731
        first = {c["case_id"]: canon(c["context"]["affected_services"][0]) for c in cs}
        same = sum(A_[c["case_id"]]["ranking"][0] == first[c["case_id"]] for c in cs)
        rf = [c for c in cs if first[c["case_id"]] == c["gt"]["root_service"]]
        rn = [c for c in cs if first[c["case_id"]] != c["gt"]["root_service"]]
        acc = lambda L_: sum(A_[c["case_id"]]["ranking"][0] == c["gt"]["root_service"] for c in L_) / max(len(L_), 1)  # noqa: E731
        L.append(f"| {m} | {same}/{len(cs)} | {acc(rf):.2f} (n={len(rf)}) | {acc(rn):.2f} (n={len(rn)}) |")
    for k_ in (1, 2):
        sh = R(f"order{k_}", DEP, "shuffled")
        if sh:
            ids = [c for c in flagged if c["case_id"] in sh]
            r = EV.paired(ids, EV.top1(ids, rank(sh)), EV.top1(ids, dep))
            L.append(f"\nShuffled order {k_} ({DEP}): AC@1 {r['a']/r['n']:.3f} vs deployed order {r['b']/r['n']:.3f}; "
                     f"difference {fmt(r)}, p {r['p_perm']:.4f}")

    # ------------------------------------------------ 4. run-to-run noise
    L.append("\n## 4. Exploratory: run-to-run variation on identical prompts\n")
    L.append("No-NOTE cases: the annotated and stripped prompts are byte-identical, so a change is pure run-to-run variation.\n")
    L.append("| model | top-1 changed (all) | OB | SS | TT |\n|---|---|---|---|---|")
    for m in MODELS:
        A_, S_ = R("main", m, "annotated"), R("main", m, "stripped")
        row = []
        for sysn in (None, "ob", "ss", "tt"):
            cs = [c for c in flagged if c["n_notes"] == 0 and (sysn is None or c["system"] == sysn)
                  and c["case_id"] in A_ and c["case_id"] in S_]
            n = sum(A_[c["case_id"]]["ranking"][0] != S_[c["case_id"]]["ranking"][0] for c in cs)
            row.append(f"{n}/{len(cs)}")
        L.append(f"| {m} | " + " | ".join(row) + " |")
    reps = [R(t, DEP, "annotated") for t in ("main", "repA", "repB", "repC")]
    reps = [x for x in reps if x]
    if len(reps) >= 3:
        accs = [sum(x[c["case_id"]]["ranking"][0] == c["gt"]["root_service"] for c in flagged if c["case_id"] in x)
                / len(flagged) for x in reps]
        maj = 0
        for c in flagged:
            tops = [x[c["case_id"]]["ranking"][0] for x in reps if c["case_id"] in x]
            cnt = collections.Counter(tops).most_common()
            maj += int(cnt[0][0] == c["gt"]["root_service"] and (len(cnt) == 1 or cnt[0][1] > cnt[1][1]))
        L.append(f"\nRepeated runs of {DEP} (annotated, flagged cases, {len(reps)} runs): AC@1 per run "
                 f"{', '.join(f'{x:.3f}' for x in accs)}; mean {np.mean(accs):.3f}, SD {np.std(accs, ddof=1):.3f}; "
                 f"unique-plurality AC@1 {maj/len(flagged):.3f}")

    # ------------------------------------------------ 5. chronic alarms
    L.append("\n## 5. Exploratory: always-on alarms\n")
    L.append("| system | most often flagged non-root service | flagged in | " +
             " | ".join(f"{m} names it first" for m in MODELS) + " |")
    L.append("|---|---|---|" + "---|" * len(MODELS))
    for sysn in ("ob", "ss", "tt"):
        cs = [c for c in flagged if c["system"] == sysn]
        cnt = collections.Counter(s.replace("-db", "") for c in cs for s in c["context"]["affected_services"]
                                  if s.replace("-db", "") != c["gt"]["root_service"])
        svc, n = cnt.most_common(1)[0]
        names = []
        for m in MODELS:
            A_ = R("main", m, "annotated")
            names.append(f"{sum(A_[c['case_id']]['ranking'][0] == svc for c in cs if c['case_id'] in A_)}/{len(cs)}")
        L.append(f"| {sysn} | {svc} | {n}/{len(cs)} | " + " | ".join(names) + " |")
    if a.ctx_chronic:
        cc = EV.load_jsonl(os.path.join(a.ctx_chronic, "contexts.jsonl"))
        ccf = {c["case_id"]: c for c in cc}
        L.append(f"\nE3 baseline-aware log alarms: flagged cases {sum(c['flagged'] for c in cc)}/270 "
                 f"(frozen pipeline: {len(flagged)}/270).")
        chr_run = EV.load_llm(os.path.join(a.ctx_chronic, "llm", f"main__{DEP}__annotated.jsonl")) \
            if os.path.exists(os.path.join(a.ctx_chronic, "llm", f"main__{DEP}__annotated.jsonl")) else {}
        nonllm_c = json.load(open(os.path.join(a.ctx_chronic, "ranks_nonllm.json")))
        rows = [("deployed model", dep, rank(chr_run))] if chr_run else []
        rows.append(("detector_count", meth["detector_count"], nonllm_c["detector_count"]))
        L.append("\n| method | system | AC@1 frozen pipeline | AC@1 with alarm filter | difference [95% CI] |")
        L.append("|---|---|---|---|---|")
        for label, r_old, r_new in rows:
            for sysn in ("ob", "ss", "tt", "all"):
                cs = [c for c in cases if sysn == "all" or c["system"] == sysn]
                cs_new = [ccf[c["case_id"]] for c in cs]
                t_new = EV.top1(cs_new, r_new)
                t_old = EV.top1(cs, r_old)
                r = EV.paired(cs, t_new, t_old)
                L.append(f"| {label} | {sysn} | {r['b']/r['n']:.3f} | {r['a']/r['n']:.3f} | {fmt(r)} |")

    # ------------------------------------------------ 6. decoy detail
    L.append("\n## 6. Exploratory: decoy detail\n")
    L.append("| model | system | decoy first: decoy | placebo | stripped | decoy in top 5: decoy | placebo | stripped |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        D_, S_, P_ = R("main", m, "decoy"), R("main", m, "stripped"), R("main", m, "placebo")
        for sysn in ("ob", "ss", "tt", "all"):
            cs = [c for c in flagged if (sysn == "all" or c["system"] == sysn) and c["decoy"]["service"]
                  and c["case_id"] in D_ and c["case_id"] in S_]
            f1 = lambda X_: sum(X_[c["case_id"]]["ranking"][0] == c["decoy"]["service"] for c in cs if c["case_id"] in X_)  # noqa: E731
            f5 = lambda X_: sum(c["decoy"]["service"] in X_[c["case_id"]]["ranking"][:5] for c in cs if c["case_id"] in X_)  # noqa: E731
            pl1 = f"{f1(P_)}" if P_ else "-"
            pl5 = f"{f5(P_)}" if P_ else "-"
            L.append(f"| {m} | {sysn} | {f1(D_)}/{len(cs)} | {pl1} | {f1(S_)} | {f5(D_)} | {pl5} | {f5(S_)} |")

    # ------------------------------------------------ 7. anonymisation detail
    L.append("\n## 7. Exploratory: anonymisation by system and leak status\n")
    L.append("| subset | n | named AC@1 | anonymised AC@1 | difference [95% CI] |\n|---|---|---|---|---|")
    for label, sel in (("OB", lambda c: c["system"] == "ob"), ("SS", lambda c: c["system"] == "ss"),
                       ("TT", lambda c: c["system"] == "tt"),
                       ("no leaked name", lambda c: (an.get(c["case_id"], {}).get("anon_leaks") or 0) == 0),
                       ("leaked name", lambda c: (an.get(c["case_id"], {}).get("anon_leaks") or 0) > 0)):
        cs = [c for c in flagged if c["case_id"] in an and sel(c)]
        if not cs:
            continue
        r = EV.paired(cs, EV.top1(cs, rank(an)), EV.top1(cs, dep))
        L.append(f"| {label} | {len(cs)} | {r['b']/r['n']:.3f} | {r['a']/r['n']:.3f} | {fmt(r)} |")

    # ------------------------------------------------ 8. natural NOTEs
    L.append("\n## 8. Exploratory: what the natural NOTEs pointed at\n")
    hit = tot = 0
    for c in flagged:
        if c["n_notes"] == 0:
            continue
        for line in c["summary"]["annotated"].split("\n"):
            if line.lstrip().startswith("NOTE:"):
                tot += 1
                m_ = re.findall(r"[\w-]+", line)
                hit += int(c["gt"]["root_service"] in {w.replace("-db", "") for w in m_})
    L.append(f"NOTE lines mentioning the root service: {hit}/{tot}")

    out = os.path.join(a.ctx, "exploratory.md")
    with open(out, "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
