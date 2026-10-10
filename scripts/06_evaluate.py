"""Score every ranking with RCAEval's own Evaluator and run the pre-registered
analyses (PROTOCOL_V3.md section 7).

usage: python scripts/06_evaluate.py --ctx out/re2 [--allow-incomplete]
writes out/re2/results.md and out/re2/results.json

Confirmatory statistic for every paired comparison: the difference in AC@1
(top-1 accuracy), with a 95% cluster-bootstrap interval and a cluster
sign-flip permutation p-value; clusters are (system, root service, fault).
Exact McNemar is reported alongside as a secondary, unclustered test.
"""
import argparse
import collections
import glob
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import config as C  # noqa: E402

try:
    from RCAEval.benchmark.evaluation import Evaluator
    from RCAEval.classes.graph import Node
except Exception:  # pragma: no cover
    Evaluator = Node = None

PRIMARY_RCAEVAL = ["nsigma", "baro", "circa", "e_diagnosis", "microcause", "mmnsigma", "mmbaro", "mmcirca"]
OUR_COMPARATORS = ["lr_visible", "detector_count", "first_affected", "simplerca", "largest_anomaly"]
NI_MARGIN = 0.05      # P2 non-inferiority and RQ4 equivalence margin (5 points)
N_BOOT, N_PERM = 2000, 10000


# ----------------------------------------------------------------- loading
def load_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_llm(path):
    """Last successful record per case (error records are ignored)."""
    out = {}
    for r in load_jsonl(path):
        if not r.get("error") and r.get("ranking"):
            out[r["case_id"]] = r
    return out


def chance_rank(c):
    """The one chance ranking of a case, shared by every method."""
    rest = sorted(c["candidates"])
    random.Random(f"{C.SEED}|fill|{c['case_id']}").shuffle(rest)
    return rest


def rank_of(c, ranks):
    r = ranks.get(c["case_id"])
    return r if r else chance_rank(c)


# ------------------------------------------------------------------ scoring
def score(cases, ranks):
    ev = Evaluator(max_k=5)
    for c in cases:
        ev.add_case(ranks=[Node(x, "unknown") for x in rank_of(c, ranks)],
                    answer=Node(c["gt"]["root_service"], "unknown"),
                    n_candidates=len(c["candidates"]) or None)
    return {"n": ev.num, "AC@1": ev.accuracy(1), "AC@3": ev.accuracy(3), "AC@5": ev.accuracy(5),
            "Avg@5": ev.average(5), "chance_Avg@5": ev.chance_average(5)}


def top1(cases, ranks):
    out = {}
    for c in cases:
        r = rank_of(c, ranks)
        out[c["case_id"]] = int(bool(r) and r[0] == c["gt"]["root_service"])
    return out


def avg5(c, r):
    return float(np.mean([int(c["gt"]["root_service"] in r[:k]) for k in range(1, 6)]))


def cluster_of(c):
    return (c["system"], c["gt"]["root_service"], c["fault"])


def _clusters(cases, values):
    g = collections.defaultdict(list)
    for c in cases:
        if c["case_id"] in values:
            g[cluster_of(c)].append(values[c["case_id"]])
    return list(g.values())


def boot_ci(cases, values, level=0.95):
    """Cluster-bootstrap interval for the mean of per-case values."""
    groups = _clusters(cases, values)
    if not groups:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(C.SEED)
    stats = []
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(groups), len(groups))
        vals = [v for i in pick for v in groups[i]]
        stats.append(np.mean(vals))
    a = (1 - level) / 2
    return float(np.percentile(stats, 100 * a)), float(np.percentile(stats, 100 * (1 - a)))


def perm_p(cases, diff):
    """Two-sided cluster sign-flip permutation test of mean(diff) = 0."""
    groups = [sum(g) for g in _clusters(cases, diff)]
    if not groups or all(d == 0 for d in groups):
        return 1.0
    t = abs(sum(groups))
    rng = np.random.default_rng(C.SEED)
    d = np.array(groups, dtype=float)
    flips = rng.choice([-1.0, 1.0], size=(N_PERM, len(d)))
    tstar = np.abs((flips * d).sum(axis=1))
    return float((np.sum(tstar >= t - 1e-12) + 1) / (N_PERM + 1))


def mcnemar(a, b):
    """Exact McNemar on paired 0/1 dicts. Returns (a_only, b_only, p)."""
    from scipy.stats import binomtest
    keys = sorted(set(a) & set(b))
    a_only = sum(1 for k in keys if a[k] and not b[k])
    b_only = sum(1 for k in keys if b[k] and not a[k])
    n = a_only + b_only
    return a_only, b_only, (binomtest(a_only, n, 0.5).pvalue if n else 1.0)


def paired(cases, a, b, level=0.95):
    """Paired comparison of two 0/1 dicts: mean(a - b), cluster CI,
    permutation p, McNemar."""
    keys = [c for c in cases if c["case_id"] in a and c["case_id"] in b]
    diff = {c["case_id"]: a[c["case_id"]] - b[c["case_id"]] for c in keys}
    a_only, b_only, p_mc = mcnemar({k: a[k] for k in diff}, {k: b[k] for k in diff})
    lo, hi = boot_ci(keys, diff, level)
    return {"n": len(keys), "a": sum(a[c["case_id"]] for c in keys), "b": sum(b[c["case_id"]] for c in keys),
            "diff": float(np.mean(list(diff.values()))) if diff else float("nan"),
            "ci": [lo, hi], "p_perm": perm_p(keys, diff), "a_only": a_only, "b_only": b_only, "p_mcnemar": p_mc}


def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def fmt_pair(r):
    return (f"{r['diff']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] | "
            f"{r['p_perm']:.4f} | {r['a_only']}/{r['b_only']} | {r['p_mcnemar']:.4f}")


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx", required=True)
    ap.add_argument("--allow-incomplete", action="store_true")
    a = ap.parse_args()
    cases = load_jsonl(os.path.join(a.ctx, "contexts.jsonl"))
    flagged = [c for c in cases if c["flagged"]]
    methods = {}
    for fname in ("ranks_nonllm.json", "ranks_classifiers.json", "ranks_rcaeval.json"):
        p = os.path.join(a.ctx, fname)
        if os.path.exists(p):
            methods.update(json.load(open(p)))
    llm, rep2 = {}, {}
    for p in sorted(glob.glob(os.path.join(a.ctx, "llm", "*.jsonl"))):
        tag, name = os.path.basename(p)[:-6].split("__", 1)
        if tag == "main":
            llm[name] = load_llm(p)
            methods[f"llm:{name}"] = {k: v["ranking"] for k, v in llm[name].items()}
        elif tag == "rep2":
            rep2[name] = load_llm(p)

    res = {"coverage": {}, "scores": {}, "scores_flagged": {}, "incomplete": {}, "rq1_rq2": [],
           "p2": {}, "rq3": {}, "anon": {}, "votecheck": {}}
    L = ["# Results (generated by 06_evaluate.py)\n"]

    # ---- completeness
    for name, recs in llm.items():
        cond = name.split("__")[1]
        need = {c["case_id"] for c in flagged if cond not in ("decoy", "placebo") or c["decoy"]["service"]}
        miss = sorted(need - set(recs))
        if miss:
            res["incomplete"][name] = miss
    if res["incomplete"]:
        L.append("**INCOMPLETE CELLS** (missing cases are scored as chance): " +
                 ", ".join(f"{k}: {len(v)}" for k, v in res["incomplete"].items()) + "\n")
        print("WARNING incomplete:", {k: len(v) for k, v in res["incomplete"].items()})
        if not a.allow_incomplete:
            print("Refusing to report. Finish the runs or pass --allow-incomplete.")
            sys.exit(2)

    systems = sorted({c["system"] for c in cases})
    subsets = {s: [c for c in cases if c["system"] == s] for s in systems}
    subsets["all"] = cases

    # ---- RQ0 coverage
    L.append("## Detector coverage\n\n| system | cases | build failed | flagged | with NOTE |\n|---|---|---|---|---|")
    for s, cs in subsets.items():
        row = {"cases": len(cs), "failed": sum(c.get("build_failed", False) for c in cs),
               "flagged": sum(c["flagged"] for c in cs), "with_note": sum(c["n_notes"] > 0 for c in cs)}
        res["coverage"][s] = row
        L.append(f"| {s} | {row['cases']} | {row['failed']} | {row['flagged']} | {row['with_note']} |")

    # ---- scores
    for label, key, only_flagged in (("all cases; unflagged and missing cases ranked by chance", "scores", False),
                                     ("flagged cases only", "scores_flagged", True)):
        L.append(f"\n## Scores ({label})\n")
        L.append("| method | system | n | AC@1 | AC@3 | AC@5 | Avg@5 | 95% CI Avg@5 | chance Avg@5 |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for m, rk in sorted(methods.items()):
            for s, cs in subsets.items():
                if only_flagged:
                    cs = [c for c in cs if c["flagged"]]
                if not cs:
                    continue
                sc = score(cs, rk)
                sc["ci"] = boot_ci(cs, {c["case_id"]: avg5(c, rank_of(c, rk)) for c in cs})
                res[key].setdefault(m, {})[s] = sc
                ch = sc["chance_Avg@5"]
                L.append(f"| {m} | {s} | {sc['n']} | {sc['AC@1']:.3f} | {sc['AC@3']:.3f} | {sc['AC@5']:.3f} | "
                         f"{sc['Avg@5']:.3f} | [{sc['ci'][0]:.3f}, {sc['ci'][1]:.3f}] | "
                         f"{(f'{ch:.3f}' if ch is not None else '-')} |")

    # ---- RQ1/RQ2 paired, deployed model vs comparators (pooled = confirmatory)
    dep = f"llm:{C.DEPLOYED_MODEL}__annotated"
    if dep in methods:
        comps = [m for m in OUR_COMPARATORS if m in methods]
        comps += [f"rcaeval:{m}" for m in PRIMARY_RCAEVAL if f"rcaeval:{m}" in methods]
        L.append(f"\n## RQ1/RQ2: AC@1 difference, {dep} minus comparator\n")
        L.append("Pooled rows are confirmatory (Holm across comparators); per-system rows are descriptive.\n")
        L.append("| system | comparator | diff [95% CI] | p (cluster perm) | LLM-only/comp-only | p (McNemar) | p Holm |")
        L.append("|---|---|---|---|---|---|---|")
        rows = []
        for s, cs in subsets.items():
            t_dep = top1(cs, methods[dep])
            for m in comps:
                r = paired(cs, t_dep, top1(cs, methods[m]))
                r.update({"system": s, "comparator": m})
                rows.append(r)
        pooled = [r for r in rows if r["system"] == "all"]
        for r, adj in zip(pooled, holm([r["p_perm"] for r in pooled])):
            r["p_holm"] = adj
        for r in rows:
            holm_txt = f"{r['p_holm']:.4f}" if "p_holm" in r else "-"
            L.append(f"| {r['system']} | {r['comparator']} | {fmt_pair(r)} | {holm_txt} |")
        res["rq1_rq2"] = rows
        if "lr_visible" in methods:
            r = paired(cases, top1(cases, methods["lr_visible"]), top1(cases, methods[dep]))
            verdict = ("supported" if r["ci"][0] > -NI_MARGIN else
                       "contradicted" if (r["ci"][1] < 0 and r["p_perm"] < 0.05) else "inconclusive")
            r["verdict"] = verdict
            res["p2"] = r
            L.append(f"\n**P2** (lr_visible minus deployed model, AC@1, margin -{NI_MARGIN}): "
                     f"{fmt_pair(r)} -> {verdict}")

    # ---- RQ3 annotations
    models = sorted({k.split("__")[0] for k in llm})
    L.append("\n## RQ3: annotations\n")
    p3a, p3b = [], []

    def changed(X_, Y_, cs):
        return {c["case_id"]: int(X_[c["case_id"]]["ranking"][0] != Y_[c["case_id"]]["ranking"][0]) for c in cs}

    for mdl in models:
        A_, S_, D_ = (llm.get(f"{mdl}__{c}") for c in ("annotated", "stripped", "decoy"))
        R_ = rep2.get(f"{mdl}__annotated")
        row = {}
        if A_ and S_:
            note = [c for c in cases if c["n_notes"] > 0 and c["case_id"] in A_ and c["case_id"] in S_]
            ctrl = [c for c in cases if c["n_notes"] == 0 and c["case_id"] in A_ and c["case_id"] in S_]
            row["note_changed"] = [sum(changed(A_, S_, note).values()), len(note)]
            row["ctrl_changed"] = [sum(changed(A_, S_, ctrl).values()), len(ctrl)]
            if R_:
                both = [c for c in note if c["case_id"] in R_]
                r = paired(both, changed(A_, S_, both), changed(A_, R_, both))
                row["p3a"] = r
                p3a.append(r)
        if D_ and S_:
            ids = [c for c in cases if c["case_id"] in D_ and c["case_id"] in S_ and c["decoy"]["service"]]
            fol = {c["case_id"]: int(D_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
            base = {c["case_id"]: int(S_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids}
            r = paired(ids, fol, base)
            harm_pool = [c for c in ids if S_[c["case_id"]]["ranking"][0] == c["gt"]["root_service"]]
            r["harm"] = [sum(fol[c["case_id"]] for c in harm_pool), len(harm_pool)]
            r["by_template"] = {t: [sum(fol[c["case_id"]] for c in ids if c["decoy"]["template"] == t),
                                    sum(1 for c in ids if c["decoy"]["template"] == t)]
                                for t in ("memory_pressure", "dependency")}
            row["p3b"] = r
            p3b.append(r)
            P_ = llm.get(f"{mdl}__placebo")
            if P_:
                ids2 = [c for c in ids if c["case_id"] in P_]
                plc = {c["case_id"]: int(P_[c["case_id"]]["ranking"][0] == c["decoy"]["service"]) for c in ids2}
                row["decoy_vs_placebo"] = paired(ids2, {k: fol[k] for k in plc}, plc)
        res["rq3"][mdl] = row
    for items in (p3a, p3b):
        for r, adj in zip(items, holm([r["p_perm"] for r in items])):
            r["p_holm"] = adj
    L.append("| model | NOTE cases changed (annot vs stripped) | no-NOTE changed | "
             "P3a: change(strip) - change(rerun) [CI] | p perm | p Holm |")
    L.append("|---|---|---|---|---|---|")
    for mdl in models:
        row = res["rq3"][mdl]
        nc, cc, r = row.get("note_changed"), row.get("ctrl_changed"), row.get("p3a")
        nc_t = f"{nc[0]}/{nc[1]}" if nc else "-"
        cc_t = f"{cc[0]}/{cc[1]}" if cc else "-"
        r_t = (f"{r['diff']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] | {r['p_perm']:.4f} | {r['p_holm']:.4f}"
               if r else "- | - | -")
        L.append(f"| {mdl} | {nc_t} | {cc_t} | {r_t} |")
    L.append("\n| model | decoy first (decoy) | same service first (stripped) | diff [CI] | p perm | p Holm | "
             "harm: correct under stripped, decoy first under decoy | by template |")
    L.append("|---|---|---|---|---|---|---|---|")
    for mdl in models:
        r = res["rq3"][mdl].get("p3b")
        if r:
            L.append(f"| {mdl} | {r['a']}/{r['n']} | {r['b']}/{r['n']} | {r['diff']:+.3f} [{r['ci'][0]:+.3f}, "
                     f"{r['ci'][1]:+.3f}] | {r['p_perm']:.4f} | {r['p_holm']:.4f} | {r['harm'][0]}/{r['harm'][1]} | "
                     f"{r['by_template']} |")
    for mdl in models:
        dv = res["rq3"][mdl].get("decoy_vs_placebo")
        if dv:
            L.append(f"\n{mdl}: decoy vs placebo (service named first): {dv['a']}/{dv['n']} vs {dv['b']}/{dv['n']}, "
                     f"diff {dv['diff']:+.3f} [{dv['ci'][0]:+.3f}, {dv['ci'][1]:+.3f}], p perm {dv['p_perm']:.4f}")
    agree = {}
    for cond in ("annotated", "stripped"):
        sets = [llm.get(f"{m}__{cond}") for m in models]
        if len(models) >= 2 and all(sets):
            ids = [c for c in cases if c["n_notes"] > 0 and all(c["case_id"] in x for x in sets)]
            agree[cond] = {c["case_id"]: int(len({x[c["case_id"]]["ranking"][0] for x in sets}) == 1) for c in ids}
    if len(agree) == 2:
        ids = [c for c in cases if c["case_id"] in agree["annotated"] and c["case_id"] in agree["stripped"]]
        r = paired(ids, agree["annotated"], agree["stripped"])
        res["rq3"]["p3c"] = r
        L.append(f"\n**P3c** all models agree on top-1, NOTE cases: annotated {r['a']}/{r['n']}, "
                 f"stripped {r['b']}/{r['n']}; {fmt_pair(r)}")

    # ---- RQ4 anonymisation (equivalence: 90% CI within +-margin)
    an, ann = llm.get(f"{C.DEPLOYED_MODEL}__anon"), llm.get(f"{C.DEPLOYED_MODEL}__annotated")
    if an and ann:
        ids = [c for c in cases if c["case_id"] in an and c["case_id"] in ann]
        r = paired(ids, top1(ids, {k: v["ranking"] for k, v in an.items()}),
                   top1(ids, {k: v["ranking"] for k, v in ann.items()}), level=0.90)
        r["equivalent"] = bool(r["ci"][0] > -NI_MARGIN and r["ci"][1] < NI_MARGIN)
        leaks = [v.get("anon_leaks") or 0 for v in an.values()]
        r["leaks"] = {"cases_with_leak": sum(x > 0 for x in leaks), "n": len(leaks)}
        res["anon"] = r
        L.append(f"\n## RQ4: anonymised minus named ({C.DEPLOYED_MODEL}), AC@1, 90% CI\n\n{fmt_pair(r)}; "
                 f"equivalent within +-{NI_MARGIN}: {r['equivalent']}; prompts with a leaked name: "
                 f"{r['leaks']['cases_with_leak']}/{r['leaks']['n']}")

    # ---- first-vote check (ties count as disagreement)
    for p in glob.glob(os.path.join(a.ctx, "llm", "votecheck__*.jsonl")):
        recs = load_llm(p)
        agree_n = 0
        for r in recs.values():
            tops = [v["ranking"][0] for v in r["votes"]]
            cnt = collections.Counter(tops).most_common()
            unique = len(cnt) == 1 or cnt[0][1] > cnt[1][1]
            agree_n += int(unique and tops[0] == cnt[0][0])
        res["votecheck"][os.path.basename(p)] = [agree_n, len(recs)]
        L.append(f"\nFirst vote equals the unique 5-vote plurality top-1 ({os.path.basename(p)}): {agree_n}/{len(recs)}")

    with open(os.path.join(a.ctx, "results.json"), "w") as f:
        json.dump(res, f, indent=1, default=float)
    with open(os.path.join(a.ctx, "results.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
