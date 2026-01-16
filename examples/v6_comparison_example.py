#!/usr/bin/env python3
"""
V6 Multi-Narrative Comparison Example

Demonstrates how to compare multiple accounts of the same incident:
- Find agreements between sources
- Detect contradictions
- Identify unique claims
- Generate comparison report

Usage:
    python examples/v6_comparison_example.py
"""

from nnrt.core.engine import Engine
from nnrt.core.context import TransformRequest
from nnrt.cli.main import setup_default_pipeline
from nnrt.v6.comparison import compare_narratives, format_comparison_report


def main():
    # Two contrasting accounts of the same incident
    
    complainant_narrative = """
    At 11:30 PM on January 10, 2026, I was walking home on Cedar Street.
    One officer approached me from behind and grabbed my arm without warning.
    I did not resist. He twisted my arm behind my back and pushed me to the ground.
    I hit my head on the pavement. My shoulder was hurting.
    About 20 minutes later, another officer arrived.
    I was taken to the police station and held for 3 hours.
    """
    
    officer_narrative = """
    At approximately 23:45 hours on January 10, 2026, I observed a suspicious 
    individual on Cedar Street who matched a description from an earlier call.
    I approached the individual and identified myself as a police officer.
    The individual became agitated and attempted to flee.
    I used minimal force to detain the individual for questioning.
    My partner, Officer Williams, arrived on scene approximately 15 minutes later.
    The individual was transported to the station for identification.
    """
    
    witness_narrative = """
    I was looking out my window around 11:30 or 11:45 PM.
    I saw a man walking on Cedar Street.
    A police officer approached him. They seemed to talk briefly.
    Then I saw the man on the ground. I couldn't see exactly what happened.
    Another police car arrived a bit later.
    """
    
    print("=" * 70)
    print("            V6 MULTI-NARRATIVE COMPARISON EXAMPLE")
    print("=" * 70)
    print()
    
    # Initialize engine and pipeline
    engine = Engine()
    setup_default_pipeline(engine, profile="law_enforcement")
    
    # Process all narratives
    print("Processing narratives...")
    print("  • Complainant statement...")
    complainant_result = engine.transform(
        TransformRequest(text=complainant_narrative), 
        pipeline_id="default"
    )
    
    print("  • Officer report...")
    officer_result = engine.transform(
        TransformRequest(text=officer_narrative), 
        pipeline_id="default"
    )
    
    print("  • Witness statement...")
    witness_result = engine.transform(
        TransformRequest(text=witness_narrative), 
        pipeline_id="default"
    )
    
    # Compare all three narratives
    print("\nComparing narratives...")
    comparison_result = compare_narratives([
        ("complainant", complainant_result),
        ("officer", officer_result),
        ("witness", witness_result),
    ])
    
    # Show summary
    print()
    print("📊 COMPARISON SUMMARY:")
    print(f"   Sources: {comparison_result.source_count} ({', '.join(comparison_result.source_labels)})")
    print(f"   Overall Consistency: {comparison_result.overall_consistency:.0%}")
    print(f"   ✅ Agreements: {comparison_result.agreement_count}")
    print(f"   ❌ Contradictions: {comparison_result.contradiction_count}")
    print(f"   ⚠️ Unique Claims: {comparison_result.unique_claim_count}")
    print(f"   🔄 Timeline Discrepancies: {comparison_result.timeline_discrepancy_count}")
    
    if comparison_result.critical_findings:
        print(f"   🔴 Critical Issues: {len(comparison_result.critical_findings)}")
    
    # Show detailed findings
    print()
    print("=" * 70)
    print("                    DETAILED FINDINGS")
    print("=" * 70)
    
    # Group findings by type
    for finding_type in ["contradiction", "unique_claim", "timeline_discrepancy", "agreement"]:
        type_findings = [f for f in comparison_result.findings if f.type.value == finding_type]
        
        if type_findings:
            icons = {
                "agreement": "✅",
                "contradiction": "❌",
                "unique_claim": "⚠️",
                "timeline_discrepancy": "🔄",
            }
            icon = icons.get(finding_type, "•")
            
            print(f"\n{icon} {finding_type.upper().replace('_', ' ')}S ({len(type_findings)}):")
            
            for finding in type_findings[:5]:
                print(f"\n   {finding.description}")
                for source, excerpt in finding.source_excerpts.items():
                    print(f"      • {source}: \"{excerpt[:50]}...\"")
                
                if finding.suggested_resolution:
                    print(f"      💡 {finding.suggested_resolution}")
            
            if len(type_findings) > 5:
                print(f"\n   ... and {len(type_findings) - 5} more")
    
    # Print full report
    print()
    print("=" * 70)
    print("                    FORMATTED REPORT")
    print("=" * 70)
    print(format_comparison_report(comparison_result))
    
    print()
    print("=" * 70)
    print("Review the unique claims and contradictions for investigation focus.")
    print("=" * 70)


if __name__ == "__main__":
    main()
