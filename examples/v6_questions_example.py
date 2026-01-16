#!/usr/bin/env python3
"""
V6 Question Generation Example

Demonstrates how to use the V6 question generation system:
- Generate questions from timeline gaps
- Identify vague statements needing clarification
- Detect missing actors and injury follow-ups

Usage:
    python examples/v6_questions_example.py
"""

from nnrt.core.engine import Engine
from nnrt.core.context import TransformRequest
from nnrt.cli.main import setup_default_pipeline
from nnrt.v6.questions import generate_all_questions


def main():
    # Narrative with intentionally vague language and gaps
    narrative = """
    At 11:30 PM, I was walking on Cedar Street when someone approached me.
    I was grabbed and pushed to the ground. I think I hit my head on something.
    
    I don't remember what happened next.
    
    I woke up in the back of a police car. My shoulder was hurting badly.
    I was taken somewhere - maybe to the police station.
    
    The next day, I went to the emergency room.
    """
    
    print("=" * 70)
    print("               V6 QUESTION GENERATION EXAMPLE")
    print("=" * 70)
    print()
    
    # Initialize engine and pipeline
    engine = Engine()
    setup_default_pipeline(engine, profile="law_enforcement")
    
    # Process the narrative
    print("Processing narrative...")
    result = engine.transform(TransformRequest(text=narrative), pipeline_id="default")
    
    # Generate questions
    print("Generating investigation questions...")
    question_set = generate_all_questions(
        time_gaps=result.time_gaps,
        atomic_statements=result.atomic_statements,
        events=result.events,
    )
    
    # Show summary
    print()
    print("📊 QUESTION SUMMARY:")
    print(f"   Total Questions: {question_set.total_count}")
    print(f"   🔴 Critical: {question_set.critical_count}")
    print(f"   🟠 High: {question_set.high_count}")
    print(f"   Timeline Gap Questions: {question_set.timeline_gap_questions}")
    print(f"   Missing Info Questions: {question_set.missing_info_questions}")
    print(f"   Clarification Questions: {question_set.clarification_questions}")
    
    # Show all questions by priority
    print()
    print("=" * 70)
    print("                    GENERATED QUESTIONS")
    print("=" * 70)
    
    priority_icons = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '⚪',
    }
    
    for i, q in enumerate(question_set.questions, 1):
        icon = priority_icons.get(q.priority.value, '○')
        category = q.category.value.replace('_', ' ').title()
        
        print(f"\n{i}. {icon} [{q.priority.value.upper()}] {category}")
        print(f"   Q: {q.text}")
        
        if q.related_text:
            excerpt = q.related_text[:60] + "..." if len(q.related_text) > 60 else q.related_text
            print(f"   Context: \"{excerpt}\"")
        
        if q.rationale:
            print(f"   Why: {q.rationale[:70]}...")
        
        if q.follow_up_hints:
            print(f"   Follow-ups: {', '.join(q.follow_up_hints[:2])}")
    
    print()
    print("=" * 70)
    print("Use these questions in follow-up interviews to fill narrative gaps.")
    print("=" * 70)


if __name__ == "__main__":
    main()
