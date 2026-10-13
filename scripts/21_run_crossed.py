"""Amendment 8 (part A): the 2x2 that crosses the evidence a pipeline shows
with the prompt it is shown in.

The two existing cells are reused unchanged:
  deployed system prompt + deployed user message  = condition `annotated` (out/<suite>/llm)
  generic system prompt  + generic user message   = condition `g_full`    (out/<suite>_generic/llm)
This script runs the two crossed cells on the deployed agent's flagged cases:
  x_dsys_guser  deployed system prompt (persona, instructions, answer schema) + generic user message
  x_gsys_duser  generic system prompt + deployed user message (the agent's full context, as `annotated`)

usage: python scripts/21_run_crossed.py --suite re2 --model gpt-oss-120b --condition x_dsys_guser
writes out/<suite>/llm/main__<model>__<condition>.jsonl (04_run_llm.py record format). Resumable.
"""
import argparse
import hashlib
import json
import os
import sys
import time

if os.environ.get("PYTHONHASHSEED") != "0":  # same hash seed as every other run
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import agent as A  # noqa: E402
from rcastudy import config as C  # noqa: E402
from rcastudy import generic as G  # noqa: E402


def messages(rec, grec, condition):
    services = rec["candidates"]
    d_sys, d_user = A.build_messages(rec["context"], rec["summary"]["annotated"], services)
    g_sys, g_user = G.messages(grec["generic"], grec["candidates"], "g_full")
    if condition == "x_dsys_guser":
        return d_sys, g_user, A.schema_ok
    if condition == "x_gsys_duser":
        return g_sys, d_user, G.schema_ok
    raise ValueError(condition)


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True, choices=["re2", "re3"])
    ap.add_argument("--out", default="out")
    ap.add_argument("--model", required=True, choices=sorted(C.MODELS))
    ap.add_argument("--condition", required=True, choices=["x_dsys_guser", "x_gsys_duser"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    recs = [r for r in load(os.path.join(a.out, a.suite, "contexts.jsonl")) if r.get("flagged")]
    gen = {r["case_id"]: r for r in load(os.path.join(a.out, f"{a.suite}_generic", "contexts.jsonl"))}
    missing = [r["case_id"] for r in recs if not (gen.get(r["case_id"]) or {}).get("generic")]
    if missing:
        print(f"WARNING: {len(missing)} flagged cases have no generic summary and are skipped: {missing[:5]}")
    recs = [r for r in recs if r["case_id"] not in missing]
    out_dir = os.path.join(a.out, a.suite, "llm")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"main__{a.model}__{a.condition}.jsonl")
    done = set()
    if os.path.exists(out):
        done = {d["case_id"] for d in (json.loads(l) for l in open(out, encoding="utf-8") if l.strip())
                if not d.get("error")}
    todo = [r for r in recs if r["case_id"] not in done][: a.limit]
    print(f"{len(recs)} flagged cases, {len(done)} done, {len(todo)} to run -> {out}")
    if a.dry_run:
        r = todo[0] if todo else recs[0]
        s, u, _ = messages(r, gen[r["case_id"]], a.condition)
        print("=" * 30, "SYSTEM\n", s[:1500], "\n", "=" * 30, "USER\n", u[:2500])
        return
    call = A.GroqCaller(C.MODELS[a.model])
    with open(out, "a", encoding="utf-8") as fo:
        for i, r in enumerate(todo, 1):
            system, user, ok = messages(r, gen[r["case_id"]], a.condition)
            votes, error = [], None
            try:
                resp = call(system, user)
                parsed = A.parse(resp["text"])
                retried = False
                if not ok(parsed):
                    resp = call(system, user)
                    parsed = A.parse(resp["text"])
                    retried = True
                rank, n_listed = A.ranking(parsed if isinstance(parsed, dict) else {}, r["candidates"],
                                           r["case_id"], None)
                votes.append({"vote": 1, "raw": resp["text"], "parsed": parsed, "schema_ok": ok(parsed),
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
                   "condition": a.condition, "tag": "main",
                   "prompt_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest(),
                   "decoy": None, "anon_leaks": None, "error": error, "votes": votes,
                   "ranking": votes[0]["ranking"] if (votes and not error) else None,
                   "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
            fo.write(json.dumps(rec) + "\n")
            fo.flush()
            if not error:
                print(f"[{i}/{len(todo)}] {r['case_id']} -> {rec['ranking'][0]} "
                      f"({votes[0]['latency_s']}s, {votes[0]['finish_reason']})")


if __name__ == "__main__":
    main()
