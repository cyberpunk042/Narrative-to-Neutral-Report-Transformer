"""
NNRT CLI — Command-line interface for transformations.
"""

import argparse
import json
import sys
from pathlib import Path

from nnrt import __version__
from nnrt.core.context import TransformRequest
from nnrt.core.engine import Engine, Pipeline, get_engine
from nnrt.ir.serialization import to_json
from nnrt.output.structured import build_structured_output
from nnrt.passes import (
    annotate_context,
    augment_ir,
    build_ir,
    classify_statements,
    evaluate_policy,
    extract_entities,
    extract_events,
    extract_identifiers,
    normalize,
    package,
    render,
    segment,
    tag_spans,
)


def setup_default_pipeline(engine: Engine) -> None:
    """Register the default pipeline."""
    default_pipeline = Pipeline(
        id="default",
        name="Default NNRT Pipeline",
        passes=[
            normalize,
            segment,
            tag_spans,
            annotate_context,     # Sets context (including quotes)
            classify_statements,  # Uses context for classification
            extract_identifiers,
            extract_entities,     # Phase 4: Entity Extraction
            extract_events,       # Phase 4: Event Extraction
            build_ir,
            evaluate_policy,
            augment_ir,
            render,
            package,
        ],
    )
    engine.register_pipeline(default_pipeline)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="nnrt",
        description="Narrative-to-Neutral Report Transformer",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"nnrt {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Transform command
    transform_parser = subparsers.add_parser("transform", help="Transform a narrative")
    transform_parser.add_argument(
        "input",
        type=str,
        help="Input text or path to file (use - for stdin)",
    )
    transform_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    transform_parser.add_argument(
        "--format",
        choices=["text", "json", "ir", "structured"],
        default="text",
        help="Output format: text (default), structured (pre-alpha JSON), json, ir",
    )
    transform_parser.add_argument(
        "--pipeline",
        type=str,
        default="default",
        help="Pipeline to use (default: default)",
    )
    transform_parser.add_argument(
        "--llm",
        action="store_true",
        help="Use LLM-based rendering (requires transformers, slower but more fluent)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "transform":
        return run_transform(args)

    return 0


def run_transform(args: argparse.Namespace) -> int:
    """Run transformation command."""
    # Get input text
    if args.input == "-":
        text = sys.stdin.read()
    elif len(args.input) < 256 and Path(args.input).exists():
        # Only check as path if it's short enough to be a valid path
        text = Path(args.input).read_text()
    else:
        text = args.input

    # Setup engine
    engine = get_engine()
    setup_default_pipeline(engine)

    # Enable LLM rendering if requested
    if args.llm:
        import os
        os.environ["NNRT_USE_LLM"] = "1"

    # Run transformation
    request = TransformRequest(text=text)
    result = engine.transform(request, args.pipeline)

    # Format output
    if args.format == "structured":
        structured = build_structured_output(result, text)
        output = structured.model_dump_json(indent=2)
    elif args.format == "json":
        output = to_json(result)
    elif args.format == "ir":
        output = to_json(result, indent=4)
    else:
        output = result.rendered_text or ""
        if result.diagnostics:
            output += "\n\n--- Diagnostics ---\n"
            for diag in result.diagnostics:
                output += f"[{diag.level.value}] {diag.code}: {diag.message}\n"

    # Write output
    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)

    return 0 if result.status.value in ("success", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
