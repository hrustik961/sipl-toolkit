from pathlib import Path
import pytest
from lark import Lark, LarkError

GRAMMAR_PATH = Path(__file__).resolve().parent.parent / "grammar" / "sipl.lark"


@pytest.fixture(scope="module")
def parser() -> Lark:
    return Lark(GRAMMAR_PATH.read_text(encoding="utf-8"), start="start", parser="earley")


POSITIVE_PROGRAMS = [
    # 1. Оператор skip
    "begin skip end",
    # 2. Просте присвоювання
    "begin X := 5 end",
    # 3. Від'ємні числа та вирази
    "begin X := -10 + 3 * (Y - 2) end",
    # 4. Послідовність операторів
    "begin X := 1; Y := 2; Z := X + Y end",
    # 5. Вкладений блок begin/end
    "begin begin X := 1 end; skip end",
    # 6. Умовний оператор if-then-else
    "begin if X > 0 then Y := 1 else Y := -1 end",
    # 7. Рівність у булевому виразі
    "begin if X = Y then Z := 0 else Z := 1 end",
    # 8. Диз'юнкція та заперечення (ASCII та Unicode)
    "begin if not (X = 0) or X > 10 then Y := 1 else Y := 0 end",
    "begin if ¬(X = 0) ∨ X > 10 then Y := 1 else Y := 0 end",
    # 9. Цикл while
    "begin while X > 0 do X := X - 1 end",
    # 10. Піднесення до степеня
    """
    begin
        R := 1;
        while Y > 0 do
        begin
            R := R * X;
            Y := Y - 1
        end
    end
    """,
]

NEGATIVE_PROGRAMS = [
    # 1. Порожній рядок
    "",
    # 2. Немає begin/end на верхньому рівні
    "X := 1",
    # 3. Незакритий блок begin
    "begin X := 1",
    # 4. Порожній блок begin end
    "begin end",
    # 5. Зайва крапка з комою перед end
    "begin X := 1; end",
    # 6. Неправильний оператор присвоювання (= замість :=)
    "begin X = 1 end",
    # 7. Неповний if без else
    "begin if X > 0 then Y := 1 end",
    # 8. Цикл while без do
    "begin while X > 0 X := X - 1 end",
    # 9. Незакрита дужка у виразі
    "begin X := (1 + 2 * 3 end",
    # 10. Арифметичний вираз замість умови в if
    "begin if X + 1 then Y := 2 else Y := 3 end",
    # 11. Присвоювання числу
    "begin 5 := X end",
]


@pytest.mark.parametrize("code", POSITIVE_PROGRAMS)
def test_valid_sipl_programs(parser: Lark, code: str) -> None:
    tree = parser.parse(code)
    assert tree is not None


@pytest.mark.parametrize("code", NEGATIVE_PROGRAMS)
def test_invalid_sipl_programs(parser: Lark, code: str) -> None:
    with pytest.raises(LarkError):
        parser.parse(code)