from pathlib import Path
import pytest

from sipl.interpreter import (
    SiplInterpreter,
    StepLimitExceededError,
    UndefinedVariableError,
    execute_sipl,
)
from sipl.parser import parse_sipl

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_skip_preserves_state() -> None:
    prog = parse_sipl("begin skip end")
    res = execute_sipl(prog, {"X": 7})
    assert res.final_state == {"X": 7}
    assert res.steps == 1


def test_assignment_and_arithmetic() -> None:
    prog = parse_sipl("begin A := 10; B := A * 2 - 5; C := B + 1 end")
    res = execute_sipl(prog)
    assert res.final_state == {"A": 10, "B": 15, "C": 16}


def test_if_then_else_branches() -> None:
    code = """
    begin
        if X > Y or X = Y then
            MAX := X
        else
            MAX := Y
    end
    """
    prog = parse_sipl(code)
    assert execute_sipl(prog, {"X": 10, "Y": 4}).final_state["MAX"] == 10
    assert execute_sipl(prog, {"X": 5, "Y": 5}).final_state["MAX"] == 5
    assert execute_sipl(prog, {"X": 2, "Y": 9}).final_state["MAX"] == 9


def test_example_power() -> None:
    prog = parse_sipl((EXAMPLES_DIR / "power.sipl").read_text(encoding="utf-8"))
    res = execute_sipl(prog, {"X": 3, "Y": 4})
    assert res.final_state["R"] == 81
    assert res.final_state["Y"] == 0


def test_example_gcd() -> None:
    prog = parse_sipl((EXAMPLES_DIR / "gcd.sipl").read_text(encoding="utf-8"))
    res = execute_sipl(prog, {"X": 48, "Y": 18})
    assert res.final_state["X"] == 6
    assert res.final_state["Y"] == 6


def test_example_factorial() -> None:
    prog = parse_sipl((EXAMPLES_DIR / "fact.sipl").read_text(encoding="utf-8"))
    res = execute_sipl(prog, {"N": 5})
    assert res.final_state["F"] == 120


def test_undefined_variable_raises_with_span() -> None:
    prog = parse_sipl("begin\n    X := UNKNOWN + 1\nend")
    with pytest.raises(UndefinedVariableError) as exc_info:
        execute_sipl(prog)
    err = exc_info.value
    assert err.span is not None
    assert err.span.start_line == 2
    assert "UNKNOWN" in str(err)


def test_infinite_loop_protection() -> None:
    prog = parse_sipl("begin while 1 = 1 do skip end")
    with pytest.raises(StepLimitExceededError) as exc_info:
        execute_sipl(prog, max_steps=50)
    assert "50" in str(exc_info.value)


def test_invalid_max_steps() -> None:
    with pytest.raises(ValueError):
        SiplInterpreter(max_steps=0)