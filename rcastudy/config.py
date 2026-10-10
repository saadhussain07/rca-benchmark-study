"""Frozen study constants.

Every value here is either (a) copied from the deployed system, with the
source file and line it came from, or (b) a benchmark-adaptation choice
declared in PROTOCOL_V3.md section 4. Nothing in this file may change after
the protocol is frozen without a numbered amendment.
"""

# ---------------------------------------------------------------- windows
# All methods see the same 20-minute window, following RCAEval main.py
# (--length 20): the 10 minutes before injection and the 10 minutes after.
NORMAL_WINDOW_S = 600
ANOMAL_WINDOW_S = 600
# One evaluation cycle per case, at the end of the anomalous window.
CYCLE_OFFSET_S = 600

# ------------------------------------------------- metrics (metric_collector.py)
RESAMPLE_STEP_S = 30            # Prometheus query step, MC:280-299
METRIC_LOOKBACK_S = 600         # per-cycle CPU range, minutes=10, MC:483
ROLLING_STD_SAMPLES = 6         # current + previous 5 samples, MC:224-238
IF_CONTAMINATION = 0.1          # MC:240
IF_RANDOM_STATE = 42            # MC:240
THRESHOLD_PERCENTILE = 95.0     # MC:121, 244
MIN_BASELINE_SAMPLES = 10       # MC:209-222
CPU_FLOOR_P95_MULT = 1.5        # MC:612-616
# Deployed absolute floor is 0.005 cores (MC:89). RCAEval's CPU unit is not
# documented; CPU_TO_CORES converts it. It is set before the freeze by the
# decision rule in PROTOCOL_V3.md section 8, applied to the normal-window CPU
# ranges printed by scripts/01_inspect.py. None disables the absolute floor
# and keeps only the relative 1.5 x p95 floor.
MIN_MEANINGFUL_CPU_CORES = 0.005
CPU_TO_CORES = 0.01             # section 8 rule, 2026-10-10: percent of one core in RE1, RE2, RE3
MEM_BYTES_PER_MB = 1024 * 1024  # MC: memory_mb = bytes / 1024^2 (RCAEval: bytes)
TRACE_DURATION_TO_US = 1.0      # RCAEval span duration assumed in microseconds
# The deployed error-rate feature was the constant 1.0 in every logged record
# (no Istio; system_spec.md section 1.1). It is kept constant here.
ERROR_RATE_CONSTANT = 1.0

# ------------------------------------------------ traces (trace_analyser.py)
TRACE_LOOKBACK_S = 600          # start_time = now - 10 min
TRACE_LIMIT = 100               # Jaeger limit=100 traces per service
LATENCY_THRESHOLD_MS = 2000
ERROR_RATE_THRESHOLD = 0.05

# ------------------------------------------------------ logs (log_parser.py)
LOG_LOOKBACK_S = 300            # Loki query minutes=5
LOG_LIMIT = 500                 # Loki limit=500
LOG_ERROR_THRESHOLD = 10
ERROR_WORDS = ["error", "exception", "failed", "refused", "timeout"]
DEPENDENCY_KEYWORDS = {
    "redis": ["redis", "stackexchange.redis"],
    "grpc": ["grpc", "unavailable", "deadline exceeded"],
    "dns": ["no such host", "name resolution", "dns"],
}

# --------------------------------------------- agent (runtime_anomaly_agent.py)
TEMPERATURE = 0.1
MAX_TOKENS = 3000
N_VOTES_MAIN = 1                # declared deviation; deployed K = 5
N_VOTES_CHECK = 5               # first-vote check subset
N_VOTE_CHECK_CASES = 30
# Groq reasoning settings are left at provider defaults, as deployed; the
# response's finish_reason and reasoning-token count are logged per call.
MODELS = {
    "gpt-oss-120b": "openai/gpt-oss-120b",   # deployed model
    "gpt-oss-20b": "openai/gpt-oss-20b",
    "qwen3.8-27b": "qwen/qwen3.8-27b",
}
DEPLOYED_MODEL = "gpt-oss-120b"
MAX_RANKED = 5

# ------------------------------------------------------------- randomness
SEED = 20261010

FAULTS = ["cpu", "mem", "disk", "socket", "delay", "loss"]
SYSTEMS = {"ob": "Online Boutique", "ss": "Sock Shop", "tt": "Train Ticket"}
