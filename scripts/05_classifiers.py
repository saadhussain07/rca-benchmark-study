"""Same-feature classifiers (RQ2). Grouped 5-fold CV and leave-one-system-out.

usage: python scripts/05_classifiers.py --ctx out/re2
writes out/re2/ranks_classifiers.json
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import baselines as B  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx", required=True)
    a = ap.parse_args()
    vis = pd.read_csv(os.path.join(a.ctx, "features_visible.csv"))
    allf = pd.read_csv(os.path.join(a.ctx, "features_all.csv"))
    out = {
        "lr_visible": B.cv_rank(vis, "lr"),
        "rf_visible": B.cv_rank(vis, "rf"),
        "lr_all": B.cv_rank(allf, "lr"),
        "lr_visible_loso": B.loso_rank(vis, "lr"),
    }
    with open(os.path.join(a.ctx, "ranks_classifiers.json"), "w") as f:
        json.dump(out, f)
    print({k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    main()
