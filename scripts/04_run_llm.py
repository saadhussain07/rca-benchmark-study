"""Call one model under one condition on every flagged case. Resumable: cases
already in the output file are skipped, so the same command can be rerun after
a quota stop.

conditions:
  annotated  deployed context as built
  stripped   every NOTE line removed (E1 manipulation)
  decoy      stripped + one NOTE making a claim about a seeded non-root service
  placebo    stripped + one NOTE naming the same service without a claim
  anon       annotated, service names replaced by service-01..NN in the
             structured text (raw log lines kept; leaks counted)

A within-case noise run for P3a is the annotated condition with --tag rep2.

usage:
  python scripts/04_run_llm.py --ctx out/re2 --model gpt-oss-120b --condition annotated
  python scripts/04_run_llm.py --ctx out/re2 --model gpt-oss-120b --condition annotated --dry-run --limit 1
  python scripts/04_run_llm.py --ctx out/re2 --model gpt-oss-120b --condition annotated --votes 5 --subset out/re2/vote_check_cases.txt --tag votecheck
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
from rcastudy import context as X  # noqa: E402


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def messages_for(rec, condition):
    """Return (system, user, back-map, leak count)."""
    ctx = rec["context"]
    services = rec["candidates"]
    if condition == "anon":
        names = sorted(set(services) | set(rec["detector_services"]))
        apply, back, fwd = X.anonymiser(rec["case_id"], names)
        ctx_a = X.anonymise_obj(ctx, apply)
        summary = X.anonymise_summary(rec["summary"]["annotated"], apply)
        system, user = A.build_messages(ctx_a, summary, sorted(fwd[s] for s in services))
        return system, user, back, X.leak_count(system + "\n" + user, fwd)
    system, user = A.build_messages(ctx, rec["summary"][condition], services)
    return system, user, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx", required=True, help="folder with contexts.jsonl")
    ap.add_argument("--model", required=True, choices=sorted(C.MODELS))
    ap.add_argument("--condition", required=True, choices=["annotated", "stripped", "decoy", "placebo", "anon"])
    ap.add_argument("--votes", type=int, default=C.N_VOTES_MAIN)
    ap.add_argument("--subset", default=None, help="file with one case id per line")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tag", default="main")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt, call nothing")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between calls")
    ap.add_argument("--note-only", action="store_true", help="only cases whose context carries a NOTE (rep2 runs)")
    a = ap.parse_args()

    recs = [r for r in load(os.path.join(a.ctx, "contexts.jsonl")) if r["flagged"]]
    if a.subset:
        keep = {l.strip() for l in open(a.subset) if l.strip()}
        recs = [r for r in recs if r["case_id"] in keep]
    if a.note_only:
        recs = [r for r in recs if r["n_notes"] > 0]
    if a.limit:
        recs = recs[: a.limit]

    out_dir = os.path.join(a.ctx, "llm")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{a.tag}__{a.model}__{a.condition}.jsonl")
    done = set()
    if os.path.exists(out):
        # error records do not count as done: they are retried on the next run
        done = {d["case_id"] for d in (json.loads(l) for l in open(out, encoding="utf-8") if l.strip())
                if not d.get("error")}
    todo = [r for r in recs if r["case_id"] not in done]
    if a.condition in ("decoy", "placebo"):
        todo = [r for r in todo if r["decoy"]["service"]]
    print(f"{len(recs)} flagged cases, {len(done)} done, {len(todo)} to run -> {out}")

    if a.dry_run:
        r = todo[0] if todo else recs[0]
        s, u, _, leak = messages_for(r, a.condition)
        if leak is not None:
            print(f"[anon] original names left in prompt: {leak}")
        print("=" * 30, "SYSTEM\n", s, "\n", "=" * 30, "USER\n", u)
        return

    call = A.GroqCaller(C.MODELS[a.model])
    with open(out, "a", encoding="utf-8") as fo:
        for i, r in enumerate(todo, 1):
            system, user, back, leak = messages_for(r, a.condition)
            votes, error = [], None
            try:
                for v in range(a.votes):
                    resp = call(system, user)
                    parsed = A.parse(resp["text"])
                    retried = False
                    if not A.schema_ok(parsed):  # deployed agent retries once
                        resp = call(system, user)
                        parsed = A.parse(resp["text"])
                        retried = True
                    rank, n_listed = A.ranking(parsed, r["candidates"], r["case_id"], back)
                    votes.append({"vote": v + 1, "raw": resp["text"], "parsed": parsed,
                                  "schema_ok": A.schema_ok(parsed), "retried": retried,
                                  "ranking": rank, "n_listed": n_listed,
                                  **{k: resp.get(k) for k in ("finish_reason", "has_reasoning_field",
                                                              "latency_s", "prompt_tokens",
                                                              "completion_tokens", "reasoning_tokens")}})
                    if a.sleep:
                        time.sleep(a.sleep)
            except A.QuotaExhausted as e:
                print(f"\nDaily quota reached after {i-1} cases. Rerun the same command later.\n{e}")
                break
            except Exception as e:  # noqa: BLE001  (one case must not stop the run)
                error = f"{type(e).__name__}: {str(e)[:500]}"
                print(f"[{i}/{len(todo)}] {r['case_id']} ERROR {error[:120]}")
            rec = {"case_id": r["case_id"], "model": a.model, "model_id": C.MODELS[a.model],
                   "condition": a.condition, "tag": a.tag,
                   "prompt_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest(),
                   "decoy": r["decoy"] if a.condition in ("decoy", "placebo") else None,
                   "anon_leaks": leak, "error": error,
                   "votes": votes, "ranking": votes[0]["ranking"] if (votes and not error) else None,
                   "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
            fo.write(json.dumps(rec) + "\n")
            fo.flush()
            if not error:
                print(f"[{i}/{len(todo)}] {r['case_id']} -> {rec['ranking'][0]} "
                      f"({votes[0]['latency_s']}s, {votes[0]['finish_reason']})")


if __name__ == "__main__":
    main()
