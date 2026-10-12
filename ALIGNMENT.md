# Alignment Audit — agent-stop-condition-spec

Round R14, rubric v4.0 (E/F graded). Local-only draft: no git remote, no push, no repo creation.
Date: 2026-10-13.

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Runnable Python, pure stdlib | PASS | agent_stop_condition_spec.py imports argparse/json/re/sys/time only; `python agent_stop_condition_spec.py --help` runs |
| 2 | argparse CLI | PASS | subcommands validate/check/bench; `--json` on validate+check; usage errors exit 2 |
| 3 | self_test inherits scaffold-v2 four defenses | PASS | D1 SystemExit caught in run_cli; D2 CJK/emoji fixtures (c02–c04); D3 fixtures via newline="" (c14, _write); D4 last line `SUMMARY: PASS n/n` |
| 4 | E gate >=60 cases, 3 categories | PASS | SUMMARY: PASS 65/65 — [A] 25 functional / [B] 20 exception / [C] 22 extreme edge, incl. empty/oversized/unicode/BOM/CRLF inputs |
| 5 | SUMMARY last-line contract | PASS | `python self_test.py` prints `SUMMARY: PASS 65/65` as final line; meta-case asserts len(CASES)>=60 |
| 6 | README English, <=60-word lead | PASS | README.md opening paragraph is 57 words, English |
| 7 | README Problem section | PASS | README.md '## Problem' |
| 8 | README How-it-works | PASS | README.md '## How it works' (incl. rule table) |
| 9 | README Quickstart with timing | PASS | README.md '## Quickstart' cites run times |
| 10 | why-not-X >=3 alternatives | PASS | README.md '## Why not X' lists 4 alternatives incl. the real anchor (AutoGen TerminationCondition / framework built-ins); adjacent per _r14_design.json |
| 11 | Performance [Measured] + repro command | PASS | README.md '## Performance' table with `python agent_stop_condition_spec.py bench --specs 5000` repro command |
| 12 | Minimal Fallback | PASS | README.md '## Minimal Fallback' (Markdown table + review) |
| 13 | Design Trade-offs | PASS | README.md '## Design Trade-offs' (4 entries) |
| 14 | Limits & Second-order Effects | PASS | README.md '## Limits & Second-order Effects' (4 entries) |
| 15 | FAQ incl When NOT to use | PASS | README.md '## FAQ' first item is 'When NOT to use this?' |
| 16 | Core Assumptions >=3 + confidence + as-of + hygiene | PASS | README.md '[Core Assumptions]' lists 4 assumptions with confidence line and 'As of 2026-10-13'; MIT LICENSE (zhengming contributors); CHANGELOG.md v0.1.0 -> v0.1.1; no secrets, no real names, contact limited to hcac4735@agent.qq.com |
| F2 | Anchor read before writing How-this-differs | PASS | Anchor = AutoGen TerminationCondition / LangGraph / CrewAI framework built-ins (per _r14_design.json: no independent standalone tool exists); dedicated section 'How this differs from framework built-ins' written at the spec-vs-runtime layer, factual framing, no disparagement; design-jason anchor note (WebSearch 2026-10-12) re-verified against the 2026-10-13 README pass |

Round-2 iterations: equal-value duplicate conditions no longer flagged (U3/U5 narrowed);
case count raised into the 60-85 band; How-this-differs tightened; Performance re-measured; all green.
