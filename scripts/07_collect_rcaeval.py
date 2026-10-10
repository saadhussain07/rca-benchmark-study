"""Turn RCAEval's per-case result files into our ranking format.

usage: python scripts/07_collect_rcaeval.py --kept ../RCAEval/output/kept --ctx out/re2
writes out/re2/ranks_rcaeval.json  ({"rcaeval:<method>": {case_id: [services]}})
"""
import argparse
import glob
import json
import os


def services_from_ranks(ranks):
    """Same folding as RCAEval main.py: metric -> service, '-db' removed,
    duplicates dropped keeping the first occurrence."""
    out = []
    for x in ranks:
        s = str(x).split("_")[0].replace("-db", "")
        if s not in out:
            out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kept", required=True)
    ap.add_argument("--ctx", required=True)
    a = ap.parse_args()
    known = set()
    with open(os.path.join(a.ctx, "contexts.jsonl"), encoding="utf-8") as f:
        for l in f:
            known.add(json.loads(l)["case_id"])
    res = {}
    for d in sorted(glob.glob(os.path.join(a.kept, "*__*"))):
        method, dataset = os.path.basename(d).split("__")
        sysname = dataset.split("-")[1]
        suite = dataset.split("-")[0]
        for p in glob.glob(os.path.join(d, "*.json")):
            base = os.path.basename(p)[:-5]
            if base.endswith("_failed"):
                continue
            service, fault, n = base.split("_")[:3]
            cid = f"{suite}{sysname}_{service}_{fault}_{n}"
            data = json.load(open(p))
            ranks = data.get("0") or data.get(0) or []
            res.setdefault(f"rcaeval:{method}", {})[cid] = services_from_ranks(ranks)
    missing = {m: len(known - set(v)) for m, v in res.items()}
    with open(os.path.join(a.ctx, "ranks_rcaeval.json"), "w") as f:
        json.dump(res, f)
    print({m: len(v) for m, v in res.items()})
    print("cases without a ranking (scored as chance):", missing)


if __name__ == "__main__":
    main()
