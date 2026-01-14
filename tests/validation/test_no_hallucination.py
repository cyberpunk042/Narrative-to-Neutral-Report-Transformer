import pytest
from nnrt.core.context import TransformRequest
from nnrt.output.structured import build_structured_output

def test_no_hallucination(engine, hard_cases):
    """
    Verify that structured output does not contain hallucinations.
    Entities and Events must be grounded in the input text.
    """
    for case in hard_cases:
        text = case["input"]
        result = engine.transform(TransformRequest(text=text))
        output = build_structured_output(result, text)
        
        input_lower = text.lower()
        
        # 1. Check Entities
        for ent in output.entities:
            # Skip special roles that might be implicit
            if ent.role == "reporter":
                continue
                
            # Skip generated labels
            if ent.label == "Individual (Unidentified)":
                continue
                
            # Check label (if not "Unknown")
            if ent.label and ent.label != "Unknown":
                # Label should be present (case-insensitive)
                # Note: This might fail if we normalize names, but current logic is extraction-based.
                assert ent.label.lower() in input_lower, \
                    f"[Case: {case['id']}] Entity label '{ent.label}' found in output but not input."

            # Check mentions
            for mention in ent.mentions:
                m_text = mention["text"]
                assert m_text.lower() in input_lower, \
                    f"[Case: {case['id']}] Entity mention '{m_text}' found in output but not input."

        # 2. Check Events
        for evt in output.events:
            # Event description is currently built from "verb + object" from text tokens.
            # So parts of it should be in text.
            # We check if significant words are in text.
            desc_words = evt.description.lower().split()
            for word in desc_words:
                # specific check to ignore common stop words if needed, 
                # but currently we expect extraction.
                # "grabbed arm" -> both in text.
                if len(word) > 2:
                    assert word in input_lower, \
                        f"[Case: {case['id']}] Event word '{word}' in description '{evt.description}' not found in input."

        # 3. Check Statements
        for stmt in output.statements:
            # Original text must be in input
            # stmt.original is extracted text.
            assert stmt.original.lower() in input_lower, \
                f"[Case: {case['id']}] Statement original text not found in input: {stmt.original[:20]}..."
