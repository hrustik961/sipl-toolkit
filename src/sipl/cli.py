from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from sipl import __version__
from sipl.interpreter import SiplRuntimeError, execute_sipl
from sipl.parser import SiplSyntaxError, parse_sipl
from sipl.semantics import build_semantic_term
from sipl.visualization import (
    build_ast_model,
    build_parse_tree_model,
    render_comparison_html,
    render_tree_dot,
    render_tree_json,
    render_tree_svg,
    render_tree_text,
)


def _parse_state_assignments(pairs: list[str]) -> dict[str, int]:
    state: dict[str, int] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Invalid variable assignment {item!r}; expected VAR=INT")
        name, raw_val = item.split("=", 1)
        name = name.strip()
        if not name.isidentifier():
            raise ValueError(f"Invalid SIPL variable name: {name!r}")
        state[name] = int(raw_val.strip())
    return state


def _emit(payload: dict[str, Any], human_text: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(human_text)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sipl",
        description="SIPL CLI: syntax check, AST, interpreter, semantics and visualization",
    )
    parser.add_argument("--version", action="version", version=f"sipl-toolkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="Check syntax of a .sipl file")
    p_check.add_argument("file", type=Path, help="Path to .sipl file")
    p_check.add_argument("--json", action="store_true", help="Output JSON")

    # parse
    p_parse = sub.add_parser("parse", help="Parse .sipl file into AST")
    p_parse.add_argument("file", type=Path, help="Path to .sipl file")
    p_parse.add_argument("--json", action="store_true", help="Output JSON")

    # run
    p_run = sub.add_parser("run", help="Run a .sipl program")
    p_run.add_argument("file", type=Path, help="Path to .sipl file")
    p_run.add_argument(
        "-s",
        "--state",
        nargs="*",
        default=[],
        metavar="VAR=INT",
        help="Initial variables, e.g. -s X=3 Y=4",
    )
    p_run.add_argument("--max-steps", type=int, default=10_000, help="Max execution steps")
    p_run.add_argument("--json", action="store_true", help="Output JSON")

    # sem
    p_sem = sub.add_parser("sem", help="Build semantic term for a .sipl program")
    p_sem.add_argument("file", type=Path, help="Path to .sipl file")
    p_sem.add_argument("--latex", action="store_true", help="Output in LaTeX")
    p_sem.add_argument("--steps", action="store_true", help="Show derivation steps")
    p_sem.add_argument("--json", action="store_true", help="Output JSON")

    # viz
    p_viz = sub.add_parser("viz", help="Visualize tree (text, json, dot, svg, html)")
    p_viz.add_argument("file", type=Path, help="Path to .sipl file")
    p_viz.add_argument(
        "--tree",
        choices=["ast", "parse", "compare"],
        default="ast",
        help="Tree type (default: ast)",
    )
    p_viz.add_argument(
        "--format",
        choices=["text", "json", "dot", "svg", "html"],
        default="text",
        help="Output format",
    )
    p_viz.add_argument("-o", "--out", type=Path, default=None, help="Output file path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    file_path: Path = args.file
    if not file_path.is_file():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        return 2

    source = file_path.read_text(encoding="utf-8")

    try:
        if args.command == "check":
            prog = parse_sipl(source)
            payload = {"status": "ok", "file": str(file_path), "span": prog.span.to_dict()}
            _emit(payload, f"OK: {file_path}", args.json)
            return 0

        if args.command == "parse":
            prog = parse_sipl(source)
            ast_vis = build_ast_model(prog, source)
            payload = {"status": "ok", "file": str(file_path), "ast": ast_vis.to_dict()}
            _emit(payload, render_tree_text(ast_vis), args.json)
            return 0

        if args.command == "run":
            init_state = _parse_state_assignments(args.state)
            prog = parse_sipl(source)
            res = execute_sipl(prog, initial_state=init_state, max_steps=args.max_steps)
            payload = {
                "status": "ok",
                "initial_state": init_state,
                "final_state": res.final_state,
                "steps": res.steps,
            }
            human = f"State ({res.steps} steps): {res.final_state}"
            _emit(payload, human, args.json)
            return 0

        if args.command == "sem":
            prog = parse_sipl(source)
            sem_res = build_semantic_term(prog)
            payload = {
                "status": "ok",
                "semantic_term": sem_res.text,
                "latex": sem_res.latex,
                "steps": [
                    {"rule": s.rule, "construct": s.source_construct, "result": s.result_term}
                    for s in sem_res.steps
                ],
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(sem_res.latex if args.latex else sem_res.text)
                if args.steps:
                    print("\nSteps:")
                    for idx, step in enumerate(sem_res.steps, 1):
                        print(f"  {idx}. [{step.rule}] {step.source_construct} ==> {step.result_term}")
            return 0

        if args.command == "viz":
            prog = parse_sipl(source)
            pt_vis = build_parse_tree_model(source)
            ast_vis = build_ast_model(prog, source)

            if args.tree == "compare" or args.format == "html":
                output = render_comparison_html(source, pt_vis, ast_vis)
            else:
                target = ast_vis if args.tree == "ast" else pt_vis
                if args.format == "text":
                    output = render_tree_text(target)
                elif args.format == "json":
                    output = render_tree_json(target)
                elif args.format == "dot":
                    output = render_tree_dot(target)
                elif args.format == "svg":
                    output = render_tree_svg(target)
                else:
                    output = render_tree_text(target)

            if args.out:
                args.out.write_text(output, encoding="utf-8")
                print(f"Saved to {args.out}")
            else:
                print(output)
            return 0

    except SiplSyntaxError as exc:
        if getattr(args, "json", False):
            print(
                json.dumps(
                    {"status": "syntax_error", "message": exc.message, "span": exc.span.to_dict()},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(str(exc), file=sys.stderr)
        return 1
    except (SiplRuntimeError, ValueError) as exc:
        if getattr(args, "json", False):
            span_data = exc.span.to_dict() if isinstance(exc, SiplRuntimeError) and exc.span else None
            print(
                json.dumps(
                    {"status": "runtime_error", "message": str(exc), "span": span_data},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())