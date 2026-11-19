from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union


@dataclass(frozen=True)
class SourceSpan:
    """Координати фрагмента коду у вихідному тексті (1-based індексація)"""
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    start_pos: int = 0
    end_pos: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }


# Арифметичні вирази (Aexp)

@dataclass(frozen=True)
class NumExpr:
    value: int
    span: SourceSpan


@dataclass(frozen=True)
class VarExpr:
    name: str
    span: SourceSpan


@dataclass(frozen=True)
class BinArithExpr:
    op: Literal["+", "-", "*"]
    left: AExp
    right: AExp
    span: SourceSpan


AExp = Union[NumExpr, VarExpr, BinArithExpr]


# Булеві вирази (Bexp)

@dataclass(frozen=True)
class RelExpr:
    op: Literal["=", ">"]
    left: AExp
    right: AExp
    span: SourceSpan


@dataclass(frozen=True)
class OrExpr:
    left: BExp
    right: BExp
    span: SourceSpan


@dataclass(frozen=True)
class NotExpr:
    expr: BExp
    span: SourceSpan


BExp = Union[RelExpr, OrExpr, NotExpr]


# Оператори (Stmt)

@dataclass(frozen=True)
class AssignStmt:
    target: str
    expr: AExp
    span: SourceSpan


@dataclass(frozen=True)
class SeqStmt:
    first: Stmt
    second: Stmt
    span: SourceSpan


@dataclass(frozen=True)
class IfStmt:
    cond: BExp
    then_branch: Stmt
    else_branch: Stmt
    span: SourceSpan


@dataclass(frozen=True)
class WhileStmt:
    cond: BExp
    body: Stmt
    span: SourceSpan


@dataclass(frozen=True)
class BlockStmt:
    body: Stmt
    span: SourceSpan


@dataclass(frozen=True)
class SkipStmt:
    span: SourceSpan


Stmt = Union[AssignStmt, SeqStmt, IfStmt, WhileStmt, BlockStmt, SkipStmt]


# Програма (Program)

@dataclass(frozen=True)
class Program:
    body: Stmt
    span: SourceSpan


ASTNode = Union[Program, Stmt, AExp, BExp]