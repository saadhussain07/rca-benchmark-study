"""Amendment 7: run a model on the generic pipeline's prompts.

usage: python scripts/19_run_generic.py --ctx out/re3_generic --model gpt-oss-120b --condition g_full
writes <ctx>/llm/<tag>__<model>__<condition>.jsonl in the same record format as 04_run_llm.py,
so the frozen scoring code reads it unchanged. Resumable.
"""
import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import agent as A  # noqa: E402
from rcastudy import config as C  # noqa: E402
from rcastudy import generic as G  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx", required=True)
    ap.add_argument("--model", required=True, choices=sorted(C.MODELS))
    ap.add_argument("--condition", required=True, choices=["g_full", "g_nolog", "g_decoy"])
    ap.add_argument("--tag", default="main")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(os.path.join(a.ctx, "contexts.jsonl"), encoding="utf-8") if l.strip()]
    recs = [r for r in recs if r.get("flagged") and r.get("generic")]
    if a.condition == "g_decoy":
        recs = [r for r in recs if r["decoy"]["service"]]
    out_dir = os.path.join(a.ctx, "llm")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{a.tag}__{a.model}__{a.condition}.jsonl")
    done = set()
    if os.path.exists(out):
        done = {d["case_id"] for d in (json.loads(l) for l in open(out, encoding="utf-8") if l.strip())
                if not d.get("error")}
    todo = [r for r in recs if r["case_id"] not in done][: a.limit]
    print(f"{len(recs)} cases, {len(done)} done, {len(todo)} to run -> {out}")
    if a.dry_run:
        r = todo[0] if todo else recs[0]
        s, u = G.messages(r["generic"], r["candidates"], a.condition, r["decoy"]["service"])
        print("=" * 30, "SYSTEM\n", s, "\n", "=" * 30, "USER\n", u)
        return
    call = A.GroqCaller(C.MODELS[a.model])
    with open(out, "a", encoding="utf-8") as fo:
        for i, r in enumerate(todo, 1):
            system, user = G.messages(r["generic"], r["candidates"], a.condition, r["decoy"]["service"])
            check = G.log_example_residue(r["generic"], user) if a.condition == "g_nolog" else None
            votes, error = [], None
            try:
                resp = call(system, user)
                parsed = A.parse(resp["text"])
                retried = False
                if not G.schema_ok(parsed):
                    resp = call(system, user)
                    parsed = A.parse(resp["text"])
                    retried = True
                rank, n_listed = A.ranking(parsed if isinstance(parsed, dict) else {}, r["candidates"],
                                           r["case_id"], None)
                votes.append({"vote": 1, "raw": resp["text"], "parsed": parsed, "schema_ok": G.schema_ok(parsed),
                              "retried": retried, "ranking": rank, "n_listed": n_listed,
                              **{k: resp.get(k) for k in ("finish_reason", "has_reasoning_field", "latency_s",
                                                          "prompt_tokens", "completion_tokens",
                                                          "reasoning_tokens")}})
            except A.QuotaExhausted as e:
                print(f"\nQuota or spending limit reached after {i - 1} cases. Rerun the same command later.\n{e}")
                break
            except Exception as e:  # noqa: BLE001
                error = f"{type(e).__name__}: {str(e)[:500]}"
                print(f"[{i}/{len(todo)}] {r['case_id']} ERROR {error[:120]}")
            rec = {"case_id": r["case_id"], "model": a.model, "model_id": C.MODELS[a.model],
                   "condition": a.condition, "tag": a.tag,
                   "prompt_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest(),
                   "decoy": r["decoy"] if a.condition == "g_decoy" else None, "anon_leaks": check,
                   "error": error, "votes": votes,
                   "ranking": votes[0]["ranking"] if (votes and not error) else None,
                   "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
            fo.write(json.dumps(rec) + "\n")
            fo.flush()
            if not error:
                print(f"[{i}/{len(todo)}] {r['case_id']} -> {rec['ranking'][0]} "
                      f"({votes[0]['latency_s']}s, {votes[0]['finish_reason']})")


if __name__ == "__main__":
    main()
