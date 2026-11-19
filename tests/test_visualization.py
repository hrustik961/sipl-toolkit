import json

from sipl.parser import parse_sipl
from sipl.visualization import (
    build_ast_model,
    build_parse_tree_model,
    count_nodes,
    render_comparison_html,
    render_tree_dot,
    render_tree_json,
    render_tree_svg,
    render_tree_text,
)


def test_parse_tree_and_ast_exporters() -> None:
    code = "begin X := 1 + 2 end"
    pt = build_parse_tree_model(code)
    ast = build_ast_model(parse_sipl(code), code)

    # Parse Tree має більше вузлів через токени begin/end/:=/+
    assert count_nodes(pt) > count_nodes(ast)

    # Text export
    pt_text = render_tree_text(pt)
    ast_text = render_tree_text(ast)
    assert "program" in pt_text
    assert "AssignStmt(target='X')" in ast_text

    # JSON export
    pt_data = json.loads(render_tree_json(pt))
    assert pt_data["kind"] == "rule"
    assert pt_data["span"]["start_line"] == 1

    # DOT & SVG export
    dot_out = render_tree_dot(ast, "TestAST")
    assert "digraph TestAST" in dot_out
    svg_out = render_tree_svg(ast)
    assert svg_out.startswith("<svg")
    assert "AssignStmt" in svg_out


def test_comparison_html_contains_both_trees() -> None:
    code = "begin if X > 0 then Y := 1 else Y := 2 end"
    pt = build_parse_tree_model(code)
    ast = build_ast_model(parse_sipl(code), code)
    html_doc = render_comparison_html(code, pt, ast)

    assert "Parse Tree vs AST" in html_doc
    assert html_doc.count("<svg") == 2
    assert "IfStmt" in html_doc