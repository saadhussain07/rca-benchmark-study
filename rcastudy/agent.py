"""The deployed agent's prompt, adapted only where the benchmark requires it.

Changes from original/runtime_anomaly_agent.py (PROTOCOL_V3.md section 4):
  B1 the service list in the system prompt is generated from the case's
     system instead of the hard-coded Online Boutique list with ports;
  B2 two keys are added to the JSON schema: root_cause_service and
     ranked_root_cause_services (at most 5), needed for Avg@k;
  B3 no conversation history (each case is an independent incident);
  B4 one vote per call in the main runs (K=5 on the check subset);
  B5 a <think>...</think> block, which some reasoning models put in the
     message text, is removed before the deployed JSON extraction.
Everything else (role text, data-source names, silence paragraph,
user-message template, temperature, max_tokens, JSON extraction) is copied
verbatim. Provider defaults are used for reasoning settings, as deployed.
"""
import json
import os
import random
import re
import time

from . import config as C

SYSTEM_TEMPLATE = """You are an expert AIOps Runtime Anomaly Detection Agent
for a Kubernetes cloud-native environment.

Your role is to:
1. Analyze runtime telemetry data (metrics, traces, logs)
2. Identify genuine anomalies vs normal behavior
3. Determine root cause of detected anomalies
4. Recommend specific, actionable remediation steps
5. Assess confidence level of your analysis

You have access to data from:
- Prometheus metrics (CPU, memory, error rates)
- Jaeger distributed traces (latency, errors)
- Loki log streams (error patterns, warnings)

Services in the cluster:
{service_lines}

IMPORTANT: If a service that is normally expected to report metrics is
MISSING from the telemetry entirely (metrics_present: false), treat that
absence itself as evidence -- a terminated or crashed pod stops emitting
metrics, which is a distinct signature from a running pod with normal
metrics. Do not default root-cause attribution to whichever service DOES
have visible anomalous metrics if a silent service is a more likely
origin (e.g. a dependency the visible service calls).

Always respond in this exact JSON format:
{{
  "verdict": "ANOMALY_CONFIRMED" or "FALSE_POSITIVE" or "NORMAL",
  "confidence": 0.0 to 1.0,
  "severity": "CRITICAL" or "HIGH" or "MEDIUM" or "LOW" or "NORMAL",
  "affected_services": ["service1", "service2"],
  "root_cause_service": "the single service most likely to be the origin of the fault",
  "ranked_root_cause_services": ["most likely", "second", "third", "fourth", "fifth"],
  "root_cause": "Detailed explanation of root cause",
  "evidence": ["evidence1", "evidence2"],
  "remediation_steps": [
    {{"step": 1, "action": "specific kubectl command", "reason": "...", "risk": "LOW/MEDIUM/HIGH"}}
  ],
  "auto_remediate": true or false,
  "escalate_to_human": true or false,
  "explanation": "Human readable summary"
}}"""

USER_TEMPLATE = """
Analyze the following runtime telemetry from our Kubernetes cluster:

{llm_summary}

Additional context:
- Total metric anomalies: {n_metric}
- Total trace anomalies: {n_trace}
- Total log anomalies: {n_log}
- Affected services: {affected}
- Silent services (no telemetry this cycle): {silent}
- Requires immediate action: {requires_action}

Anomalous metrics (only flagged services):
{anomalous_metrics}

Anomalous logs (only flagged services):
{anomalous_logs}

Please analyze and provide your verdict in the exact JSON format specified.
"""

REQUIRED_KEYS = ["verdict", "confidence", "severity", "root_cause"]


def build_messages(ctx, summary, services):
    """Return (system, user) text. `summary` replaces ctx['summary_for_llm']
    so that conditions can be applied; everything else comes from ctx."""
    service_lines = "\n".join(f"- {s}" for s in services)
    system = SYSTEM_TEMPLATE.format(service_lines=service_lines)
    full_metrics = ctx.get("full_metrics", [])
    full_logs = ctx.get("full_logs", [])
    user = USER_TEMPLATE.format(
        llm_summary=summary,
        n_metric=ctx.get("total_anomalies", {}).get("metrics", 0),
        n_trace=ctx.get("total_anomalies", {}).get("traces", 0),
        n_log=ctx.get("total_anomalies", {}).get("logs", 0),
        affected=ctx.get("affected_services", []),
        silent=[],  # deployed collector always reports every service (A11)
        requires_action=ctx.get("requires_action", False),
        anomalous_metrics=json.dumps([m for m in full_metrics if m.get("is_anomaly")], indent=2),
        anomalous_logs=json.dumps([l for l in full_logs if l.get("is_anomaly")], indent=2),
    )
    return system, user


def parse(text):
    """JSON extraction copied from the deployed agent (after B5)."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)
    try:
        start, end = text.find("{"), text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {"raw_response": text}


def schema_ok(result):
    return all(k in result for k in REQUIRED_KEYS)


def ranking(result, candidates, case_id, back=None):
    """Turn a response into a full ranking over the candidate services.

    Order: ranked_root_cause_services, then root_cause_service, then
    affected_services; names are mapped back from anonymised form, folded
    with canonical(), and kept only if they are candidates. The remaining
    candidates follow in a seeded random order (chance fill), so unlisted
    services earn no credit beyond chance.
    """
    from .data import canonical
    back = back or {}
    listed = []
    srcs = []
    for key in ("ranked_root_cause_services", "root_cause_service", "affected_services"):
        v = result.get(key)
        if isinstance(v, str):
            v = [v]
        if isinstance(v, list):
            srcs.extend(v)
    cand = set(candidates)
    for s in srcs:
        if not isinstance(s, str):
            continue
        s = s.strip()
        s = back.get(s, s)
        s = canonical(s)
        if s in cand and s not in listed:
            listed.append(s)
    rest = sorted(c for c in candidates if c not in listed)
    random.Random(f"{C.SEED}|fill|{case_id}").shuffle(rest)
    return listed + rest, len(listed)


class GroqCaller:
    """Thin client with backoff. Stops cleanly on a daily-quota error."""

    def __init__(self, model_id):
        from groq import Groq
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.model_id = model_id

    def __call__(self, system, user):
        delay = 5
        for attempt in range(8):
            try:
                t0 = time.time()
                r = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    max_tokens=C.MAX_TOKENS, temperature=C.TEMPERATURE)
                usage = getattr(r, "usage", None)
                details = getattr(usage, "completion_tokens_details", None)
                msg_obj = r.choices[0].message
                return {"text": msg_obj.content or "",
                        "finish_reason": r.choices[0].finish_reason,
                        "has_reasoning_field": bool(getattr(msg_obj, "reasoning", None)),
                        "latency_s": round(time.time() - t0, 2),
                        "prompt_tokens": getattr(usage, "prompt_tokens", None),
                        "completion_tokens": getattr(usage, "completion_tokens", None),
                        "reasoning_tokens": getattr(details, "reasoning_tokens", None) if details else None}
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "rate_limit_exceeded" in msg and ("per day" in msg or "TPD" in msg or "RPD" in msg):
                    raise QuotaExhausted(msg)
                if "Error code: 413" in msg or "too large" in msg.lower() or "context_length_exceeded" in msg:
                    raise RequestTooLarge(msg)  # retrying cannot help
                if "rate_limit" in msg or "429" in msg or "503" in msg or "timeout" in msg.lower():
                    time.sleep(delay)
                    delay = min(delay * 2, 120)
                    continue
                raise
        raise RuntimeError("too many retries")


class QuotaExhausted(Exception):
    pass


class RequestTooLarge(Exception):
    pass
