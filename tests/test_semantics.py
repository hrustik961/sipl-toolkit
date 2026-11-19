from pathlib import Path

from sipl.parser import parse_sipl
from sipl.semantics import build_semantic_term

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_golden_power_semantic_term() -> None:
    """Перевіряє точний семантичний терм програми R := X^Y"""
    prog = parse_sipl((EXAMPLES_DIR / "power.sipl").read_text(encoding="utf-8"))
    res = build_semantic_term(prog)

    expected_text = (
        "AS^R(1̄) · WH(S^2(gr, Y⇒, 0̄), "
        "AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1̄)))"
    )
    assert res.text == expected_text
    assert r"\overline{1}" in res.latex
    assert r"WH(S^2(gr, Y\Rightarrow, \overline{0})" in res.latex

    rules = [step.rule for step in res.steps]
    assert "NS_Stm_As" in rules
    assert "NS_Stm_Wh" in rules
    assert "NS_Stm_Seq" in rules
    assert rules[-1] == "NS_Prog"


def test_golden_gcd_semantic_term() -> None:
    """Перевіряє семантичний терм алгоритму Евкліда з not, =, >, if-then-else"""
    prog = parse_sipl((EXAMPLES_DIR / "gcd.sipl").read_text(encoding="utf-8"))
    res = build_semantic_term(prog)

    expected_text = (
        "WH(S^1(neg, S^2(eq, X⇒, Y⇒)), "
        "IF(S^2(gr, X⇒, Y⇒), AS^X(S^2(sub, X⇒, Y⇒)), AS^Y(S^2(sub, Y⇒, X⇒))))"
    )
    assert res.text == expected_text


def test_golden_skip_and_or_operators() -> None:
    prog = parse_sipl("begin if X = 0 or Y > 1 then skip else Z := X + 2 end")
    res = build_semantic_term(prog)

    expected_text = (
        "IF(S^2(or, S^2(eq, X⇒, 0̄), S^2(gr, Y⇒, 1̄)), "
        "id, AS^Z(S^2(add, X⇒, 2̄)))"
    )
    assert res.text == expected_text
    assert res.term.to_dict()["kind"] == "IF"