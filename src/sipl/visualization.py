from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import html
import json
from typing import Any

from lark import Token, Tree

from sipl.ast import ASTNode, Program, SourceSpan
from sipl.parser import SiplParser


@dataclass(frozen=True)
class VisNode:
    """Вузол дерева для експорту в текст, JSON, DOT, SVG або HTML"""
    node_id: str
    label: str
    kind: str  # "rule" | "token" | "ast"
    span: SourceSpan | None = None
    source_fragment: str = ""
    children: tuple[VisNode, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "label": self.label,
            "kind": self.kind,
            "span": self.span.to_dict() if self.span else None,
            "source_fragment": self.source_fragment,
            "children": [c.to_dict() for c in self.children],
        }


def _extract_fragment(source: str, span: SourceSpan | None) -> str:
    if span is None or span.end_pos <= span.start_pos:
        return ""
    frag = source[span.start_pos : span.end_pos].strip()
    if len(frag) > 40:
        return frag[:37] + "..."
    return frag


def build_parse_tree_model(source: str, parser: SiplParser | None = None) -> VisNode:
    """Перетворює дерево розбору Lark у VisNode"""
    sipl_parser = parser or SiplParser()
    cst = sipl_parser.parse_to_cst(source)
    counter = 0

    def walk(node: Tree[Token] | Token) -> VisNode:
        nonlocal counter
        counter += 1
        nid = f"pt_{counter}"

        if isinstance(node, Token):
            line = node.line or 1
            col = node.column or 1
            end_line = node.end_line or line
            end_col = node.end_column or (col + len(node.value))
            s_pos = node.start_pos or 0
            e_pos = node.end_pos or (s_pos + len(node.value))
            span = SourceSpan(line, col, end_line, end_col, s_pos, e_pos)
            return VisNode(
                node_id=nid,
                label=f"{node.type}: {node.value!r}",
                kind="token",
                span=span,
                source_fragment=node.value,
            )

        meta = node.meta
        span: SourceSpan | None = None
        if not getattr(meta, "empty", True):
            span = SourceSpan(
                meta.line,
                meta.column,
                meta.end_line,
                meta.end_column,
                meta.start_pos,
                meta.end_pos,
            )
        rule_name = str(node.data)
        children = tuple(walk(ch) for ch in node.children)
        return VisNode(
            node_id=nid,
            label=rule_name,
            kind="rule",
            span=span,
            source_fragment=_extract_fragment(source, span),
            children=children,
        )

    return walk(cst)


def build_ast_model(program: Program, source: str = "") -> VisNode:
    """Перетворює AST програми у VisNode"""
    counter = 0

    def walk(node: ASTNode) -> VisNode:
        nonlocal counter
        counter += 1
        nid = f"ast_{counter}"
        cls_name = type(node).__name__
        span: SourceSpan | None = getattr(node, "span", None)

        attrs: list[str] = []
        child_nodes: list[VisNode] = []

        if is_dataclass(node):
            for f in fields(node):
                if f.name == "span":
                    continue
                val = getattr(node, f.name)
                if is_dataclass(val):
                    child_nodes.append(walk(val))  # type: ignore[arg-type]
                else:
                    attrs.append(f"{f.name}={val!r}")

        label = f"{cls_name}({', '.join(attrs)})" if attrs else cls_name
        return VisNode(
            node_id=nid,
            label=label,
            kind="ast",
            span=span,
            source_fragment=_extract_fragment(source, span),
            children=tuple(child_nodes),
        )

    return walk(program)


def render_tree_text(root: VisNode) -> str:
    """Рендерить дерево у вигляді ASCII-тексту"""
    lines: list[str] = []

    def walk(node: VisNode, prefix: str, is_last: bool, is_root: bool) -> None:
        span_info = (
            f" [{node.span.start_line}:{node.span.start_col}-{node.span.end_line}:{node.span.end_col}]"
            if node.span
            else ""
        )
        connector = "" if is_root else ("└── " if is_last else "├── ")
        lines.append(f"{prefix}{connector}{node.label}{span_info}")
        next_prefix = "" if is_root else prefix + ("    " if is_last else "│   ")
        for idx, child in enumerate(node.children):
            walk(child, next_prefix, idx == len(node.children) - 1, False)

    walk(root, "", True, True)
    return "\n".join(lines)


def render_tree_json(root: VisNode) -> str:
    """Експортує дерево у JSON"""
    return json.dumps(root.to_dict(), ensure_ascii=False, indent=2)


def render_tree_dot(root: VisNode, graph_name: str = "SIPLTree") -> str:
    """Експортує дерево у формат DOT"""
    lines = [
        f"digraph {graph_name} {{",
        '  node [shape=box, style="rounded,filled", fontname="Consolas", fontsize=10];',
        '  edge [color="#64748b"];',
    ]

    def walk(node: VisNode) -> None:
        fill = "#e0f2fe" if node.kind == "ast" else ("#fef3c7" if node.kind == "token" else "#f1f5f9")
        span_txt = (
            f"\\n[{node.span.start_line}:{node.span.start_col}..{node.span.end_line}:{node.span.end_col}]"
            if node.span
            else ""
        )
        esc_label = (node.label + span_txt).replace('"', '\\"')
        lines.append(f'  {node.node_id} [label="{esc_label}", fillcolor="{fill}"];')
        for child in node.children:
            lines.append(f"  {node.node_id} -> {child.node_id};")
            walk(child)

    walk(root)
    lines.append("}")
    return "\n".join(lines)


def render_tree_svg(root: VisNode) -> str:
    """Генерує SVG-дерево"""
    node_w = 175
    node_h = 44
    h_gap = 18
    v_gap = 72

    positions: dict[str, tuple[float, float]] = {}
    all_nodes: list[VisNode] = []
    next_leaf_x = 20.0
    max_depth = 0

    def layout(node: VisNode, depth: int) -> float:
        nonlocal next_leaf_x, max_depth
        max_depth = max(max_depth, depth)
        all_nodes.append(node)
        y = 20.0 + depth * v_gap
        if not node.children:
            x = next_leaf_x
            next_leaf_x += node_w + h_gap
        else:
            child_xs = [layout(ch, depth + 1) for ch in node.children]
            x = (child_xs[0] + child_xs[-1]) / 2.0
        positions[node.node_id] = (x, y)
        return x

    layout(root, 0)
    total_w = max(320, int(next_leaf_x + 20))
    total_h = max(160, int((max_depth + 1) * v_gap + 30))

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}" style="font-family: Consolas, monospace; background: #ffffff;">'
    ]

    # Ребра
    for node in all_nodes:
        px, py = positions[node.node_id]
        for ch in node.children:
            cx, cy = positions[ch.node_id]
            svg_parts.append(
                f'<line x1="{px + node_w / 2:.1f}" y1="{py + node_h:.1f}" '
                f'x2="{cx + node_w / 2:.1f}" y2="{cy:.1f}" stroke="#94a3b8" stroke-width="1.5"/>'
            )

    # Вузли
    for node in all_nodes:
        x, y = positions[node.node_id]
        fill = "#dbeafe" if node.kind == "ast" else ("#fef3c7" if node.kind == "token" else "#f1f5f9")
        stroke = "#2563eb" if node.kind == "ast" else ("#d97706" if node.kind == "token" else "#475569")
        short_label = node.label if len(node.label) <= 24 else node.label[:21] + "..."
        span_str = (
            f"{node.span.start_line}:{node.span.start_col}-{node.span.end_line}:{node.span.end_col}"
            if node.span
            else ""
        )
        title_text = html.escape(f"{node.label} | span={span_str} | code={node.source_fragment!r}")
        svg_parts.append(
            f'<g><title>{title_text}</title>'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{node_w}" height="{node_h}" rx="6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
            f'<text x="{x + node_w / 2:.1f}" y="{y + 18:.1f}" font-size="11" '
            f'text-anchor="middle" fill="#0f172a">{html.escape(short_label)}</text>'
            f'<text x="{x + node_w / 2:.1f}" y="{y + 34:.1f}" font-size="9.5" '
            f'text-anchor="middle" fill="#475569">{html.escape(span_str)}</text>'
            f"</g>"
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def count_nodes(root: VisNode) -> int:
    return 1 + sum(count_nodes(ch) for ch in root.children)


def render_comparison_html(source: str, parse_tree: VisNode, ast_tree: VisNode) -> str:
    """HTML-подання для порівняння Parse Tree і AST"""
    pt_svg = render_tree_svg(parse_tree)
    ast_svg = render_tree_svg(ast_tree)
    pt_count = count_nodes(parse_tree)
    ast_count = count_nodes(ast_tree)

    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8" />
  <title>SIPL: Parse Tree vs AST</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 20px; background: #f8fafc; color: #000000; }}
    h1 {{ font-size: 20px; margin: 0 0 6px 0; color: #000000; }}
    .meta {{ margin-bottom: 14px; font-size: 14px; color: #64748b; }}
    .meta strong {{ color: #000000; font-weight: 600; }}
    .meta .sep {{ margin: 0 8px; color: #cbd5e1; }}
    pre {{
      background: #ffffff;
      color: #000000;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 12px 14px;
      margin: 0 0 16px 0;
      font-family: Consolas, monospace;
      font-size: 13.5px;
      line-height: 1.45;
      overflow-x: auto;
    }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; }}
    .panel {{ background: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 14px; overflow-x: auto; }}
    .panel h2 {{ font-size: 16px; margin-top: 0; color: #000000; }}
  </style>
</head>
<body>
  <h1>SIPL — Parse Tree vs AST</h1>
  <div class="meta">
    Parse Tree: <strong>{pt_count}</strong><span class="sep">|</span>
    AST: <strong>{ast_count}</strong><span class="sep">|</span>
    Прибрано: <strong>{pt_count - ast_count}</strong>
  </div>
  <pre>{html.escape(source.strip())}</pre>
  <div class="grid">
    <div class="panel">
      <h2>Parse Tree</h2>
      {pt_svg}
    </div>
    <div class="panel">
      <h2>AST</h2>
      {ast_svg}
    </div>
  </div>
</body>
</html>
"""