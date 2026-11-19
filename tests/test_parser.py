from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lark import Lark, Token, Transformer, Tree, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedToken

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

DEFAULT_GRAMMAR_PATH = Path(__file__).resolve().parents[2] / "grammar" / "sipl.lark"


@dataclass
class SiplSyntaxError(Exception):
    """Помилка парсингу SIPL з координатами"""
    message: str
    span: SourceSpan
    snippet: str = ""

    def __str__(self) -> str:
        loc = f"line {self.span.start_line}, col {self.span.start_col}"
        if self.snippet:
            return f"SyntaxError ({loc}): {self.message}\n{self.snippet}"
        return f"SyntaxError ({loc}): {self.message}"


def _span_from_meta(meta: Any) -> SourceSpan:
    if getattr(meta, "empty", True):
        return SourceSpan(1, 1, 1, 1, 0, 0)
    return SourceSpan(
        start_line=meta.line,
        start_col=meta.column,
        end_line=meta.end_line,
        end_col=meta.end_column,
        start_pos=meta.start_pos,
        end_pos=meta.end_pos,
    )


def _span_from_token(tok: Token) -> SourceSpan:
    line = tok.line or 1
    col = tok.column or 1
    end_line = tok.end_line or line
    end_col = tok.end_column or (col + len(tok.value))
    start_pos = tok.start_pos or 0
    end_pos = tok.end_pos or (start_pos + len(tok.value))
    return SourceSpan(line, col, end_line, end_col, start_pos, end_pos)


def _merge_spans(first: SourceSpan, second: SourceSpan) -> SourceSpan:
    return SourceSpan(
        start_line=first.start_line,
        start_col=first.start_col,
        end_line=second.end_line,
        end_col=second.end_col,
        start_pos=first.start_pos,
        end_pos=second.end_pos,
    )


def _format_snippet(source: str, line: int, col: int) -> str:
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        target_line = lines[line - 1]
        pointer = " " * max(0, col - 1) + "^"
        return f"  {line} | {target_line}\n    | {pointer}"
    return ""


def _ast_items(items: list[Any]) -> list[Any]:
    """Відфільтровує службові токени"""
    return [x for x in items if not isinstance(x, Token) or x.type in {"IDENT", "NUMBER", "NOT_OP"}]


class _AstBuilder(Transformer[Token, Program]):
    @v_args(meta=True)
    def start(self, meta: Any, items: list[Any]) -> Program:
        return items[0]

    @v_args(meta=True)
    def program(self, meta: Any, items: list[Any]) -> Program:
        nodes = _ast_items(items)
        return Program(body=nodes[0], span=_span_from_meta(meta))

    @v_args(meta=True)
    def seq_stmt(self, meta: Any, items: list[Any]) -> SeqStmt:
        first, second = _ast_items(items)
        return SeqStmt(first=first, second=second, span=_merge_spans(first.span, second.span))

    @v_args(meta=True)
    def assign_stmt(self, meta: Any, items: list[Any]) -> AssignStmt:
        ident_tok, expr = _ast_items(items)
        span = _merge_spans(_span_from_token(ident_tok), expr.span)
        return AssignStmt(target=str(ident_tok), expr=expr, span=span)

    @v_args(meta=True)
    def if_stmt(self, meta: Any, items: list[Any]) -> IfStmt:
        cond, then_b, else_b = _ast_items(items)
        return IfStmt(cond=cond, then_branch=then_b, else_branch=else_b, span=_span_from_meta(meta))

    @v_args(meta=True)
    def while_stmt(self, meta: Any, items: list[Any]) -> WhileStmt:
        cond, body = _ast_items(items)
        return WhileStmt(cond=cond, body=body, span=_span_from_meta(meta))

    @v_args(meta=True)
    def block_stmt(self, meta: Any, items: list[Any]) -> BlockStmt:
        nodes = _ast_items(items)
        return BlockStmt(body=nodes[0], span=_span_from_meta(meta))

    @v_args(meta=True)
    def skip_stmt(self, meta: Any, items: list[Any]) -> SkipStmt:
        return SkipStmt(span=_span_from_meta(meta))

    @v_args(meta=True)
    def add_expr(self, meta: Any, items: list[Any]) -> BinArithExpr:
        left, right = _ast_items(items)
        return BinArithExpr(op="+", left=left, right=right, span=_merge_spans(left.span, right.span))

    @v_args(meta=True)
    def sub_expr(self, meta: Any, items: list[Any]) -> BinArithExpr:
        left, right = _ast_items(items)
        return BinArithExpr(op="-", left=left, right=right, span=_merge_spans(left.span, right.span))

    @v_args(meta=True)
    def mul_expr(self, meta: Any, items: list[Any]) -> BinArithExpr:
        left, right = _ast_items(items)
        return BinArithExpr(op="*", left=left, right=right, span=_merge_spans(left.span, right.span))

    @v_args(meta=True)
    def factor(self, meta: Any, items: list[Any]) -> AExp:
        return _ast_items(items)[0]

    @v_args(meta=True)
    def num_expr(self, meta: Any, items: list[Any]) -> NumExpr:
        tok: Token = items[0]
        return NumExpr(value=int(tok.value), span=_span_from_token(tok))

    @v_args(meta=True)
    def var_expr(self, meta: Any, items: list[Any]) -> VarExpr:
        tok: Token = items[0]
        return VarExpr(name=str(tok.value), span=_span_from_token(tok))

    @v_args(meta=True)
    def eq_expr(self, meta: Any, items: list[Any]) -> RelExpr:
        left, right = _ast_items(items)
        return RelExpr(op="=", left=left, right=right, span=_merge_spans(left.span, right.span))

    @v_args(meta=True)
    def gt_expr(self, meta: Any, items: list[Any]) -> RelExpr:
        left, right = _ast_items(items)
        return RelExpr(op=">", left=left, right=right, span=_merge_spans(left.span, right.span))

    @v_args(meta=True)
    def or_expr(self, meta: Any, items: list[Any]) -> OrExpr:
        left, right = _ast_items(items)
        return OrExpr(left=left, right=right, span=_merge_spans(left.span, right.span))

    @v_args(meta=True)
    def not_expr(self, meta: Any, items: list[Any]) -> NotExpr:
        op_tok, expr = _ast_items(items)
        return NotExpr(expr=expr, span=_merge_spans(_span_from_token(op_tok), expr.span))

    @v_args(meta=True)
    def bterm(self, meta: Any, items: list[Any]) -> BExp:
        return _ast_items(items)[0]


class SiplParser:
    """Парсер SIPL для побудови Parse Tree і AST"""

    def __init__(self, grammar_path: Path = DEFAULT_GRAMMAR_PATH) -> None:
        grammar_text = grammar_path.read_text(encoding="utf-8")
        self._lark = Lark(
            grammar_text,
            start="start",
            parser="earley",
            propagate_positions=True,
            keep_all_tokens=True,
        )
        self._builder = _AstBuilder()

    def parse_to_cst(self, source: str) -> Tree[Token]:
        """Повертає дерево розбору Lark"""
        try:
            return self._lark.parse(source)
        except UnexpectedToken as exc:
            line = exc.line or 1
            col = exc.column or 1
            expected = ", ".join(sorted(exc.expected)) if exc.expected else "valid token"
            tok_val = exc.token.value if exc.token else "<EOF>"
            msg = f"Unexpected token {tok_val!r}; expected one of: {expected}"
            span = SourceSpan(line, col, line, col + max(1, len(tok_val)))
            raise SiplSyntaxError(msg, span, _format_snippet(source, line, col)) from exc
        except UnexpectedCharacters as exc:
            line = exc.line or 1
            col = exc.column or 1
            msg = f"Unexpected character {exc.char!r}"
            span = SourceSpan(line, col, line, col + 1)
            raise SiplSyntaxError(msg, span, _format_snippet(source, line, col)) from exc
        except UnexpectedEOF as exc:
            lines = source.splitlines()
            line = max(1, len(lines))
            col = len(lines[-1]) + 1 if lines else 1
            msg = "Unexpected end of file while parsing SIPL program"
            span = SourceSpan(line, col, line, col)
            raise SiplSyntaxError(msg, span, _format_snippet(source, line, col)) from exc

    def parse(self, source: str) -> Program:
        """Повертає AST програми SIPL"""
        cst = self.parse_to_cst(source)
        return self._builder.transform(cst)


_DEFAULT_PARSER: SiplParser | None = None


def parse_sipl(source: str) -> Program:
    """Парсить текст SIPL у AST"""
    global _DEFAULT_PARSER
    if _DEFAULT_PARSER is None:
        _DEFAULT_PARSER = SiplParser()
    return _DEFAULT_PARSER.parse(source)