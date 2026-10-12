#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-stop-condition-spec — a formal, declarative spec for agent stop
conditions (termination predicates), with structural validation, an
unreachable-termination detector, and a consistency test surface.

This is a spec + static checker, NOT a runtime termination implementation.
Framework built-ins (e.g. AutoGen TerminationCondition, LangGraph recursion
limits, Claude Code stop hooks) implement stopping at run time; this tool
lints the *declaration* of stop conditions before an agent ever runs.
Pure standard library, single file, offline.
"""
import argparse, json, re, sys, time

ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
TYPES = ("max_turns", "token_budget", "timeout_ms", "predicate", "no_progress", "handoff")
NUMERIC = {"max_turns": "value", "token_budget": "value", "timeout_ms": "value"}


def _err(findings, rule, severity, msg, ref=None):
    f = {"rule": rule, "severity": severity, "message": msg}
    if ref is not None:
        f["ref"] = ref
    findings.append(f)


def validate_spec(spec):
    """Structural validation. Returns findings."""
    findings = []
    if not isinstance(spec, dict):
        _err(findings, "R0", "error", "spec must be a JSON object")
        return findings
    conds = spec.get("conditions")
    if not isinstance(conds, list):
        _err(findings, "R1", "error", "conditions must be a list")
        return findings
    if not conds:
        _err(findings, "R1", "error", "conditions must not be empty (agent would never stop)")
        return findings
    ids = set()
    for i, c in enumerate(conds):
        ref = c.get("id") if isinstance(c, dict) else "#%d" % (i + 1)
        if not isinstance(c, dict):
            _err(findings, "R2", "error", "condition is not an object", ref)
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or not ID_RE.match(cid):
            _err(findings, "R2", "error", "id missing or not [A-Za-z_][A-Za-z0-9_]{0,63}", ref)
            continue
        if cid in ids:
            _err(findings, "R2", "error", "duplicate condition id", cid)
            continue
        ids.add(cid)
        ctype = c.get("type")
        if ctype not in TYPES:
            _err(findings, "R3", "error", "type must be one of %s" % "|".join(TYPES), cid)
            continue
        if ctype in NUMERIC:
            v = c.get("value")
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                _err(findings, "R4", "error", "%s requires an integer value > 0" % ctype, cid)
        if ctype == "predicate":
            expr = c.get("expression")
            if not isinstance(expr, str) or not expr.strip():
                _err(findings, "R5", "error", "predicate requires a non-empty expression", cid)
            mt = c.get("min_turns", 0)
            if not isinstance(mt, int) or isinstance(mt, bool) or mt < 0:
                _err(findings, "R5", "error", "min_turns must be an integer >= 0", cid)
        if ctype == "no_progress":
            w = c.get("window")
            if not isinstance(w, int) or isinstance(w, bool) or w < 2:
                _err(findings, "R6", "error", "no_progress requires an integer window >= 2", cid)
    ordering = spec.get("ordering", "any")
    if ordering not in ("any", "all"):
        _err(findings, "R7", "error", "ordering must be 'any' or 'all'")
    return findings


def check_unreachable(spec):
    """Unreachable-termination and consistency detection."""
    findings = []
    conds = spec.get("conditions") if isinstance(spec, dict) else None
    if not isinstance(conds, list) or not conds:
        _err(findings, "U1", "error", "no stop conditions declared: termination is unreachable")
        return findings
    ordering = spec.get("ordering", "any")
    max_turn_values = [c["value"] for c in conds
                       if isinstance(c, dict) and c.get("type") == "max_turns"
                       and isinstance(c.get("value"), int) and not isinstance(c.get("value"), bool)]
    smallest_max_turns = min(max_turn_values) if max_turn_values else None
    seen_types = {}
    for c in conds:
        if not isinstance(c, dict):
            continue
        ctype = c.get("type")
        if ctype in seen_types and seen_types[ctype] != c.get("value") and ctype in NUMERIC:
            if ordering == "all":
                _err(findings, "U3", "error",
                     "ordering=all with two '%s' conditions and different values is unsatisfiable" % ctype, c.get("id"))
            else:
                _err(findings, "U5", "warning",
                     "duplicate '%s' condition with a different value (first wins under ordering=any)" % ctype, c.get("id"))
        seen_types.setdefault(ctype, c.get("value"))
        if ctype == "predicate" and smallest_max_turns is not None:
            mt = c.get("min_turns", 0)
            if not isinstance(mt, int) or isinstance(mt, bool):
                continue
            if ordering == "all" and mt > smallest_max_turns:
                _err(findings, "U2", "error",
                     "predicate min_turns=%d can never fire before max_turns=%d under ordering=all"
                     % (mt, smallest_max_turns), c.get("id"))
            elif ordering == "any" and mt >= smallest_max_turns:
                _err(findings, "U4", "warning",
                     "predicate min_turns=%d can never fire before max_turns=%d stops the run"
                     % (mt, smallest_max_turns), c.get("id"))
        if ctype == "no_progress" and ordering == "all" and smallest_max_turns is not None:
            w = c.get("window")
            if isinstance(w, int) and not isinstance(w, bool) and w > smallest_max_turns:
                _err(findings, "U6", "warning",
                     "no_progress window=%d exceeds max_turns=%d under ordering=all"
                     % (w, smallest_max_turns), c.get("id"))
    return findings


def _has_error(findings):
    return any(f["severity"] == "error" for f in findings)


def _load(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _print(findings, as_json):
    if as_json:
        print(json.dumps({"findings": findings}, ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("OK: no findings")
        for f in findings:
            ref = " [%s]" % f["ref"] if f.get("ref") else ""
            print("%-7s %-4s%s %s" % (f["severity"], f["rule"], ref, f["message"]))


def _positive_int(text):
    try:
        v = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("not an integer: %r" % text)
    if v < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return v


def bench(n):
    specs = []
    for i in range(n):
        specs.append({"ordering": "any", "conditions": [
            {"id": "turns", "type": "max_turns", "value": 20 + (i % 30)},
            {"id": "pred", "type": "predicate", "expression": "state.done", "min_turns": i % 10},
            {"id": "budget", "type": "token_budget", "value": 1000 * (i + 1)},
        ]})
    t0 = time.perf_counter()
    total = sum(len(validate_spec(s)) + len(check_unreachable(s)) for s in specs)
    dt = time.perf_counter() - t0
    return n, total, dt


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="agent-stop-condition-spec",
        description="Validate and lint agent stop-condition specs (static; not a runtime implementation).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="structural validation of a spec file")
    pv.add_argument("spec")
    pv.add_argument("--json", action="store_true")

    pc = sub.add_parser("check", help="unreachable-termination and consistency detection")
    pc.add_argument("spec")
    pc.add_argument("--json", action="store_true")

    pb = sub.add_parser("bench", help="time validate+check on synthetic specs")
    pb.add_argument("--specs", type=_positive_int, default=5000)

    args = ap.parse_args(argv)
    if args.cmd == "bench":
        n, total, dt = bench(args.specs)
        print("specs=%d findings=%d in %.4fs (%.0f specs/s)"
              % (n, total, dt, n / dt if dt else 0))
        sys.exit(0)

    try:
        spec = _load(args.spec)
    except OSError as exc:
        print("error: cannot read %s: %s" % (args.spec, exc), file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print("error: invalid JSON in %s: %s" % (args.spec, exc), file=sys.stderr)
        sys.exit(1)

    findings = validate_spec(spec) if args.cmd == "validate" else check_unreachable(spec)
    _print(findings, args.json)
    sys.exit(1 if _has_error(findings) else 0)


if __name__ == "__main__":
    main()
