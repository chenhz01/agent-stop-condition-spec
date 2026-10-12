# -*- coding: utf-8 -*-
"""self_test for agent-stop-condition-spec — inherits scaffold v2 four defenses:
  D1 SystemExit/BaseException capture in run_cli
  D2 Unicode-safe patterns (CJK/emoji fixtures)
  D3 fixtures written with newline="" (Windows CRLF safe)
  D4 last line `SUMMARY: PASS n/n`
"""
import contextlib, io, json, os, sys, tempfile, unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib
mod = importlib.import_module("agent_stop_condition_spec")
main = mod.main


def run_cli(argv):
    """D1: catch SystemExit and Exception; return (code, stdout, stderr)."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


def _write(text, suffix=".json"):
    """D3: newline="" prevents \r\n double-write on Windows."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return path


def _spec(*conds, **kw):
    s = {"ordering": kw.pop("ordering", "any"), "conditions": list(conds)}
    s.update(kw)
    return json.dumps(s)


def _turns(v=20):
    return {"id": "turns", "type": "max_turns", "value": v}


def _pred(expr="state.done", mt=1):
    return {"id": "done", "type": "predicate", "expression": expr, "min_turns": mt}


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


# ---------------- [A] functional ----------------

@case
def a01_validate_good_spec():
    p = _write(_spec(_turns(), _pred()))
    code, out, _ = run_cli(["validate", p])
    assert code == 0 and "OK" in out


@case
def a02_validate_json_output():
    p = _write(_spec(_turns()))
    code, out, _ = run_cli(["validate", p, "--json"])
    assert code == 0 and json.loads(out)["findings"] == []


@case
def a03_check_clean_spec():
    p = _write(_spec(_turns(), _pred()))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "OK" in out


@case
def a04_u1_empty_conditions_error():
    p = _write(_spec())
    code, out, _ = run_cli(["check", p])
    assert code == 1 and "U1" in out


@case
def a05_u2_all_ordering_predicate_unreachable():
    p = _write(_spec(_turns(5), _pred(mt=10), ordering="all"))
    code, out, _ = run_cli(["check", p])
    assert code == 1 and "U2" in out


@case
def a06_u4_any_ordering_predicate_never_fires():
    p = _write(_spec(_turns(5), _pred(mt=5), ordering="any"))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "U4" in out


@case
def a07_u3_all_duplicate_numeric_conflict():
    p = _write(_spec(_turns(10), {"id": "turns2", "type": "max_turns", "value": 99}, ordering="all"))
    code, out, _ = run_cli(["check", p])
    assert code == 1 and "U3" in out


@case
def a08_u5_any_duplicate_numeric_warning():
    p = _write(_spec(_turns(10), {"id": "turns2", "type": "max_turns", "value": 99}))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "U5" in out


@case
def a09_u6_no_progress_window_exceeds_turns():
    p = _write(_spec(_turns(3), {"id": "stall", "type": "no_progress", "window": 10}, ordering="all"))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "U6" in out


@case
def a10_r1_empty_conditions_on_validate():
    p = _write(_spec())
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R1" in out


@case
def a11_r2_duplicate_id():
    p = _write(_spec(_turns(10), _turns(20)))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def a12_r3_unknown_type():
    p = _write(_spec({"id": "x", "type": "vibes", "value": 1}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R3" in out


@case
def a13_r4_zero_max_turns():
    p = _write(_spec(_turns(0)))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R4" in out


@case
def a14_r5_empty_expression():
    p = _write(_spec({"id": "p", "type": "predicate", "expression": "  "}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R5" in out


@case
def a15_r6_window_below_two():
    p = _write(_spec({"id": "s", "type": "no_progress", "window": 1}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R6" in out


@case
def a16_r7_bad_ordering():
    p = _write(_spec(_turns(), ordering="sometimes"))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R7" in out


@case
def a17_all_types_accepted():
    conds = [_turns(30), {"id": "b", "type": "token_budget", "value": 5000},
             {"id": "t", "type": "timeout_ms", "value": 60000}, _pred(),
             {"id": "s", "type": "no_progress", "window": 3},
             {"id": "h", "type": "handoff"}]
    p = _write(_spec(*conds))
    code, out, _ = run_cli(["validate", p])
    assert code == 0


@case
def a18_bench_small():
    code, out, _ = run_cli(["bench", "--specs", "50"])
    assert code == 0 and "specs=50" in out


@case
def a19_bench_default():
    code, out, _ = run_cli(["bench"])
    assert code == 0 and "specs/s" in out


@case
def a20_help_exit0():
    code, out, _ = run_cli(["--help"])
    assert code == 0 and "agent-stop-condition-spec" in out


@case
def a21_no_args_exit2():
    code, _, _ = run_cli([])
    assert code == 2


@case
def a22_unknown_subcommand_exit2():
    code, _, _ = run_cli(["halt-everything"])
    assert code == 2


@case
def a23_direct_validate_function():
    assert mod.validate_spec({"ordering": "any", "conditions": [_turns()]}) == []


@case
def a24_direct_check_function():
    f = mod.check_unreachable({"ordering": "any", "conditions": []})
    assert f[0]["rule"] == "U1"


@case
def a25_missing_file():
    code, _, err = run_cli(["validate", "Z:/no/spec.json"])
    assert code == 1 and "cannot read" in err


# ---------------- [B] exception paths ----------------

@case
def b01_invalid_json():
    p = _write("{nope")
    code, _, err = run_cli(["validate", p])
    assert code == 1 and "invalid JSON" in err


@case
def b02_spec_is_list():
    p = _write("[]")
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R0" in out


@case
def b03_spec_is_string():
    p = _write('"x"')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R0" in out


@case
def b04_conditions_not_list():
    p = _write('{"conditions": {"id": "x"}}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R1" in out


@case
def b05_condition_not_object():
    p = _write('{"conditions": [42]}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def b06_id_is_number():
    p = _write('{"conditions": [{"id": 7, "type": "max_turns", "value": 5}]}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def b07_value_is_string():
    p = _write('{"conditions": [{"id": "t", "type": "max_turns", "value": "20"}]}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R4" in out


@case
def b08_value_is_bool():
    p = _write('{"conditions": [{"id": "t", "type": "max_turns", "value": true}]}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R4" in out


@case
def b09_value_negative():
    p = _write('{"conditions": [{"id": "t", "type": "token_budget", "value": -5}]}')
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R4" in out


@case
def b10_min_turns_negative():
    p = _write(_spec({"id": "p", "type": "predicate", "expression": "x", "min_turns": -1}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R5" in out


@case
def b11_min_turns_is_string():
    p = _write(_spec({"id": "p", "type": "predicate", "expression": "x", "min_turns": "1"}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R5" in out


@case
def b12_window_is_string():
    p = _write(_spec({"id": "s", "type": "no_progress", "window": "3"}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R6" in out


@case
def b13_bench_specs_zero():
    code, _, _ = run_cli(["bench", "--specs", "0"])
    assert code == 2


@case
def b14_bench_specs_negative():
    code, _, _ = run_cli(["bench", "--specs", "-1"])
    assert code == 2


@case
def b15_bench_specs_not_int():
    code, _, _ = run_cli(["bench", "--specs", "many"])
    assert code == 2


@case
def b16_check_on_missing_file():
    code, _, err = run_cli(["check", "Z:/no/spec.json"])
    assert code == 1 and "cannot read" in err


@case
def b17_truncated_json():
    p = _write('{"conditions": [')
    code, _, err = run_cli(["check", p])
    assert code == 1 and "invalid JSON" in err


@case
def b18_empty_file():
    p = _write("")
    code, _, _ = run_cli(["validate", p])
    assert code == 1


@case
def b19_whitespace_only():
    p = _write(" \t\n ")
    code, _, _ = run_cli(["validate", p])
    assert code == 1


@case
def b20_directory_as_input():
    code, _, err = run_cli(["validate", os.path.dirname(os.path.abspath(__file__))])
    assert code == 1 and "cannot read" in err


# ---------------- [C] extreme / edge ----------------

@case
def c01_utf8_bom_spec():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(p, "wb") as fh:
        fh.write(b"\xef\xbb\xbf" + _spec(_turns()).encode("utf-8"))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c02_unicode_cjk_expression():
    p = _write(_spec({"id": "p", "type": "predicate", "expression": "状态.完成 == true"}))
    code, out, _ = run_cli(["validate", p])
    assert code == 0  # expression is opaque text


@case
def c03_unicode_cjk_id_rejected():
    p = _write(_spec({"id": "终止", "type": "max_turns", "value": 5}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def c04_unicode_emoji_expression():
    p = _write(_spec({"id": "p", "type": "predicate", "expression": "done \U0001f680"}))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c05_huge_expression_100k():
    p = _write(_spec({"id": "p", "type": "predicate", "expression": "x or " * 20000 + "y"}))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c06_huge_turn_value_ok():
    p = _write(_spec(_turns(10**12)))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c07_min_turns_zero_ok():
    p = _write(_spec(_turns(5), _pred(mt=0)))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "OK" in out


@case
def c08_min_turns_equals_max_any_warning():
    p = _write(_spec(_turns(5), _pred(mt=5)))
    code, out, _ = run_cli(["check", p])
    assert "U4" in out


@case
def c09_min_turns_above_max_any_warning():
    p = _write(_spec(_turns(5), _pred(mt=9)))
    code, out, _ = run_cli(["check", p])
    assert "U4" in out


@case
def c10_predicate_only_spec_clean():
    p = _write(_spec(_pred()))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "OK" in out


@case
def c11_handoff_only_spec_clean():
    p = _write(_spec({"id": "h", "type": "handoff"}))
    code, out, _ = run_cli(["check", p])
    assert code == 0


@case
def c12_extra_spec_keys_ignored():
    p = _write('{"ordering": "any", "conditions": [%s], "version": 3}' % json.dumps(_turns()))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c13_extra_condition_keys_ignored():
    p = _write(_spec(dict(_turns(), owner="team")))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c14_crlf_file():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(p, "w", encoding="utf-8", newline="") as fh:  # D3
        fh.write(_spec(_turns()).replace("\n", "\r\n"))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c15_100_conditions_bulk():
    conds = [{"id": "c%03d" % i, "type": "max_turns", "value": i + 1} for i in range(1, 100)]
    p = _write(_spec(*conds))
    code, out, _ = run_cli(["validate", p])
    assert code == 0  # duplicates differ only by id; numeric dup detection is check's job


@case
def c16_deeply_nested_extra_field():
    deep = {"a": [{"b": {"c": [1] * 200}}]}
    p = _write(_spec(dict(_turns(), meta=deep)))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c17_check_json_structure():
    p = _write(_spec())
    code, out, _ = run_cli(["check", p, "--json"])
    f = json.loads(out)["findings"][0]
    assert set(f) >= {"rule", "severity", "message"}


@case
def c18_id_max_len_64_ok():
    p = _write(_spec({"id": "a" * 64, "type": "max_turns", "value": 3}))
    code, _, _ = run_cli(["validate", p])
    assert code == 0


@case
def c19_id_65_chars_rejected():
    p = _write(_spec({"id": "a" * 65, "type": "max_turns", "value": 3}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R2" in out


@case
def c20_all_ordering_two_identical_values_ok():
    p = _write(_spec(_turns(10), {"id": "turns2", "type": "max_turns", "value": 10}, ordering="all"))
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "U3" not in out


@case
def c21_bool_value_in_no_progress_rejected():
    p = _write(_spec({"id": "s", "type": "no_progress", "window": True}))
    code, out, _ = run_cli(["validate", p])
    assert code == 1 and "R6" in out


@case
def c22_empty_conditions_validate_and_check_both_fail():
    p = _write(_spec())
    c1, _, _ = run_cli(["validate", p])
    c2, out2, _ = run_cli(["check", p])
    assert c1 == 1 and c2 == 1 and "U1" in out2


class T(unittest.TestCase):
    def test_meta_case_count(self):
        self.assertGreaterEqual(len(CASES), 60)


for _fn in CASES:
    setattr(T, "test_" + _fn.__name__, lambda self, f=_fn: f())

if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))
    sys.exit(0 if fails == 0 else 1)
