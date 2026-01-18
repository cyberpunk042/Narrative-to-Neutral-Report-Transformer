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
    classify_atomic,
    classify_statements,
    decompose,
    evaluate_policy,
    extract_entities,
    extract_events,
    extract_identifiers,
    link_provenance,
    normalize,
    package,
    render,
    segment,
    tag_spans,
)
from nnrt.passes.p42_coreference import resolve_coreference
from nnrt.passes.p43_resolve_actors import resolve_actors
from nnrt.passes.p44_timeline_v6 import build_enhanced_timeline as build_timeline
from nnrt.passes.p46_group_statements import group_statements
from nnrt.passes.p48_classify_evidence import classify_evidence
from nnrt.passes.p27_epistemic_tag import tag_epistemic
from nnrt.passes.p27b_attribute_statements import attribute_statements
from nnrt.passes.p72_safety_scrub import safety_scrub


def setup_default_pipeline(engine: Engine, profile: str = "law_enforcement") -> None:
    """Register the default pipeline with specified profile."""
    from nnrt.passes import cleanup_punctuation
    from nnrt.policy.loader import clear_cache
    from nnrt.policy.engine import set_default_profile
    
    # Clear cache and set profile for policy engine
    clear_cache()
    set_default_profile(profile)
    
    default_pipeline = Pipeline(
        id="default",
        name="Default NNRT Pipeline",
        passes=[
            normalize,
            segment,
            tag_spans,
            annotate_context,     # Sets context (including quotes)
            classify_statements,  # Uses context for classification
            decompose,            # NEW: Decompose into atomic statements
            tag_epistemic,        # V4 ALPHA: Tag epistemic metadata
            attribute_statements, # V4 ALPHA: Transform/aberrate dangerous content
            classify_atomic,      # NEW: Classify atomic statements
            link_provenance,      # NEW: Link interpretations to sources
            extract_identifiers,
            extract_entities,     # Phase 4: Entity Extraction
            extract_events,       # Phase 4: Event Extraction
            build_ir,
            resolve_coreference,  # v3: Link pronouns to entities (for chains)
            resolve_actors,       # V5: Replace pronouns with entity names
            build_timeline,       # v3: Order events temporally
            group_statements,     # v3: Cluster related statements
            classify_evidence,    # v3: Classify evidence types
            evaluate_policy,
            augment_ir,
            render,
            safety_scrub,         # V4 ALPHA: Final safety scrub of rendered text
            cleanup_punctuation,  # Fix punctuation artifacts
            package,
        ],
    )
    engine.register_pipeline(default_pipeline)


def setup_raw_pipeline(engine: Engine, profile: str = "law_enforcement") -> None:
    """
    Register a RAW pipeline - the original v1 pipeline.
    
    This is the simple/fast neutralization WITHOUT the v2 safety measures:
    - NO atomic decomposition
    - NO statement classification
    - NO provenance linking
    - NO entity/event extraction
    
    Just basic neutralization: normalize → segment → policy → render
    
    Use this for:
    - Fast processing when structured analysis isn't needed
    - Comparing v1 vs v2 output
    - Legacy compatibility
    """
    from nnrt.passes import cleanup_punctuation
    from nnrt.passes import extract_identifiers
    from nnrt.policy.loader import clear_cache
    from nnrt.policy.engine import set_default_profile
    
    clear_cache()
    set_default_profile(profile)
    
    raw_pipeline = Pipeline(
        id="raw",
        name="Raw NNRT Pipeline (v1 Simple)",
        passes=[
            normalize,
            segment,
            tag_spans,
            annotate_context,
            classify_statements,
            extract_identifiers,    # YES - extract dates, locations, badges, etc.
            # NO decompose, classify_atomic, link_provenance
            # NO extract_entities, extract_events
            build_ir,
            evaluate_policy,
            augment_ir,
            render,                # YES - render neutral output
            cleanup_punctuation,   # YES - fix punctuation
            package,               # YES - package output
        ],
    )
    engine.register_pipeline(raw_pipeline)


def setup_structured_only_pipeline(engine: Engine, profile: str = "law_enforcement") -> None:
    """
    Register the structured pipeline - full v2 with all safety measures.
    
    Identical to default pipeline (full decomposition, classification, etc.)
    The difference is the OUTPUT FORMAT: structured document style instead of prose.
    
    Both produce:
    - rendered_text (neutral prose)
    - atomic_statements
    - entities, events
    - identifiers
    - diagnostics
    
    The UI formats the Neutral Output panel as an "official document" with
    bullet points and sections rather than flowing prose.
    """
    from nnrt.passes import cleanup_punctuation, safety_scrub
    from nnrt.policy.loader import clear_cache
    from nnrt.policy.engine import set_default_profile
    
    clear_cache()
    set_default_profile(profile)
    
    structured_pipeline = Pipeline(
        id="structured_only",
        name="Structured Pipeline (v2 Full)",
        passes=[
            normalize,
            segment,
            tag_spans,
            annotate_context,
            classify_statements,
            decompose,
            tag_epistemic,         # V4: Set epistemic_type for observation split
            classify_atomic,
            link_provenance,
            extract_identifiers,
            extract_entities,
            extract_events,
            build_ir,
            resolve_coreference,   # V5: Link pronouns to entities (for chains)
            resolve_actors,        # V5: Replace pronouns with entity names
            build_timeline,        # V6: Enhanced timeline with gap detection
            group_statements,      # V5: Semantic grouping
            classify_evidence,     # V5: Evidence classification
            evaluate_policy,
            augment_ir,
            render,                # YES - render neutral output
            safety_scrub,          # V7: Article agreement + cleanup
            cleanup_punctuation,   # YES - fix punctuation
            package,               # YES - package output
        ],
    )
    engine.register_pipeline(structured_pipeline)


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
    transform_parser.add_argument(
        "--profile",
        type=str,
        default="law_enforcement",
        choices=["standard", "law_enforcement", "base"],
        help="Policy profile to use (default: law_enforcement)",
    )
    transform_parser.add_argument(
        "--raw",
        action="store_true",
        help="[DEBUG] Skip rendering, output raw decomposed IR. Shows what pipeline extracts before rewriting.",
    )
    transform_parser.add_argument(
        "--no-prose",
        action="store_true",
        help="Skip prose rendering, output structured data only (faster).",
    )
    
    # Logging configuration
    transform_parser.add_argument(
        "--log-level",
        type=str,
        choices=["silent", "info", "verbose", "debug"],
        default=None,
        help="Log verbosity level (default: info, or NNRT_LOG_LEVEL env var)",
    )
    transform_parser.add_argument(
        "--log-channel",
        type=str,
        default=None,
        help="Comma-separated log channels to show (pipeline,transform,extract,policy,render,system). Default: all",
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
    # Configure logging first
    from nnrt.core.logging import configure_logging, LogLevel, LogChannel
    
    log_level = getattr(args, 'log_level', None)
    log_channel = getattr(args, 'log_channel', None)
    
    channels = None
    if log_channel:
        channels = [ch.strip() for ch in log_channel.split(",")]
    
    configure_logging(
        level=log_level,
        channels=channels,
        force=True,
    )
    
    # Get input text
    if args.input == "-":
        text = sys.stdin.read()
    elif len(args.input) < 256 and Path(args.input).exists():
        # Only check as path if it's short enough to be a valid path
        text = Path(args.input).read_text()
    else:
        text = args.input

    # Setup engine with selected profile
    engine = get_engine()
    profile = getattr(args, 'profile', 'law_enforcement')
    
    # Choose pipeline based on flags
    use_raw = getattr(args, 'raw', False)
    no_prose = getattr(args, 'no_prose', False)
    
    if use_raw:
        setup_raw_pipeline(engine, profile=profile)
        pipeline_id = "raw"
    elif no_prose:
        setup_structured_only_pipeline(engine, profile=profile)
        pipeline_id = "structured_only"
    else:
        setup_default_pipeline(engine, profile=profile)
        pipeline_id = args.pipeline

    # Enable LLM rendering if requested (only for full pipeline)
    if args.llm and not use_raw and not no_prose:
        import os
        os.environ["NNRT_USE_LLM"] = "1"

    # Run transformation
    request = TransformRequest(text=text)
    result = engine.transform(request, pipeline_id)

    # Format output
    if use_raw:
        # RAW mode: output decomposed structure without rewriting
        output = format_raw_output(result, text)
    elif no_prose or args.format == "structured":
        # Structured output (with or without prose)
        structured = build_structured_output(result, text)
        if no_prose:
            # Mark that prose was not rendered
            structured.rendered_text = "[prose rendering skipped - use without --no-prose for prose]"
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


def format_raw_output(result, original_text: str) -> str:
    """
    Format raw pipeline output for debugging.
    
    Shows what the pipeline extracted WITHOUT any rewriting.
    This is the foundation for designing proper structured output.
    """
    lines = [
        "=" * 80,
        "NNRT RAW OUTPUT (DEBUG MODE)",
        "=" * 80,
        "",
        "⚠️  DISCLAIMER: This is raw decomposition output.",
        "    No rewriting has been applied. This shows what NNRT extracts",
        "    from the narrative BEFORE any neutralization.",
        "",
        "=" * 80,
        f"SEGMENTS ({len(result.segments)})",
        "=" * 80,
    ]
    
    for i, seg in enumerate(result.segments):
        contexts = ", ".join(seg.contexts) if seg.contexts else "(none)"
        lines.append(f"\n[{i}] {seg.id}")
        lines.append(f"    Text: {seg.text[:100]}{'...' if len(seg.text) > 100 else ''}")
        lines.append(f"    Contexts: {contexts}")
        lines.append(f"    Chars: {seg.start_char}-{seg.end_char}")
    
    # NEW: Atomic Statements section
    lines.append("")
    lines.append("=" * 80)
    lines.append(f"ATOMIC STATEMENTS ({len(result.atomic_statements)})")
    lines.append("=" * 80)
    
    for i, stmt in enumerate(result.atomic_statements[:30]):  # Limit to first 30
        stmt_type = stmt.type_hint.value if hasattr(stmt.type_hint, 'value') else str(stmt.type_hint)
        flags = f" {stmt.flags}" if stmt.flags else ""
        lines.append(f"\n[{i}] {stmt.id}")
        lines.append(f"    Type: {stmt_type} (confidence: {stmt.confidence:.2f})")
        lines.append(f"    Text: {stmt.text[:80]}{'...' if len(stmt.text) > 80 else ''}")
        lines.append(f"    Clause: {stmt.clause_type}")
        if stmt.connector:
            lines.append(f"    Connector: '{stmt.connector}'")
        if stmt.derived_from:
            lines.append(f"    Derived from: {stmt.derived_from}")
        if stmt.flags:
            lines.append(f"    Flags: {stmt.flags}")
    
    if len(result.atomic_statements) > 30:
        lines.append(f"\n  ... and {len(result.atomic_statements) - 30} more statements")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append(f"POLICY DECISIONS ({len(result.policy_decisions)})")
    lines.append("=" * 80)
    
    for decision in result.policy_decisions[:50]:  # Limit to first 50
        action = decision.action.value if hasattr(decision.action, 'value') else str(decision.action)
        lines.append(f"\n  [{decision.rule_id}]")
        lines.append(f"    Action: {action}")
        lines.append(f"    Reason: {decision.reason}")
        if decision.affected_ids:
            lines.append(f"    Affects: {decision.affected_ids}")
    
    if len(result.policy_decisions) > 50:
        lines.append(f"\n  ... and {len(result.policy_decisions) - 50} more decisions")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append(f"IDENTIFIERS ({len(result.identifiers)})")
    lines.append("=" * 80)
    
    for ident in result.identifiers[:20]:
        lines.append(f"  [{ident.type.value}] {ident.value}")
    
    if len(result.identifiers) > 20:
        lines.append(f"  ... and {len(result.identifiers) - 20} more")
    
    # Summary
    lines.append("")
    lines.append("=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"  Segments: {len(result.segments)}")
    lines.append(f"  Atomic Statements: {len(result.atomic_statements)}")
    lines.append(f"  Spans: {len(result.spans)}")
    lines.append(f"  Policy decisions: {len(result.policy_decisions)}")
    lines.append(f"  Identifiers: {len(result.identifiers)}")
    lines.append(f"  Diagnostics: {len(result.diagnostics)}")
    lines.append("")
    lines.append("NOTE: In raw mode, no prose output is produced.")
    lines.append("      This is intentional - we're showing WHAT was extracted,")
    lines.append("      not HOW it would be rewritten.")
    
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
