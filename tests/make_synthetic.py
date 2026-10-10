"""Write a small synthetic RCAEval-format dataset (Zenodo layout) for testing
the pipeline end to end. Not used in the study."""
import os
import sys

import numpy as np
import pandas as pd

OB = ["frontend", "cartservice", "currencyservice", "paymentservice", "productcatalogservice", "redis"]
SS = ["front-end", "carts", "carts-db", "orders", "payment", "user"]


def case(root, sysdir, services, svc, fault, rep, seed, traces=True):
    rng = np.random.default_rng(seed)
    d = os.path.join(root, sysdir, f"{svc}_{fault}", str(rep))
    os.makedirs(d, exist_ok=True)
    t0, inj = 1_700_000_000, 1_700_000_000 + 900
    t = np.arange(t0, inj + 600)
    cols = {"time": t}
    for s in services:
        base_cpu = rng.uniform(0.5, 20)
        base_mem = rng.uniform(20e6, 200e6)
        cpu = base_cpu + rng.normal(0, base_cpu * 0.05, len(t))
        mem = base_mem + rng.normal(0, base_mem * 0.01, len(t))
        lat = 0.01 + rng.normal(0, 0.001, len(t))
        if s == svc:
            after = t >= inj
            if fault == "cpu":
                cpu[after] *= 4
            if fault == "mem":
                mem[after] += 80e6
            if fault == "delay":
                lat[after] += 0.5
        cols[f"{s}_cpu"], cols[f"{s}_mem"], cols[f"{s}_latency-90"] = cpu, mem, lat
    pd.DataFrame(cols).to_csv(os.path.join(d, "data.csv"), index=False)
    with open(os.path.join(d, "inject_time.txt"), "w") as f:
        f.write(str(inj))
    # logs
    rows = []
    for s in services:
        for ts in range(t0, inj + 600, 7):
            lvl, msg = "info", "request served"
            if s == svc and ts >= inj and fault in ("delay", "loss") and rng.random() < 0.5:
                lvl, msg = "error", f"rpc error: code = Unavailable desc = connection refused to {s}"
            rows.append({"time": "00:00", "timestamp": int(ts * 1e9), "container_name": f"{s}",
                         "message": msg, "level": lvl})
    pd.DataFrame(rows).to_csv(os.path.join(d, "logs.csv"), index=False)
    if traces:
        rows = []
        for k, ts in enumerate(range(t0, inj + 600, 3)):
            tid = f"t{k}"
            for s in services[:4]:
                dur = 2000 + rng.normal(0, 100)
                code = 0
                if s == svc and ts >= inj and fault == "delay":
                    dur += 2_500_000
                if s == svc and ts >= inj and fault == "loss" and rng.random() < 0.3:
                    code = 2
                rows.append({"traceID": tid, "spanID": f"{tid}-{s}", "serviceName": s + "service" if s == "frontend" else s,
                             "operationName": f"{s}/op", "startTime": int(ts * 1e6), "duration": int(dur),
                             "statusCode": code})
        pd.DataFrame(rows).to_csv(os.path.join(d, "traces.csv"), index=False)


def main(root):
    seed = 0
    for svc in ["cartservice", "paymentservice", "currencyservice"]:
        for fault in ["cpu", "mem", "delay", "loss"]:
            for rep in (1, 2):
                seed += 1
                case(os.path.join(root, "RE2"), "RE2-OB", OB, svc, fault, rep, seed)
    for svc in ["carts", "orders"]:
        for fault in ["cpu", "mem"]:
            seed += 1
            case(os.path.join(root, "RE2"), "RE2-SS", SS, svc, fault, 1, seed, traces=False)
    seed += 1
    case(root, "online-boutique", OB, "cartservice", "cpu", 1, seed, traces=False)


if __name__ == "__main__":
    main(sys.argv[1])
