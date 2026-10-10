"""Seeded case selections fixed by the protocol.

  re1 pilot     : one case per (system, fault) of RE1, repetition 1, service
                  drawn at random -> pilot_re1.txt  (15 cases)
  re3 pilot     : two random cases per RE3 system -> pilot_re3.txt (6 cases;
                  tests log/trace parsing and prompt length)
  re2 vote check: 30 RE2 cases drawn at random   -> vote_check_cases.txt

usage: python scripts/02_select_subsets.py --root data --out out
"""
import argparse
import collections
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import config as C  # noqa: E402
from rcastudy import data as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    re1 = D.discover(a.root, "re1")
    groups = collections.defaultdict(list)
    for c in re1:
        if c.rep == 1:
            groups[(c.system, c.fault)].append(c.case_id)
    rng = random.Random(f"{C.SEED}|pilot")
    pilot = [rng.choice(sorted(v)) for k, v in sorted(groups.items())]
    with open(os.path.join(a.out, "pilot_re1.txt"), "w") as f:
        f.write("\n".join(pilot) + "\n")
    re3 = D.discover(a.root, "re3")
    by_sys = collections.defaultdict(list)
    for c in re3:
        by_sys[c.system].append(c.case_id)
    rng = random.Random(f"{C.SEED}|pilot-re3")
    p3 = [x for k in sorted(by_sys) for x in sorted(rng.sample(sorted(by_sys[k]), min(2, len(by_sys[k]))))]
    with open(os.path.join(a.out, "pilot_re3.txt"), "w") as f:
        f.write("\n".join(p3) + "\n")
    re2 = sorted(c.case_id for c in D.discover(a.root, "re2"))
    rng = random.Random(f"{C.SEED}|votecheck")
    vc = sorted(rng.sample(re2, min(C.N_VOTE_CHECK_CASES, len(re2)))) if re2 else []
    with open(os.path.join(a.out, "vote_check_cases.txt"), "w") as f:
        f.write("\n".join(vc) + "\n")
    print(f"pilot: {len(pilot)} RE1 + {len(p3)} RE3 cases; vote check: {len(vc)} RE2 cases")


if __name__ == "__main__":
    main()
