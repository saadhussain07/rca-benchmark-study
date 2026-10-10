"""sha256 of every data file under a suite folder, for data_manifest.txt.

usage: python scripts/00_manifest.py data/RE2 > out/data_manifest_re2.txt
"""
import hashlib
import os
import sys

root = sys.argv[1]
for dp, _, fs in sorted(os.walk(root)):
    for f in sorted(fs):
        p = os.path.join(dp, f)
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        print(h.hexdigest(), os.path.relpath(p, root).replace(os.sep, "/"))
