"""Numbers requested by the independent pre-submission review.

Reads existing outputs only. Makes no model call and no RCAEval run, and
changes no frozen file or earlier output. Everything it adds is reported in
the paper as exploratory or as a check of an earlier result.

  1. RE3 replication (Amendment 3 B): exact sign-flip p beside the Monte Carlo
     p for every row, Holm on both, and the same for the 84 non-pilot cases
     (Amendment 1 borderline rule).
  2. RE2 RQ1/RQ2 family with the first-run (pre-Amendment-2) RCAEval rankings,
     as committed in Amendment 2: 11-test family (as the frozen code computed)
     and 13-test family (missing methods scored as chance).
  3. RQ0 coverage per system and fault (RE2, RE3).
  4. Position: does the top-1 follow the first service of the AFFECTED
     SERVICES line when that line is permuted (order1/order2 runs)?
  5. Always-on alarms: in how many SS cases (and TT cases) is the most-flagged
     non-root service no longer flagged once alarms not exceeding twice their
     pre-injection count are suppressed (re2_chronic contexts)?
  6. epsilon-Diagnosis on Train Ticket: what it ranks.
  7. RE3 anon_full: is the root service named in the log samples, and does
     its label appear there under anon_full?
  8. Call and token totals over every LLM output file.

usage (repo root, env active, RCAEval on PYTHONPATH as for 06_evaluate.py):
  python scripts/16_review_numbers.py --out out --pilot out/pilot_re3.txt
writes out/review_numbers.md
"""
import argparse
import collections
import glob
import importlib.util
import itertools
import json
import os
import random
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
EV = A3.EV
DEP = C.DEPLOYED_MODEL
MODELS = sorted(C.MODELS)
N_EXACT_MC = 1_000_000


def exact_p(cases, diff):
    """Two-sided cluster sign-flip p: full enumeration up to 22 non-zero
    clusters, otherwise 10^6 random sign vectors (chunked)."""
    d = np.array([sum(g) for g in EV._clusters(cases, diff)], dtype=float)
    d = d[d != 0]
    if len(d) == 0:
        return 1.0, 0
    t = abs(d.sum())
    if len(d) <= 22:
        hits = 0
        tot = 0
        for chunk in _chunks(itertools.product([-1.0, 1.0], repeat=len(d)), 200_000):
            s = np.array(chunk)
            hits += int(np.sum(np.abs(s @ d) >= t - 1e-12))
            tot += len(s)
        return hits / tot, len(d)
    rng = np.random.default_rng(C.SEED)
    hits = 0
    for _ in range(N_EXACT_MC // 100_000):
        f = rng.choice([-1.0, 1.0], size=(100_000, len(d)))
        hits += int(np.sum(np.abs(f @ d) >= t - 1e-12))
    return hits / N_EXACT_MC, len(d)


def _chunks(it, n):
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf


_orig_paired = EV.paired


def paired_exact(cases, a, b, level=0.95):
    r = _orig_paired(cases, a, b, level)
    keys = [c for c in cases if c["case_id"] in a and c["case_id"] in b]
    diff = {c["case_id"]: a[c["case_id"]] - b[c["case_id"]] for c in keys}
    r["p_exact"], r["k_nonzero"] = exact_p(keys, diff)
    return r


def fmt(r):
    return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]"


def holm_into(rows, key_in, key_out):
    for (_, r), h in zip(rows, EV.holm([r[key_in] for _, r in rows])):
        r[key_out] = h


# ------------------------------------------------------------------ 1
def part1(a, L):
    L.append("## 1. RE3 replication: exact p and the non-pilot sensitivity\n")
    L.append("MC p = the pre-registered 10,000-flip permutation p; exact = full enumeration (<= 22 non-zero "
             "clusters) or 10^6 flips. Holm within the same families as Amendment 3 (13 RQ1/RQ2 tests; 3 P3b "
             "tests; decoy vs placebo single). 'borderline' = the two Holm values fall on different sides of "
             "0.05 (Amendment 1 rule).\n")
    EV.paired = paired_exact
    try:
        c3, m3, r3 = A3.load(os.path.join(a.out, "re3"))
        pilot = {l.strip() for l in open(a.pilot) if l.strip()} if a.pilot and os.path.exists(a.pilot) else set()
        for label, cs in (("all 90 cases", c3), (f"{sum(c['case_id'] not in pilot for c in c3)} non-pilot cases",
                                                 [c for c in c3 if c["case_id"] not in pilot])):
            q = A3.quantities(cs, m3, r3)
            fam_rq = [(k, r) for k, r in q.items() if k.startswith("RQ1/RQ2")]
            fam_3b = [(k, r) for k, r in q.items() if k.startswith("P3b")]
            for fam in (fam_rq, fam_3b):
                holm_into(fam, "p_perm", "h_mc")
                holm_into(fam, "p_exact", "h_ex")
            L.append(f"### {label}\n")
            L.append("| quantity | diff [95% CI] | MC p | MC p Holm | exact p | exact p Holm | non-zero clusters | note |")
            L.append("|---|---|---|---|---|---|---|---|")
            for k, r in q.items():
                if k.startswith("P2"):
                    L.append(f"| {k} | {fmt(r)} | {r['p_perm']:.4f} | - | {r['p_exact']:.4f} | - | "
                             f"{r['k_nonzero']} | {r.get('verdict', '')} |")
                    continue
                h1 = r.get("h_mc", r["p_perm"])
                h2 = r.get("h_ex", r["p_exact"])
                note = "borderline" if (h1 < 0.05) != (h2 < 0.05) else ""
                L.append(f"| {k} | {fmt(r)} | {r['p_perm']:.4f} | {h1:.4f} | {r['p_exact']:.4f} | {h2:.4f} | "
                         f"{r['k_nonzero']} | {note} |")
            L.append("")
    finally:
        EV.paired = _orig_paired


# ------------------------------------------------------------------ 2
def part2(a, L):
    L.append("## 2. RE2 RQ1/RQ2 family with the first-run (pre-Amendment-2) RCAEval rankings\n")
    ctx = os.path.join(a.out, "re2")
    pre = os.path.join(ctx, "ranks_rcaeval_pre_a2.json")
    if not os.path.exists(pre):
        L.append(f"`{pre}` not found; skipped.\n")
        return
    cases = EV.load_jsonl(os.path.join(ctx, "contexts.jsonl"))
    meth = {}
    for f in ("ranks_nonllm.json", "ranks_classifiers.json"):
        meth.update(json.load(open(os.path.join(ctx, f))))
    meth_pre = dict(meth)
    meth_pre.update(json.load(open(pre)))
    meth_post = dict(meth)
    meth_post.update(json.load(open(os.path.join(ctx, "ranks_rcaeval.json"))))
    dep = {k: v["ranking"] for k, v in EV.load_llm(os.path.join(ctx, "llm", f"main__{DEP}__annotated.jsonl")).items()}
    t_dep = EV.top1(cases, dep)
    comps = A3.COMPARATORS
    res = {}
    for tag, mm in (("pre", meth_pre), ("post", meth_post)):
        rows = []
        for m in comps:
            r = EV.paired(cases, t_dep, EV.top1(cases, mm.get(m, {})))
            r["ranked"] = sum(1 for c in cases if mm.get(m, {}).get(c["case_id"]))
            rows.append((m, r))
        holm_into(rows, "p_perm", "h13")
        rows11 = [(m, r) for m, r in rows if r["ranked"] > 0]
        holm_into(rows11, "p_perm", "h11")
        res[tag] = dict(rows)
    L.append(f"Tests in the 11-test family (methods with >= 1 ranked case in the first run): "
             f"{sum(1 for r in res['pre'].values() if 'h11' in r)}.\n")
    L.append("| comparator | first run: ranked | first run: diff [95% CI] | Holm (11) | Holm (13, chance) | "
             "rerun (confirmatory): diff | rerun Holm (13) | verdict changes? |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m in comps:
        p, q = res["pre"][m], res["post"][m]
        h11 = f"{p['h11']:.4f}" if "h11" in p else "not in family"
        sig_pre = p.get("h11", p["h13"]) < 0.05
        sig_post = q["h13"] < 0.05
        L.append(f"| {m} | {p['ranked']} | {fmt(p)} | {h11} | {p['h13']:.4f} | {fmt(q)} | {q['h13']:.4f} | "
                 f"{'YES' if sig_pre != sig_post else 'no'} |")
    L.append("")


# ------------------------------------------------------------------ 3
def part3(a, L):
    L.append("## 3. RQ0 coverage per system and fault\n")
    for suite in ("re2", "re3"):
        p = os.path.join(a.out, suite, "contexts.jsonl")
        if not os.path.exists(p):
            continue
        cases = EV.load_jsonl(p)
        L.append(f"### {suite.upper()}\n")
        faults = sorted({c["fault"] for c in cases})
        L.append("| system | " + " | ".join(f"{f} flagged / NOTE" for f in faults) + " |")
        L.append("|---|" + "---|" * len(faults))
        for s in sorted({c["system"] for c in cases}) + ["all"]:
            cells = []
            for f in faults:
                cs = [c for c in cases if c["fault"] == f and (s == "all" or c["system"] == s)]
                cells.append(f"{sum(c['flagged'] for c in cs)}/{len(cs)} / {sum(c['n_notes'] > 0 for c in cs)}"
                             if cs else "-")
            L.append(f"| {s} | " + " | ".join(cells) + " |")
        L.append("")


# ------------------------------------------------------------------ 4
def part4(a, L):
    L.append("## 4. Position: does the top-1 follow the first listed service when the order is permuted?\n")
    ctx = os.path.join(a.out, "re2")
    cases = EV.load_jsonl(os.path.join(ctx, "contexts.jsonl"))
    flagged = [c for c in cases if c["flagged"]]
    canon = lambda s: s.replace("-db", "")  # noqa: E731
    base = EV.load_llm(os.path.join(ctx, "llm", f"main__{DEP}__annotated.jsonl"))
    L.append("Multi-service flagged cases. 'old first' = first service in the frozen order; 'new first' = first "
             "service after the seeded permutation used by 04_run_llm.py.\n")
    L.append("| run | cases | first changed | top-1 = new first | top-1 = old first | (of changed) top-1 = new first | "
             "(of changed) top-1 = old first | (of changed) frozen run top-1 = old first |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k in (1, 2):
        p = os.path.join(ctx, "llm", f"order{k}__{DEP}__shuffled.jsonl")
        if not os.path.exists(p):
            continue
        sh = EV.load_llm(p)
        cs = [c for c in flagged if len(c["context"]["affected_services"]) > 1
              and c["case_id"] in sh and c["case_id"] in base]
        n_ch = new_hit = old_hit = ch_new = ch_old = ch_base_old = 0
        for c in cs:
            aff = list(c["context"]["affected_services"])
            perm = aff[:]
            random.Random(f"{C.SEED}|order{k}|{c['case_id']}").shuffle(perm)
            old, new = canon(aff[0]), canon(perm[0])
            t = sh[c["case_id"]]["ranking"][0]
            new_hit += t == new
            old_hit += t == old
            if old != new:
                n_ch += 1
                ch_new += t == new
                ch_old += t == old
                ch_base_old += base[c["case_id"]]["ranking"][0] == old
        L.append(f"| order{k} | {len(cs)} | {n_ch} | {new_hit} | {old_hit} | {ch_new}/{n_ch} | {ch_old}/{n_ch} | "
                 f"{ch_base_old}/{n_ch} |")
    L.append("")


# ------------------------------------------------------------------ 5
def part5(a, L):
    L.append("## 5. Always-on alarms: flagged with and without the baseline-aware filter (E3)\n")
    c0 = {c["case_id"]: c for c in EV.load_jsonl(os.path.join(a.out, "re2", "contexts.jsonl"))}
    pc = os.path.join(a.out, "re2_chronic", "contexts.jsonl")
    if not os.path.exists(pc):
        L.append("re2_chronic not found; skipped.\n")
        return
    c1 = {c["case_id"]: c for c in EV.load_jsonl(pc)}
    canon = lambda s: s.replace("-db", "")  # noqa: E731
    L.append("| system | service | flagged (frozen) | still flagged with filter | dropped by filter "
             "(alarm not above 2x its pre-injection level) |")
    L.append("|---|---|---|---|---|")
    for sysn, svc in (("ss", "queue-master"), ("tt", "ts-inside-payment-service"), ("ob", "emailservice")):
        ids = [k for k, c in c0.items() if c["system"] == sysn and c["gt"]["root_service"] != svc]
        f0 = [k for k in ids if svc in {canon(s) for s in c0[k]["context"].get("affected_services", [])}]
        f1 = [k for k in f0 if k in c1 and svc in {canon(s) for s in c1[k]["context"].get("affected_services", [])}]
        L.append(f"| {sysn} | {svc} | {len(f0)}/{len(ids)} | {len(f1)} | {len(f0) - len(f1)} |")
    L.append("")


# ------------------------------------------------------------------ 6
def part6(a, L):
    L.append("## 6. epsilon-Diagnosis on Train Ticket\n")
    ctx = os.path.join(a.out, "re2")
    cases = [c for c in EV.load_jsonl(os.path.join(ctx, "contexts.jsonl")) if c["system"] == "tt"]
    rr = json.load(open(os.path.join(ctx, "ranks_rcaeval.json"))).get("rcaeval:e_diagnosis", {})
    firsts = collections.Counter()
    pos = []
    for c in cases:
        r = rr.get(c["case_id"]) or []
        if r:
            firsts[r[0]] += 1
        root = c["gt"]["root_service"]
        pos.append(r.index(root) + 1 if root in r else None)
    if not cases:
        L.append("no TT cases; skipped.\n")
        return
    L.append(f"TT cases with a ranking: {sum(1 for c in cases if rr.get(c['case_id']))}/{len(cases)}; "
             f"mean ranking length {np.mean([len(rr.get(c['case_id']) or []) for c in cases]):.1f}; "
             f"candidates per case {np.mean([len(c['candidates']) for c in cases]):.1f}.")
    L.append(f"Root found in ranking: {sum(p is not None for p in pos)}/{len(cases)}; positions (found): "
             f"{collections.Counter(p for p in pos if p is not None).most_common(10)}")
    L.append(f"Most common top-1: {firsts.most_common(8)}")
    raw = sorted(glob.glob(os.path.join(a.rcaeval_out, "e_diagnosis__re2-tt", "*.json")))[:3] if a.rcaeval_out else []
    for p in raw:
        try:
            d = json.load(open(p))
            L.append(f"- raw `{os.path.basename(p)}`: {str(d)[:400]}")
        except Exception as e:  # noqa: BLE001
            L.append(f"- raw `{os.path.basename(p)}`: unreadable ({e})")
    for c in cases[:3]:
        L.append(f"- {c['case_id']}: root {c['gt']['root_service']}; ranking[:5] {(rr.get(c['case_id']) or [])[:5]}")
    L.append("")


# ------------------------------------------------------------------ 7
def part7(a, L):
    L.append("## 7. RE3 anon_full: root service in the log samples\n")
    p = os.path.join(a.out, "re3", "contexts.jsonl")
    cases = [c for c in EV.load_jsonl(p) if c["flagged"]]
    rows = collections.Counter()
    by_sys = collections.defaultdict(collections.Counter)
    for c in cases:
        root = c["gt"]["root_service"]
        logs = json.dumps([l for l in c["context"].get("full_logs", []) if l.get("is_anomaly")])
        n_real = len(X._forms_regex({f.lower() for f in X.name_forms(root)}).findall(logs))
        names = sorted(set(c["candidates"]) | set(c["detector_services"]))
        apply, back, fwd = X.anonymiser_full(c["case_id"], names)
        ctx_a = X.anonymise_obj(c["context"], apply)
        logs_a = json.dumps([l for l in ctx_a.get("full_logs", []) if l.get("is_anomaly")])
        lab = fwd.get(root)
        n_lab = logs_a.count(lab) if lab else 0
        key = ("root named in logs" if n_real else "root not named in logs",
               "label present (anon_full)" if n_lab else "label absent (anon_full)")
        rows[key] += 1
        by_sys[c["system"]][key] += 1
    L.append("| system | root named in log samples, label kept | named, label absent | not named |")
    L.append("|---|---|---|---|")
    for s in sorted(by_sys) + ["all"]:
        cnt = rows if s == "all" else by_sys[s]
        L.append(f"| {s} | {cnt[('root named in logs', 'label present (anon_full)')]} | "
                 f"{cnt[('root named in logs', 'label absent (anon_full)')]} | "
                 f"{cnt[('root not named in logs', 'label present (anon_full)')] + cnt[('root not named in logs', 'label absent (anon_full)')]} |")
    L.append("")


# ------------------------------------------------------------------ 8
def part8(a, L):
    L.append("## 8. Calls and tokens\n")
    L.append("Calls count every API request (a schema retry is a second call; its tokens are those of the "
             "retained response only, so token totals are lower bounds when retries occurred).\n")
    L.append("| directory | files | records | errors | votes | retries | calls | prompt tokens | completion tokens | "
             "finish=length |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    tot = collections.Counter()
    for d in sorted(glob.glob(os.path.join(a.out, "*", "llm"))):
        c = collections.Counter()
        files = sorted(glob.glob(os.path.join(d, "*.jsonl")))
        for f in files:
            c["files"] += 1
            for line in open(f, encoding="utf-8"):
                if not line.strip():
                    continue
                r = json.loads(line)
                c["records"] += 1
                c["errors"] += int(bool(r.get("error")))
                for v in r.get("votes") or []:
                    c["votes"] += 1
                    c["retries"] += int(bool(v.get("retried")))
                    c["prompt"] += v.get("prompt_tokens") or 0
                    c["completion"] += v.get("completion_tokens") or 0
                    c["length"] += int(v.get("finish_reason") == "length")
        c["calls"] = c["votes"] + c["retries"]
        tot.update(c)
        L.append(f"| {os.path.relpath(d, a.out)} | {c['files']} | {c['records']} | {c['errors']} | {c['votes']} | "
                 f"{c['retries']} | {c['calls']} | {c['prompt']:,} | {c['completion']:,} | {c['length']} |")
    L.append(f"| **total** | {tot['files']} | {tot['records']} | {tot['errors']} | {tot['votes']} | {tot['retries']} | "
             f"{tot['calls']} | {tot['prompt']:,} | {tot['completion']:,} | {tot['length']} |")
    L.append("\nError records were retried by the resumable runner; the evaluation keeps the last successful record.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--pilot", default="out/pilot_re3.txt")
    ap.add_argument("--rcaeval-out", default=os.path.expanduser("~/rca/RCAEval/output/kept"))
    ap.add_argument("--only", default="", help="comma list of parts to run, e.g. 3,8")
    a = ap.parse_args()
    parts = [part1, part2, part3, part4, part5, part6, part7, part8]
    want = {int(x) for x in a.only.split(",") if x.strip()} or set(range(1, 9))
    L = ["# Review numbers (16_review_numbers.py)\n",
         "Computed from existing outputs; no model call, no baseline run. Exploratory unless a section says otherwise.\n"]
    for i, f in enumerate(parts, 1):
        if i not in want:
            continue
        try:
            f(a, L)
        except Exception as e:  # noqa: BLE001  (one part must not stop the others)
            L.append(f"## part {i} failed: {type(e).__name__}: {e}\n")
        print(f"part {i} done", flush=True)
    path = os.path.join(a.out, "review_numbers.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
