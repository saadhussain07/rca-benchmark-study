"""Amendment 2 execution fixes to RCAEval (pinned commit 259ea41), applied in place.
Idempotent: running it twice changes nothing. Prints the sha256 of each file
before and after so the change is on record.

  P1  main.py: a case on which a method raises is written as
      <service>_<fault>_<case>_failed.json and the run continues (the code
      already contains this path, made unreachable by a `raise e` placed in front
      of it). Without it, one failing case stops the run and every later case of
      that system goes unscored. Protocol section 9 already says a failed case is
      chance for that baseline; this makes the run behave that way.

  P2  RCAEval/e2e/microcause.py: tigramite >= 5 returns None from
      PCMCI.return_significant_links. tigramite 4.2.2.1 (the version RCAEval's
      lock file pins) does not build on Python 3.12. The call is replaced by a
      verbatim copy of the 4.2.2.1 function body, so the graph is built exactly
      as before.

  P3  RCAEval/e2e/microcause.py: pingouin's partial_corr returns a one-row
      frame, and `float(ret.r)` on a one-element Series is an error under
      pandas 3 (installed by RCAEval's own requirements, `pandas>2.0.1`). The
      value is read with `.iloc[0]` instead; it is the same number.

usage (from ~/rca/RCAEval):  python ~/rca/rcastudy/scripts/rcaeval_patch_a2.py
"""
import hashlib
import sys

P1_OLD = """    except Exception as e:
        raise e
        print(f"{args.method=} failed on {data_path=}")"""
P1_NEW = """    except Exception as e:
        # Amendment 2 / P1: record the failure and continue (was: raise e)
        print(f"{args.method=} failed on {data_path=}")"""

P2_OLD = """        pcmci_links = pcmci.return_significant_links(
            results["p_matrix"],
            results["val_matrix"],
            alpha_level=alpha_level,
            include_lagzero_links=False,
        )"""
P2_NEW = """        # Amendment 2 / P2: body of tigramite 4.2.2.1
        # PCMCI.return_significant_links(include_lagzero_links=False), copied
        # verbatim; tigramite >= 5 returns None from that method.
        pq_matrix, val_matrix = results["p_matrix"], results["val_matrix"]
        link_dict = dict()
        for j in range(pq_matrix.shape[1]):
            good_links = np.argwhere(pq_matrix[:, j, 1:] <= alpha_level)
            links = {(i, -tau - 1): np.abs(val_matrix[i, j, abs(tau) + 1])
                     for i, tau in good_links}
            link_dict[j] = sorted(links, key=links.get, reverse=True)
        pcmci_links = {"link_dict": link_dict, "link_matrix": pq_matrix <= alpha_level}"""


P3_OLD = "            return abs(float(ret.r))"
P3_NEW = "            return abs(float(ret[\"r\"].iloc[0]))  # Amendment 2 / P3 (pandas 3)"


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


ok = patch("main.py", P1_OLD, P1_NEW, "P1")
ok = patch("RCAEval/e2e/microcause.py", P2_OLD, P2_NEW, "P2") and ok
ok = patch("RCAEval/e2e/microcause.py", P3_OLD, P3_NEW, "P3") and ok
sys.exit(0 if ok else 1)
