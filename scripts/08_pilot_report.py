"""Pilot report: does the plumbing work? Accuracy is deliberately not shown
(PROTOCOL_V3.md section 8: pilot accuracy may not be used to change anything).

usage: python scripts/08_pilot_report.py --ctx out/pilot_re1 [--ctx out/pilot_re3 ...]
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import agent as A  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctx", action="append", required=True)
    a = ap.parse_args()
    for d in a.ctx:
        recs = [json.loads(l) for l in open(os.path.join(d, "contexts.jsonl"), encoding="utf-8") if l.strip()]
        print(f"\n=== {d}: {len(recs)} cases")
        print(f"{'case':42s} {'built':5s} {'flag':4s} {'sev':8s} {'sig m/t/l':9s} {'notes':5s} {'prompt_chars':12s} warnings")
        for r in recs:
            if r.get("build_failed"):
                print(f"{r['case_id']:42s} FAIL")
                continue
            s, u = A.build_messages(r["context"], r["summary"]["annotated"], r["candidates"])
            sig = r["signals"]
            print(f"{r['case_id']:42s} {'ok':5s} {str(r['flagged'])[0]:4s} {str(r['severity']):8s} "
                  f"{sig.get('metrics',0)}/{sig.get('traces',0)}/{sig.get('logs',0):<5} {r['n_notes']:<5d} "
                  f"{len(s)+len(u):<12d} {'; '.join(r.get('warnings', []))}")
        for p in sorted(glob.glob(os.path.join(d, "llm", "*.jsonl"))):
            rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
            print(f"\n  model responses: {os.path.basename(p)} ({len(rows)} records)")
            print(f"  {'case':42s} {'error':6s} {'schema':6s} {'retry':5s} {'finish':8s} {'listed':6s} "
                  f"{'in_tok':7s} {'out_tok':7s} {'reason_tok':10s} {'sec':5s}")
            for x in rows:
                if x.get("error"):
                    print(f"  {x['case_id']:42s} {x['error'][:90]}")
                    continue
                v = x["votes"][0]
                keys_ok = all(k in v["parsed"] for k in ("root_cause_service", "ranked_root_cause_services"))
                print(f"  {x['case_id']:42s} {'-':6s} {str(v['schema_ok'])[0]}{'+' if keys_ok else '-'}{'':4s} "
                      f"{str(v['retried'])[0]:5s} {str(v.get('finish_reason')):8s} {v['n_listed']:<6d} "
                      f"{str(v.get('prompt_tokens')):7s} {str(v.get('completion_tokens')):7s} "
                      f"{str(v.get('reasoning_tokens')):10s} {v.get('latency_s')}")
            print("  schema column: first letter = required keys present; + = ranking keys present")


if __name__ == "__main__":
    main()
