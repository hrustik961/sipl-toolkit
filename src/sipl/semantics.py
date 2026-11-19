from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sipl.ast import (
    AExp,
    AssignStmt,
    BExp,
    BinArithExpr,
    BlockStmt,
    IfStmt,
    NotExpr,
    NumExpr,
    OrExpr,
    Program,
    RelExpr,
    SeqStmt,
    SkipStmt,
    Stmt,
    VarExpr,
    WhileStmt,
)

_ARITH_OP_NAMES: dict[str, str] = {
    "+": "add",
    "-": "sub",
    "*": "mult",
}

_REL_OP_NAMES: dict[str, str] = {
    "=": "eq",
    ">": "gr",
}


@dataclass(frozen=True)
class DerivationStep:
    """Один крок виведення семантичного терму"""
    rule: str
    source_construct: str
    result_term: str


@dataclass(frozen=True)
class SemanticTerm:
    """Вузол семантичного терму."""
    kind: str
    args: tuple[Any, ...] = ()

    def to_text(self) -> str:
        """Рендерить семантичний терм у текстовій формі (Unicode)"""
        if self.kind == "const":
            val: int = self.args[0]
            return f"{val}\u0304"  # наприклад: 1̄, 0̄
        if self.kind == "var":
            name: str = self.args[0]
            return f"{name}⇒"
        if self.kind == "id":
            return "id"
        if self.kind == "AS":
            var_name, expr_term = self.args
            return f"AS^{var_name}({expr_term.to_text()})"
        if self.kind == "SEQ":
            left_term, right_term = self.args
            return f"{left_term.to_text()} · {right_term.to_text()}"
        if self.kind == "IF":
            cond_term, then_term, else_term = self.args
            return f"IF({cond_term.to_text()}, {then_term.to_text()}, {else_term.to_text()})"
        if self.kind == "WH":
            cond_term, body_term = self.args
            return f"WH({cond_term.to_text()}, {body_term.to_text()})"
        if self.kind == "S1":
            fn_name, arg1 = self.args
            return f"S^1({fn_name}, {arg1.to_text()})"
        if self.kind == "S2":
            fn_name, arg1, arg2 = self.args
            return f"S^2({fn_name}, {arg1.to_text()}, {arg2.to_text()})"
        raise ValueError(f"Unknown SemanticTerm kind: {self.kind}")

    def to_latex(self) -> str:
        """Рендерить семантичний терм у нотації LaTeX"""
        if self.kind == "const":
            return rf"\overline{{{self.args[0]}}}"
        if self.kind == "var":
            return rf"{self.args[0]}\Rightarrow"
        if self.kind == "id":
            return r"\mathrm{id}"
        if self.kind == "AS":
            var_name, expr_term = self.args
            return rf"AS^{{{var_name}}}({expr_term.to_latex()})"
        if self.kind == "SEQ":
            left_term, right_term = self.args
            return rf"{left_term.to_latex()} \cdot {right_term.to_latex()}"
        if self.kind == "IF":
            cond_term, then_term, else_term = self.args
            return rf"IF({cond_term.to_latex()}, {then_term.to_latex()}, {else_term.to_latex()})"
        if self.kind == "WH":
            cond_term, body_term = self.args
            return rf"WH({cond_term.to_latex()}, {body_term.to_latex()})"
        if self.kind == "S1":
            fn_name, arg1 = self.args
            return rf"S^1({fn_name}, {arg1.to_latex()})"
        if self.kind == "S2":
            fn_name, arg1, arg2 = self.args
            return rf"S^2({fn_name}, {arg1.to_latex()}, {arg2.to_latex()})"
        raise ValueError(f"Unknown SemanticTerm kind: {self.kind}")

    def to_dict(self) -> dict[str, Any]:
        serialized_args: list[Any] = [
            arg.to_dict() if isinstance(arg, SemanticTerm) else arg for arg in self.args
        ]
        return {
            "kind": self.kind,
            "text": self.to_text(),
            "args": serialized_args,
        }


@dataclass
class SemanticBuildResult:
    """Результат побудови семантичного терму"""
    term: SemanticTerm
    steps: list[DerivationStep] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.term.to_text()

    @property
    def latex(self) -> str:
        return self.term.to_latex()


class SemanticTermBuilder:
    """Побудова семантичного терму з AST програми"""

    def __init__(self) -> None:
        self._steps: list[DerivationStep] = []

    def build(self, program: Program) -> SemanticBuildResult:
        self._steps = []
        term = self._sem_s(program.body)
        self._steps.append(
            DerivationStep(
                rule="NS_Prog",
                source_construct="begin S end",
                result_term=term.to_text(),
            )
        )
        return SemanticBuildResult(term=term, steps=list(self._steps))

    def _sem_a(self, expr: AExp) -> SemanticTerm:
        if isinstance(expr, NumExpr):
            term = SemanticTerm("const", (expr.value,))
            self._steps.append(DerivationStep("NS_A_Num", str(expr.value), term.to_text()))
            return term

        if isinstance(expr, VarExpr):
            term = SemanticTerm("var", (expr.name,))
            self._steps.append(DerivationStep("NS_A_Var", expr.name, term.to_text()))
            return term

        if isinstance(expr, BinArithExpr):
            fn_name = _ARITH_OP_NAMES[expr.op]
            rule_name = f"NS_A_{fn_name.capitalize()}"
            left_t = self._sem_a(expr.left)
            right_t = self._sem_a(expr.right)
            term = SemanticTerm("S2", (fn_name, left_t, right_t))
            self._steps.append(DerivationStep(rule_name, f"a1 {expr.op} a2", term.to_text()))
            return term

        raise TypeError(f"Unsupported AExp node: {expr!r}")

    def _sem_b(self, expr: BExp) -> SemanticTerm:
        if isinstance(expr, RelExpr):
            fn_name = _REL_OP_NAMES[expr.op]
            left_t = self._sem_a(expr.left)
            right_t = self._sem_a(expr.right)
            term = SemanticTerm("S2", (fn_name, left_t, right_t))
            self._steps.append(DerivationStep(f"NS_B_{fn_name}", f"a1 {expr.op} a2", term.to_text()))
            return term

        if isinstance(expr, OrExpr):
            left_t = self._sem_b(expr.left)
            right_t = self._sem_b(expr.right)
            term = SemanticTerm("S2", ("or", left_t, right_t))
            self._steps.append(DerivationStep("NS_B_or", "b1 ∨ b2", term.to_text()))
            return term

        if isinstance(expr, NotExpr):
            inner_t = self._sem_b(expr.expr)
            term = SemanticTerm("S1", ("neg", inner_t))
            self._steps.append(DerivationStep("NS_B_neg", "¬b", term.to_text()))
            return term

        raise TypeError(f"Unsupported BExp node: {expr!r}")

    def _sem_s(self, stmt: Stmt) -> SemanticTerm:
        if isinstance(stmt, SkipStmt):
            term = SemanticTerm("id")
            self._steps.append(DerivationStep("NS_Stm_Skip", "skip", term.to_text()))
            return term

        if isinstance(stmt, AssignStmt):
            expr_t = self._sem_a(stmt.expr)
            term = SemanticTerm("AS", (stmt.target, expr_t))
            self._steps.append(DerivationStep("NS_Stm_As", f"{stmt.target} := a", term.to_text()))
            return term

        if isinstance(stmt, SeqStmt):
            first_t = self._sem_s(stmt.first)
            second_t = self._sem_s(stmt.second)
            term = SemanticTerm("SEQ", (first_t, second_t))
            self._steps.append(DerivationStep("NS_Stm_Seq", "S1 ; S2", term.to_text()))
            return term

        if isinstance(stmt, BlockStmt):
            inner_t = self._sem_s(stmt.body)
            self._steps.append(DerivationStep("NS_Stm_BE", "begin S end", inner_t.to_text()))
            return inner_t

        if isinstance(stmt, IfStmt):
            cond_t = self._sem_b(stmt.cond)
            then_t = self._sem_s(stmt.then_branch)
            else_t = self._sem_s(stmt.else_branch)
            term = SemanticTerm("IF", (cond_t, then_t, else_t))
            self._steps.append(DerivationStep("NS_Stm_If", "if b then S1 else S2", term.to_text()))
            return term

        if isinstance(stmt, WhileStmt):
            cond_t = self._sem_b(stmt.cond)
            body_t = self._sem_s(stmt.body)
            term = SemanticTerm("WH", (cond_t, body_t))
            self._steps.append(DerivationStep("NS_Stm_Wh", "while b do S", term.to_text()))
            return term

        raise TypeError(f"Unsupported Stmt node: {stmt!r}")


def build_semantic_term(program: Program) -> SemanticBuildResult:
    """Будує семантичний терм програми та кроки виведення"""
    return SemanticTermBuilder().build(program)