# Changelog — agent-stop-condition-spec

All releases are local drafts; no remote operations are performed.

## v0.1.1 — 2026-10-13

Fixed:
- duplicate numeric conditions with equal values no longer trigger U3/U5
  (only *different* values are conflicts).

Changed:
- self_test expanded to 65 cases across functional / exception / extreme-edge
  categories (scaffold v2 four defenses: SystemExit capture, Unicode-safe
  matching, Windows newline-safe fixtures, SUMMARY last line).
- README: How-this-differs section rewritten against framework built-ins
  (AutoGen TerminationCondition / LangGraph / CrewAI) at the spec-vs-runtime
  layer; Performance re-measured via the shipped `bench` subcommand.

## v0.1.0 — 2026-10-13

Added:
- Initial local draft: stop-condition spec schema (six condition types +
  ordering semantics), structural validation R1–R7, unreachable-termination
  checks U1–U6, argparse CLI (validate / check / bench) and scaffold-v2
  self_test.
