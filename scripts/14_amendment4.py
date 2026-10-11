"""Amendment 4 analyses (exploratory, PROTOCOL_V3_AMENDMENT_4.md).

A  SimpleRCA-style heuristic: pre-registered form (V0) and variants V1-V4, on
   RE2 and RE3, and the deployed model against each.
B  Onset uncertainty on RE2: every method re-run with the injection time it is
   given shifted by -120 s and +120 s; AC@1 per shift, change from the true
   onset, and the deployed model's gap to each method per shift.

usage: python scripts/14_amendment4.py --ctx-re2 out/re2 --ctx-re3 out/re3 --shifts -120 120
writes out/re2/amendment4.md
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

spec = importlib.util.spec_from_file_location("ev", os.path.join(HERE, "06_evaluate.py"))
EV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EV)

DEP = f"llm:{C.DEPLOYED_MODEL}__annotated"
FANG_RE2 = {"ob": 0.47, "ss": 0.24, "tt": 0.80}   # published SimpleRCA top-1 (PROTOCOL_V3 5.5)
VARIANTS = ["V0", "V1", "V2", "V3", "V4"]
VLABEL = {"V0": "pre-registered", "V1": "no sigma=0 rule", "V2": "own columns only",
          "V3": "one alert per signal type", "V4": "V1+V2+V3"}


def load(ctx):
    cases = EV.load_jsonl(os.path.join(ctx, "contexts.jsonl"))
    meth = {}
    for f in ("ranks_nonllm.json", "ranks_classifiers.json", "ranks_rcaeval.json", "ranks_simplerca_variants.json"):
        p = os.path.join(ctx, f)
        if os.path.exists(p):
            meth.update(json.load(open(p)))
    p = os.path.join(ctx, "llm", f"main__{C.DEPLOYED_MODEL}__annotated.jsonl")
    if os.path.exists(p):
        meth[DEP] = {k: v["ranking"] for k, v in EV.load_llm(p).items()}
    return cases, meth


def fmt(r):
    return f"{r['diff']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]"


def acc(cases, rk):
    t = EV.top1(cases, rk)
    return sum(t.values()) / len(t) if t else float("nan")


def part_a(a, L):
    L.append("## A. SimpleRCA-style heuristic: pre-registered form and variants (exploratory)\n")
    for name, ctx in (("RE2", a.ctx_re2), ("RE3", a.ctx_re3)):
        if not ctx or not os.path.exists(os.path.join(ctx, "ranks_simplerca_variants.json")):
            L.append(f"{name}: variants not available.\n")
            continue
        cases, meth = load(ctx)
        systems = sorted({c["system"] for c in cases})
        L.append(f"### {name}: AC@1\n")
        L.append("| variant | " + " | ".join(systems) + " | all |")
        L.append("|---|" + "---|" * (len(systems) + 1))
        for v in VARIANTS:
            rk = meth[f"simplerca:{v}"]
            cells = [f"{acc([c for c in cases if c['system'] == s], rk):.3f}" for s in systems]
            L.append(f"| {v} {VLABEL[v]} | " + " | ".join(cells) + f" | {acc(cases, rk):.3f} |")
        ch = [np.mean([1.0 / len(c['candidates']) for c in cases if c['system'] == s]) for s in systems]
        L.append("| chance | " + " | ".join(f"{x:.3f}" for x in ch) +
                 f" | {np.mean([1.0 / len(c['candidates']) for c in cases]):.3f} |")
        if name == "RE2":
            L.append("| Fang et al., published SimpleRCA | " + " | ".join(f"{FANG_RE2.get(s, float('nan')):.2f}" for s in systems) + " | - |")
        if DEP in meth:
            L.append(f"\n{name}: deployed model minus each variant, AC@1, all cases (95% cluster CI, perm p):\n")
            for v in VARIANTS:
                r = EV.paired(cases, EV.top1(cases, meth[DEP]), EV.top1(cases, meth[f"simplerca:{v}"]))
                L.append(f"- {v}: {fmt(r)}, p {r['p_perm']:.4f}")
        L.append("")


def part_b(a, L):
    L.append("## B. Onset uncertainty on RE2 (exploratory)\n")
    base_cases, base = load(a.ctx_re2)
    shifts = [0] + a.shifts
    data = {0: (base_cases, base)}
    for s in a.shifts:
        ctx = f"{a.ctx_re2}_shift{s}"   # run_amendment4_a.sh: out/re2_shift-120, out/re2_shift120
        if os.path.exists(os.path.join(ctx, "contexts.jsonl")):
            data[s] = load(ctx)
    shifts = [s for s in shifts if s in data]
    methods = [DEP, "detector_count", "first_affected", "lr_visible", "simplerca:V0", "simplerca:V3",
               "rcaeval:nsigma", "rcaeval:baro"]
    L.append("Flagged cases: " + ", ".join(f"{s:+d} s: {sum(c['flagged'] for c in data[s][0])}" for s in shifts) + "\n")
    L.append("| method | " + " | ".join(f"AC@1 at {s:+d} s" for s in shifts) + " | " +
             " | ".join(f"change at {s:+d} s [95% CI]" for s in shifts if s) + " |")
    L.append("|---|" + "---|" * (len(shifts) + len([s for s in shifts if s])))
    for m in methods:
        if not all(m in data[s][1] for s in shifts):
            L.append(f"| {m} | " + " | ".join(f"{acc(data[s][0], data[s][1][m]):.3f}" if m in data[s][1] else "-"
                                              for s in shifts) + " | (missing at some shift) |")
            continue
        vals = [f"{acc(data[s][0], data[s][1][m]):.3f}" for s in shifts]
        t0 = EV.top1(data[0][0], data[0][1][m])
        ch = []
        for s in shifts:
            if s:
                r = EV.paired(data[0][0], EV.top1(data[s][0], data[s][1][m]), t0)
                ch.append(fmt(r))
        L.append(f"| {m} | " + " | ".join(vals) + " | " + " | ".join(ch) + " |")
    L.append("\nDeployed model minus each method at each shift (AC@1, 95% cluster CI):\n")
    L.append("| comparator | " + " | ".join(f"{s:+d} s" for s in shifts) + " |")
    L.append("|---|" + "---|" * len(shifts))
    for m in methods[1:]:
        cells = []
        for s in shifts:
            cs, mt = data[s]
            if DEP in mt and m in mt:
                cells.append(fmt(EV.paired(cs, EV.top1(cs, mt[DEP]), EV.top1(cs, mt[m]))))
            else:
                cells.append("-")
        L.append(f"| {m} | " + " | ".join(cells) + " |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx-re2", required=True)
    ap.add_argument("--ctx-re3", default=None)
    ap.add_argument("--shifts", type=int, nargs="*", default=[-120, 120])
    a = ap.parse_args()
    L = ["# Amendment 4 analyses (14_amendment4.py)\n", "Everything here is exploratory and post hoc.\n"]
    part_a(a, L)
    part_b(a, L)
    with open(os.path.join(a.ctx_re2, "amendment4.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
