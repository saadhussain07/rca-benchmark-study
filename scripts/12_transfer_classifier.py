"""Amendment 3 (B): the same-feature classifier trained on every RE2 case and
applied unchanged to RE3. On RE3 it uses no RE3 label, so it is a label-free
comparator there. Same features and model as `lr_visible`.

usage: python scripts/12_transfer_classifier.py --train-ctx out/re2 --test-ctx out/re3
writes <test-ctx>/ranks_transfer.json  ({"lr_visible_re2train": {case_id: [services]}})
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
    ap.add_argument("--train-ctx", required=True)
    ap.add_argument("--test-ctx", required=True)
    a = ap.parse_args()
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    tr = pd.read_csv(os.path.join(a.train_ctx, "features_visible.csv"))
    te = pd.read_csv(os.path.join(a.test_ctx, "features_visible.csv"))
    mdl = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
    mdl.fit(tr[B.VISIBLE_FEATURES].values.astype(float), tr["label"].values)
    te = te.assign(p=mdl.predict_proba(te[B.VISIBLE_FEATURES].values.astype(float))[:, 1])
    out = {"lr_visible_re2train": {cid: B._rank_by(dict(zip(g["service"], g["p"])), cid, "transfer-lr")
                                   for cid, g in te.groupby("case_id")}}
    with open(os.path.join(a.test_ctx, "ranks_transfer.json"), "w") as f:
        json.dump(out, f)
    print({k: len(v) for k, v in out.items()}, f"trained on {tr['case_id'].nunique()} cases")


if __name__ == "__main__":
    main()
