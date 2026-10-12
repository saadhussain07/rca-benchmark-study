"""Build the deployed context for a case, and derive the study conditions.

The deployed ContextBuilder (original/context_builder.py, sha256 in
PROTOCOL_V3.md) is imported and called unchanged. Only its clock is frozen to
the cycle time, so that the same case always yields the same text.
"""
import contextlib
import datetime as _dt
import importlib.util
import io
import os
import random
import re

from . import config as C

_HERE = os.path.dirname(os.path.abspath(__file__))
_CB_PATH = os.path.join(_HERE, "..", "original", "context_builder.py")


def _load_builder_module():
    spec = importlib.util.spec_from_file_location("deployed_context_builder", _CB_PATH)
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


_CB = _load_builder_module()


def _frozen_datetime(ts):
    fixed = _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc).replace(tzinfo=None)

    class FrozenDT(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    return FrozenDT


def build(metric_result, trace_result, log_result, cycle_ts):
    """Run the deployed ContextBuilder with its clock set to cycle_ts."""
    _CB.datetime = _frozen_datetime(cycle_ts)
    with contextlib.redirect_stdout(io.StringIO()):
        ctx = _CB.ContextBuilder().build_context(metric_result, trace_result, log_result)
    return ctx


# ================================================================== conditions
def strip_notes(summary):
    """E1 manipulation, unchanged from the earlier replay protocol: remove every
    line whose text, after leading whitespace, begins with 'NOTE:'."""
    kept, removed = [], 0
    for line in summary.split("\n"):
        if line.lstrip().startswith("NOTE:"):
            removed += 1
            continue
        kept.append(line)
    return "\n".join(kept), removed


# Decoy NOTE templates: the two deployed NOTE types that can occur on RCAEval
# (A5, A6 rule out the CPU-saturation and restart NOTEs), verbatim from the
# deployed builder with the decoy service substituted (PROTOCOL_V3.md 5.3).
DECOY_TEMPLATES = {
    "memory_pressure": (
        "    NOTE: {s}'s memory usage has increased substantially relative to its "
        "own baseline. Treat this as a RESOURCE/MEMORY-PRESSURE event: possible "
        "causes include a memory leak, an oversized batch operation, or an "
        "externally injected workload. This is a confirmed anomaly "
        "(verdict=ANOMALY_CONFIRMED), not a false positive."),
    "dependency": (
        "    NOTE: this error text specifically references {s} -- if {a} depends "
        "on a {s} service to function, consider whether the TRUE root cause is "
        "that dependency being unavailable, not {a} itself."),
}
# Placebo: names the decoy service in a NOTE line but makes no claim about it.
PLACEBO_TEMPLATE = "    NOTE: {s} is one of the services deployed in this cluster."


def decoy_assignment(case_id, candidates, root):
    """Seeded choice of decoy service (never the root cause) and template.
    Returns (None, None) when there is no non-root candidate."""
    rng = random.Random(f"{C.SEED}|decoy|{case_id}")
    pool = sorted(c for c in candidates if c != root)
    if not pool:
        return None, None
    return rng.choice(pool), rng.choice(sorted(DECOY_TEMPLATES))


def _first_affected(summary, exclude):
    for line in summary.split("\n"):
        if line.startswith("AFFECTED SERVICES:"):
            names = [x.strip() for x in line.split(":", 1)[1].split(",") if x.strip()]
            names = [n for n in names if n != exclude]
            if names:
                return names[0]
    return "the affected service"


def _insert_block(summary, note):
    """Insert note as its own block (blank line before it) just before the
    CORRELATED SIGNALS block or the TASK line."""
    lines = summary.split("\n")
    idx = len(lines)
    for i, l in enumerate(lines):
        if l.startswith("CORRELATED SIGNALS") or l.startswith("TASK:"):
            idx = i - 1 if (i > 0 and lines[i - 1] == "") else i
            break
    lines[idx:idx] = ["", note]
    return "\n".join(lines)


def add_decoy(stripped_summary, decoy_service, template):
    if decoy_service is None:
        return stripped_summary
    a = _first_affected(stripped_summary, decoy_service)
    return _insert_block(stripped_summary, DECOY_TEMPLATES[template].format(s=decoy_service, a=a))


def add_placebo(stripped_summary, decoy_service):
    if decoy_service is None:
        return stripped_summary
    return _insert_block(stripped_summary, PLACEBO_TEMPLATE.format(s=decoy_service))


# ================================================================ anonymising
# Names are replaced everywhere in the structured parts of the prompt
# (service lists, summary lines, JSON service fields). In raw log text
# (sample error lines, templates, reasons) only distinctive names are
# replaced -- names with a hyphen or ending in "service" -- so that ordinary
# words such as "user" or "payment" in a log message are not rewritten. Any
# service name left anywhere in the prompt is counted as a leak
# (PROTOCOL_V3.md 5.2, RQ4).
RAW_TEXT_KEYS = {"sample_error_log", "top_pattern", "pattern", "anomaly_reasons", "new_patterns"}


def anonymiser(case_id, services):
    rng = random.Random(f"{C.SEED}|anon|{case_id}")
    order = sorted(set(services))
    rng.shuffle(order)
    fwd = {s: f"service-{i + 1:02d}" for i, s in enumerate(order)}
    names = sorted(fwd, key=len, reverse=True)
    # name, optional pod-hash suffixes; case-insensitive; not inside a longer token
    pat = re.compile(r"(?<![\w-])(" + "|".join(re.escape(n) for n in names) +
                     r")((?:-[a-z0-9]{4,10}){0,2})(?![\w-])", re.IGNORECASE)
    lower = {k.lower(): v for k, v in fwd.items()}

    def apply(text):
        return pat.sub(lambda m: lower[m.group(1).lower()], text)

    distinct = [n for n in names if "-" in n or n.lower().endswith("service")]
    pat_d = (re.compile(r"(?<![\w-])(" + "|".join(re.escape(n) for n in distinct) +
                        r")((?:-[a-z0-9]{4,10}){0,2})(?![\w-])", re.IGNORECASE) if distinct else None)

    def apply_raw(text):
        return pat_d.sub(lambda m: lower[m.group(1).lower()], text) if pat_d else text

    apply.raw = apply_raw
    back = {v: k for k, v in fwd.items()}
    return apply, back, fwd


def anonymise_summary(summary, apply):
    out = []
    for line in summary.split("\n"):
        if line.lstrip().startswith("Sample error log:"):
            out.append(apply.raw(line))  # raw log text: distinctive names only
        elif line.lstrip().startswith("- ") and ("High error count" in line or "New log pattern" in line
                                                 or "Error logs mention" in line):
            head, _, rest = line.partition(":")
            out.append(apply(head) + ":" + apply.raw(rest))
        else:
            out.append(apply(line))
    return "\n".join(out)


def anonymise_obj(obj, apply, raw=False):
    if isinstance(obj, dict):
        return {k: anonymise_obj(v, apply, raw or k in RAW_TEXT_KEYS) for k, v in obj.items()}
    if isinstance(obj, list):
        return [anonymise_obj(v, apply, raw) for v in obj]
    if isinstance(obj, str):
        return apply.raw(obj) if raw else apply(obj)
    return obj


def leak_count(text, fwd):
    """Occurrences of any original service name left in text (case-insensitive)."""
    n = 0
    for name in fwd:
        n += len(re.findall(r"(?<![\w-])" + re.escape(name) + r"(?![\w])", text, flags=re.IGNORECASE))
    return n


# ======================================================== full anonymising
# Amendment 3 (exploratory C). Every spelling of every service name is
# replaced everywhere, raw log text included: the exact name, the name without
# Train Ticket's "ts-" prefix, and both with hyphens removed or replaced by "_"
# or a space, case-insensitively. Forms of 10 or more letters are also replaced
# inside longer identifiers (InsidePaymentServiceImpl); shorter forms only as
# whole tokens, where "_", ".", "/", "[" and the like count as token edges, so
# "[carts,,,]" and "catalogue_user" are caught. Benchmark and system names
# (Sock Shop, Online Boutique / hipstershop, Train Ticket, weave, fudan) become
# "app". Ordinary words that are not a spelling of a service name ("order",
# "payment" in Train Ticket logs) are left: they are meaning, not names, and
# are reported as residual cues.
SYSTEM_WORDS = r"sock[- ]?shop|socksdb|socks|weave|hipstershop|online[- ]?boutique|boutique|train[- ]?ticket|fudan"
_SYS_RE = re.compile(r"(?<![A-Za-z0-9])(" + SYSTEM_WORDS + r")(?![A-Za-z0-9])", re.IGNORECASE)


def name_forms(name):
    forms = {name}
    bases = {name}
    if name.startswith("ts-") and len(name) > 6:
        bases.add(name[3:])
    for b in bases:
        forms.update({b, b.replace("-", ""), b.replace("-", "_"), b.replace("-", " ")})
    return {f for f in forms if len(f) >= 3}


def _forms_regex(forms):
    """One alternation, longest form first. Forms of 10+ characters without a
    space match anywhere; shorter ones only between non-alphanumerics."""
    alt = "|".join((re.escape(f) if (len(f) >= 10 and " " not in f)
                    else r"(?<![A-Za-z0-9])" + re.escape(f) + r"(?![A-Za-z0-9])")
                   for f in sorted(forms, key=len, reverse=True))
    return re.compile("(?:" + alt + ")", re.IGNORECASE)


def anonymiser_full(case_id, services):
    """Same labels as anonymiser() for the same case; replaces every form of
    every name in all text. Returns (apply, back, fwd)."""
    _, back, fwd = anonymiser(case_id, services)
    form_label = {}
    for name in sorted(fwd, key=len, reverse=True):
        for f in name_forms(name):
            form_label.setdefault(f.lower(), fwd[name])
    rx = _forms_regex(set(form_label))

    def apply(text):
        text = rx.sub(lambda m: form_label[m.group(0).lower()], text)
        return _SYS_RE.sub("app", text)

    apply.raw = apply
    return apply, back, fwd


def leak_count_full(text, fwd):
    """Occurrences of any form of any service name, or of a system name, left
    in text (the same matching rules the full anonymiser uses)."""
    forms = set()
    for name in fwd:
        forms |= {f.lower() for f in name_forms(name)}
    rx = _forms_regex(forms)
    return len(rx.findall(text)) + len(_SYS_RE.findall(text))


# ======================================================== Amendment 6
# Two further text-only conditions (PROTOCOL_V3_AMENDMENT_6.md). Neither
# changes any earlier condition.
#
# nolog: every piece of raw log text is removed (the sample error line and the
#   mined log templates), while the log detector's output stays: which service
#   is flagged, its error and log counts, the reason strings without template
#   text, and the dependency keywords. The detector evidence is unchanged; only
#   the text a person would read is gone.
#
# permuted: the real service names are deranged among the candidate services
#   (seeded per case) and every spelling of every name is rewritten everywhere,
#   raw log text included, with the same matching rules as anonymiser_full.
#   Names keep looking like names, but each now points at a different service.
#   System names are kept.

_NEWPAT = "New log pattern detected: "


def _strip_reasons(reasons):
    return [("New log pattern detected" if r.startswith(_NEWPAT) else r) for r in reasons]


def strip_log_text(summary, ctx):
    """Return (summary, ctx, n_unmatched). n_unmatched counts LOG ANOMALIES
    lines that could not be matched exactly and were rewritten by pattern."""
    import copy
    lines = summary.split("\n")
    swap, unmatched = {}, 0
    for a in ctx.get("anomaly_details", {}).get("log_anomalies", []) or []:
        old = f"  - {a['service']}: " + "; ".join(a.get("anomaly_reasons", []))
        new = f"  - {a['service']}: " + "; ".join(_strip_reasons(a.get("anomaly_reasons", [])))
        swap[old] = new
    out, in_log = [], False
    for l in lines:
        if l.startswith("LOG ANOMALIES:"):
            in_log = True
        elif l and not l.startswith(" "):
            in_log = False
        if l.lstrip().startswith("Sample error log:"):
            continue
        if in_log and l in swap:
            out.append(swap[l])
            continue
        if in_log and _NEWPAT in l:
            unmatched += 1
            l = re.sub(r"New log pattern detected: .*?(?=; (?:High error count|Error logs mention|New log pattern)|$)",
                       "New log pattern detected", l)
        out.append(l)
    c = copy.deepcopy(ctx)
    for l in c.get("full_logs", []) or []:
        if isinstance(l.get("top_pattern"), dict):
            l["top_pattern"] = {"count": l["top_pattern"].get("count")}
        elif l.get("top_pattern") is not None:
            l["top_pattern"] = None
        l["sample_error_log"] = None
    return "\n".join(out), c, unmatched


def log_text_items(ctx):
    """Every raw log string the context carries (sample lines, templates)."""
    items = set()
    for l in (ctx.get("full_logs", []) or []):
        if l.get("sample_error_log"):
            items.add(l["sample_error_log"])
        tp = l.get("top_pattern")
        if isinstance(tp, dict) and tp.get("pattern"):
            items.add(tp["pattern"])
    for a in ctx.get("anomaly_details", {}).get("log_anomalies", []) or []:
        for p in a.get("new_patterns", []) or []:
            items.add(p)
        if a.get("sample_error_log"):
            items.add(a["sample_error_log"])
    return {s for s in items if isinstance(s, str) and len(s.strip()) >= 8 and s != "OTHER"}


def log_text_residue(text, ctx):
    """How many of the context's raw log strings still occur in text."""
    return sum(1 for s in log_text_items(ctx) if s in text)


def _typed_forms(name):
    """[(kind, variant, form)] for a lower-case service name."""
    bases = [("full", name)]
    if name.startswith("ts-") and len(name) > 6:
        bases.append(("strip", name[3:]))
    out = []
    for kind, b in bases:
        for var, sep in (("hy", "-"), ("none", ""), ("us", "_"), ("sp", " ")):
            f = b.replace("-", sep)
            if len(f) >= 3:
                out.append((kind, var, f))
    return out


def _render(target, kind, var, matched):
    base = target[3:] if (kind == "strip" and target.startswith("ts-") and len(target) > 6) else target
    sep = {"hy": "-", "none": "", "us": "_", "sp": " "}[var]
    if matched.islower() or not any(ch.isalpha() for ch in matched):
        return base.replace("-", sep)
    if matched.isupper():
        return base.replace("-", sep).upper()
    return sep.join(p[:1].upper() + p[1:] for p in base.split("-"))


def derangement(case_id, items):
    items = sorted(set(items))
    if len(items) < 2:
        return {s: s for s in items}
    rng = random.Random(f"{C.SEED}|perm|{case_id}")
    for _ in range(10000):
        perm = items[:]
        rng.shuffle(perm)
        if all(a != b for a, b in zip(items, perm)):
            return dict(zip(items, perm))
    perm = items[1:] + items[:1]  # cyclic shift: always a derangement
    return dict(zip(items, perm))


def _rewriter(mapping):
    """Single-pass rewrite of every typed form of every key name into the
    same form of its target, case pattern kept."""
    form_to = {}
    for src in sorted(mapping, key=len, reverse=True):
        tgt = mapping[src]
        for kind, var, f in _typed_forms(src):
            form_to.setdefault(f.lower(), (tgt, kind, var))
    rx = _forms_regex(set(form_to))

    def apply(text):
        def sub(m):
            tgt, kind, var = form_to[m.group(0).lower()]
            return _render(tgt, kind, var, m.group(0))
        return rx.sub(sub, text)

    apply.raw = apply
    return apply


def permuter(case_id, candidates, all_names):
    """Return (apply, inverse, resolve, fwd).
    fwd: real candidate -> displayed name. Non-candidate names that extend a
    candidate (e.g. carts-db) follow it; other names stay. resolve(s) maps a
    name in a model answer back to the real candidate, or None."""
    from .data import canonical
    cand = sorted(set(candidates))
    fwd = derangement(case_id, cand)
    full = dict(fwd)
    for n in sorted(set(all_names) - set(cand)):
        owner = next((c for c in sorted(cand, key=len, reverse=True) if n.startswith(c + "-")), None)
        if owner:
            full[n] = fwd[owner] + n[len(owner):]
    apply = _rewriter(full)
    forms = set()
    for n in set(full) | set(full.values()):
        forms |= {f.lower() for _, _, f in _typed_forms(n)}
    rx_all = re.compile("|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True)), re.IGNORECASE)

    def inverse(text):
        """Skeleton of a text: every spelling of every name removed, anywhere.
        A correct rewrite leaves the skeleton of the prompt unchanged."""
        return rx_all.sub("", text)
    back = {}
    for real, shown in full.items():
        tgt = canonical(real)
        for _, _, f in _typed_forms(shown):
            back.setdefault(f.lower(), tgt)

    def resolve(s):
        if not isinstance(s, str):
            return None
        k = s.strip().lower()
        if k in back:
            return back[k]
        k2 = canonical(k)
        return back.get(k2)

    return apply, inverse, resolve, fwd


def resolve_parsed(parsed, resolve):
    """Copy of a parsed answer with every service name mapped back through
    resolve(); names that resolve to nothing become empty strings, which the
    ranking rule drops."""
    if not isinstance(parsed, dict):
        return parsed
    out = dict(parsed)
    for key in ("ranked_root_cause_services", "root_cause_service", "affected_services"):
        v = parsed.get(key)
        if isinstance(v, str):
            out[key] = resolve(v) or ""
        elif isinstance(v, list):
            out[key] = [(resolve(x) or "") if isinstance(x, str) else x for x in v]
    return out
