"""Amendment 3 execution fix to RCAEval (pinned commit 259ea41, after the
Amendment 2 patches). Idempotent; prints sha256 before and after.

  P4  main.py: RE3-TT has one folder named <service>_<fault>_<k>
      (ts-route-service_f3_1, a second batch of that service and fault).
      main.py unpacks the folder name into exactly two parts, so it raises on
      that folder, outside the per-case try block, and stops the TT run. The
      patch takes the first two parts and makes the case name b<k>r<n>, so the
      result file (ts-route-service_f3_b1r2.json) neither crashes nor overwrites
      the f3 cases. Our case ids use the same form (rcastudy/data.py).

usage (from ~/rca/RCAEval):  python ~/rca/rcastudy/scripts/rcaeval_patch_a3.py
"""
import hashlib
import sys

P4_OLD = """    service, metric = basename(dirname(dirname(data_path))).split("_")
    case = basename(dirname(data_path))
"""
P4_NEW = """    _sf = basename(dirname(dirname(data_path))).split("_")  # Amendment 3 / P4
    service, metric = _sf[0], _sf[1]
    case = basename(dirname(data_path))
    if len(_sf) > 2:
        case = f"b{_sf[2]}r{case}"
"""


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def patch(path, old, new, label):
    before = sha(path)
    src = open(path, encoding="utf-8").read()
    if new in src:
        print(f"{label} {path}: already applied  sha256={before}")
        return True
    if src.count(old) != 1:
        print(f"{label} {path}: expected text found {src.count(old)} times; NOT patched")
        return False
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    print(f"{label} {path}: patched  before={before}  after={sha(path)}")
    return True


sys.exit(0 if patch("main.py", P4_OLD, P4_NEW, "P4") else 1)
