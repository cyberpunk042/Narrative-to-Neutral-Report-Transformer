#!/usr/bin/env python3
"""
V6 Timeline Reconstruction Example

Demonstrates how to use the V6 timeline features:
- Temporal expression extraction
- Multi-day timeline reconstruction
- Gap detection with investigation questions

Usage:
    python examples/v6_timeline_example.py
"""

from nnrt.core.engine import Engine
from nnrt.core.context import TransformRequest
from nnrt.cli.main import setup_default_pipeline
from nnrt.render.structured import format_structured_output


def main():
    # Sample narrative with temporal complexity
    narrative = """
    At 11:30 PM on January 10, 2026, I was walking on Cedar Street when 
    Officer Jenkins approached me from behind. He grabbed my arm and 
    twisted it behind my back.
    
    I don't remember what happened next.
    
    I woke up in the back of a police car. My hands were cuffed and my 
    shoulder was hurting badly.
    
    About 20 minutes later, Sergeant Williams arrived at the scene.
    
    The next day, I went to the emergency room for shoulder pain. 
    The doctor said I had a sprained rotator cuff.
    
    Three months later, I filed this formal complaint.
    """
    
    print("=" * 70)
    print("               V6 TIMELINE RECONSTRUCTION EXAMPLE")
    print("=" * 70)
    print()
    
    # Initialize engine and pipeline
    engine = Engine()
    setup_default_pipeline(engine, profile="law_enforcement")
    
    # Process the narrative
    print("Processing narrative...")
    result = engine.transform(TransformRequest(text=narrative), pipeline_id="default")
    
    # Show V6 timeline data
    print()
    print("📊 EXTRACTED DATA:")
    print(f"   Temporal Expressions: {len(result.temporal_expressions)}")
    for expr in result.temporal_expressions[:5]:
        print(f"      • {expr.type.value}: '{expr.original_text}' → {expr.normalized_value or 'N/A'}")
    
    print(f"\n   Temporal Relations: {len(result.temporal_relationships)}")
    
    print(f"\n   Timeline Entries: {len(result.timeline)}")
    for entry in result.timeline:
        event = next((e for e in result.events if e.id == entry.event_id), None)
        desc = event.description[:40] if event else entry.event_id
        source = entry.time_source.value if entry.time_source else "unknown"
        print(f"      Day {entry.day_offset} [{source:8}] {desc}")
    
    print(f"\n   Time Gaps: {len(result.time_gaps)}")
    for gap in result.time_gaps:
        needs_inv = "⚠️" if gap.requires_investigation else "✓"
        print(f"      {needs_inv} {gap.gap_type.value}")
    
    # Show full rendered output with timeline section
    print()
    print("=" * 70)
    print("                    RENDERED OUTPUT")
    print("=" * 70)
    
    output = format_structured_output(
        rendered_text=result.rendered_text or "",
        atomic_statements=result.atomic_statements,
        entities=result.entities,
        events=result.events,
        identifiers=result.identifiers,
        timeline=result.timeline,
        time_gaps=result.time_gaps,
    )
    
    # Show just the timeline section
    in_timeline = False
    for line in output.split("\n"):
        if "RECONSTRUCTED TIMELINE" in line:
            in_timeline = True
        if in_timeline:
            print(line)
        if in_timeline and "INVESTIGATION QUESTIONS" in line:
            # Continue to show questions too
            pass
        if in_timeline and "RAW NEUTRALIZED" in line:
            break
    
    print()
    print("=" * 70)
    print("Done processing. Timeline shows multi-day span with gap detection.")
    print("=" * 70)


if __name__ == "__main__":
    main()
