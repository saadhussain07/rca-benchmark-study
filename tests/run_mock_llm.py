"""Run 04_run_llm.py with a fake model, for pipeline tests only."""
import json
import os
import random
import runpy
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rcastudy import agent as A  # noqa: E402


class Fake:
    def __init__(self, model_id):
        self.rng = random.Random(model_id)

    def __call__(self, system, user):
        names = [l[2:].strip() for l in system.split("\n") if l.startswith("- ")]
        aff = []
        for line in user.split("\n"):
            if line.startswith("AFFECTED SERVICES:"):
                aff = [s.strip() for s in line.split(":", 1)[1].split(",")] + aff
            if "NOTE:" in line and "is one of the services" not in line:
                hit = [n for n in names if n in line and n not in aff[:1]]
                aff = hit[:1] + aff
        if self.rng.random() < 0.2:
            self.rng.shuffle(aff)
        return {"text": "thinking...\n" + json.dumps({"verdict": "ANOMALY_CONFIRMED", "confidence": 0.9,
                "severity": "HIGH", "root_cause": "x", "root_cause_service": aff[0] if aff else "",
                "ranked_root_cause_services": aff[:5]}),
                "latency_s": 0.0, "prompt_tokens": len(user) // 4, "completion_tokens": 50}


A.GroqCaller = Fake
sys.argv = ["04_run_llm.py"] + sys.argv[1:]
runpy.run_path(os.path.join(os.path.dirname(__file__), "..", "scripts", "04_run_llm.py"), run_name="__main__")
