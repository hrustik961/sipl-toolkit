from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

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
    SourceSpan,
    Stmt,
    VarExpr,
    WhileStmt,
)

State = dict[str, int]


@dataclass
class SiplRuntimeError(Exception):
    """Помилка виконання програми"""
    message: str
    span: SourceSpan | None = None

    def __str__(self) -> str:
        if self.span:
            return f"RuntimeError (line {self.span.start_line}, col {self.span.start_col}): {self.message}"
        return f"RuntimeError: {self.message}"


class UndefinedVariableError(SiplRuntimeError):
    """Звернення до змінної, якої немає в поточному стані"""


class StepLimitExceededError(SiplRuntimeError):
    """Перевищено ліміт кроків виконання"""


@dataclass(frozen=True)
class ExecutionResult:
    """Результат виконання програми"""
    final_state: State
    steps: int


class SiplInterpreter:
    """Інтерпретатор програм"""

    def __init__(self, max_steps: int = 10_000) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps = max_steps
        self._steps = 0

    def run(self, program: Program, initial_state: Mapping[str, int] | None = None) -> ExecutionResult:
        """Виконує AST програми на початковому стані"""
        self._steps = 0
        state: State = dict(initial_state) if initial_state is not None else {}
        final_state = self._exec_stmt(program.body, state)
        return ExecutionResult(final_state=final_state, steps=self._steps)

    def _tick(self, span: SourceSpan) -> None:
        self._steps += 1
        if self._steps > self.max_steps:
            raise StepLimitExceededError(
                f"Execution exceeded maximum step limit ({self.max_steps}); possible infinite loop",
                span=span,
            )

    def _eval_aexp(self, expr: AExp, state: State) -> int:
        if isinstance(expr, NumExpr):
            return expr.value
        if isinstance(expr, VarExpr):
            if expr.name not in state:
                raise UndefinedVariableError(
                    f"Variable {expr.name!r} is undefined in current state",
                    span=expr.span,
                )
            return state[expr.name]
        if isinstance(expr, BinArithExpr):
            left_val = self._eval_aexp(expr.left, state)
            right_val = self._eval_aexp(expr.right, state)
            if expr.op == "+":
                return left_val + right_val
            if expr.op == "-":
                return left_val - right_val
            if expr.op == "*":
                return left_val * right_val
        raise TypeError(f"Unsupported arithmetic expression node: {expr!r}")

    def _eval_bexp(self, expr: BExp, state: State) -> bool:
        if isinstance(expr, RelExpr):
            left_val = self._eval_aexp(expr.left, state)
            right_val = self._eval_aexp(expr.right, state)
            if expr.op == "=":
                return left_val == right_val
            if expr.op == ">":
                return left_val > right_val
        if isinstance(expr, OrExpr):
            # Обчислюємо обидва підвирази
            left_bool = self._eval_bexp(expr.left, state)
            right_bool = self._eval_bexp(expr.right, state)
            return left_bool or right_bool
        if isinstance(expr, NotExpr):
            return not self._eval_bexp(expr.expr, state)
        raise TypeError(f"Unsupported boolean expression node: {expr!r}")

    def _exec_stmt(self, stmt: Stmt, state: State) -> State:
        if isinstance(stmt, SkipStmt):
            self._tick(stmt.span)
            return dict(state)

        if isinstance(stmt, AssignStmt):
            self._tick(stmt.span)
            val = self._eval_aexp(stmt.expr, state)
            new_state = dict(state)
            new_state[stmt.target] = val
            return new_state

        if isinstance(stmt, SeqStmt):
            mid_state = self._exec_stmt(stmt.first, state)
            return self._exec_stmt(stmt.second, mid_state)

        if isinstance(stmt, BlockStmt):
            return self._exec_stmt(stmt.body, state)

        if isinstance(stmt, IfStmt):
            self._tick(stmt.span)
            cond_val = self._eval_bexp(stmt.cond, state)
            branch = stmt.then_branch if cond_val else stmt.else_branch
            return self._exec_stmt(branch, state)

        if isinstance(stmt, WhileStmt):
            current = dict(state)
            while True:
                self._tick(stmt.span)
                if not self._eval_bexp(stmt.cond, current):
                    break
                current = self._exec_stmt(stmt.body, current)
            return current

        raise TypeError(f"Unsupported statement node: {stmt!r}")


def execute_sipl(
    program: Program,
    initial_state: Mapping[str, int] | None = None,
    max_steps: int = 10_000,
) -> ExecutionResult:
    """Запускає AST програми"""
    return SiplInterpreter(max_steps=max_steps).run(program, initial_state)