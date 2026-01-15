"""
Pass 20 — Semantic Span Tagging

Tags spans within segments with semantic labels using NLP models.

This pass uses spaCy for syntactic analysis and dependency parsing
to identify different types of semantic content:
- Observations (sensory descriptions)
- Actions (verbs and their objects)
- Statements (reported speech)
- Interpretations (subjective judgments)
- Temporal/Spatial markers
"""

from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import SpanLabel
from nnrt.ir.schema_v0_1 import SemanticSpan
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p20_tag_spans"
log = get_pass_logger(PASS_NAME)


# Keywords that indicate interpretation/judgment
INTERPRETATION_INDICATORS = {
    "clearly", "obviously", "definitely", "certainly", "surely",
    "seemed", "appeared", "looked like", "must have", "probably",
    "suspicious", "aggressive", "threatening", "hostile", "intimidating",
}

# Legal conclusion terms to flag
LEGAL_TERMS = {
    "illegal", "unlawful", "criminal", "guilty", "assault",
    "harassment", "violation", "misconduct", "brutality",
}

# Intent attribution terms
INTENT_TERMS = {
    "intentionally", "deliberately", "purposely", "on purpose",
    "tried to", "wanted to", "meant to", "was trying to",
}

# Speech verbs for detecting statements
SPEECH_VERBS = {
    "said", "told", "asked", "yelled", "shouted", "whispered",
    "replied", "responded", "stated", "demanded", "ordered",
    "commanded", "called", "announced", "claimed",
}


def _classify_span(token_text: str, dep: str, pos: str, full_sent: str) -> tuple[SpanLabel, float]:
    """
    Classify a span based on token properties.
    
    Returns (label, confidence).
    """
    text_lower = token_text.lower()
    sent_lower = full_sent.lower()
    
    # Check for legal conclusions (high priority)
    if any(term in text_lower for term in LEGAL_TERMS):
        return SpanLabel.LEGAL_CONCLUSION, 0.9
    
    # Check for intent attribution
    if any(term in text_lower for term in INTENT_TERMS):
        return SpanLabel.INTENT_ATTRIBUTION, 0.85
    
    # Check for interpretation indicators
    if any(term in text_lower for term in INTERPRETATION_INDICATORS):
        return SpanLabel.INTERPRETATION, 0.8
    
    # Check for temporal markers
    if pos in ("DATE", "TIME") or dep == "npadvmod":
        return SpanLabel.TEMPORAL, 0.85
    
    # Check for spatial markers
    if dep in ("prep", "pobj") and any(w in text_lower for w in ["at", "in", "on", "near", "by"]):
        return SpanLabel.SPATIAL, 0.7
    
    # Check for speech verbs (statements)
    if any(verb in sent_lower for verb in SPEECH_VERBS):
        if pos == "VERB" or '"' in full_sent or "'" in full_sent:
            return SpanLabel.STATEMENT, 0.8
    
    # Default: treat as observation if verb, action if noun subject
    if pos == "VERB":
        return SpanLabel.ACTION, 0.7
    
    return SpanLabel.OBSERVATION, 0.6


def tag_spans(ctx: TransformContext) -> TransformContext:
    """
    Tag semantic spans within segments.
    
    This pass:
    - Analyzes each segment with spaCy
    - Identifies semantic categories based on syntax and keywords
    - Creates spans with confidence scores
    - Flags problematic content (legal conclusions, intent attribution)
    """
    if not ctx.segments:
        log.warning("no_segments", message="No segments to tag")
        ctx.add_diagnostic(
            level="warning",
            code="NO_SEGMENTS",
            message="No segments to tag",
            source=PASS_NAME,
        )
        return ctx

    log.verbose("starting_tagging", segments=len(ctx.segments))
    
    nlp = get_nlp()
    spans: list[SemanticSpan] = []
    span_counter = 0
    flags_detected = {"legal_conclusions": 0, "intent_attributions": 0}

    for segment in ctx.segments:
        doc = nlp(segment.text)
        
        # Group tokens into meaningful spans (noun chunks + verb phrases)
        segment_spans: list[SemanticSpan] = []
        
        # Process noun chunks as potential entity spans
        for chunk in doc.noun_chunks:
            label, confidence = _classify_span(
                chunk.text, chunk.root.dep_, chunk.root.pos_, segment.text
            )
            segment_spans.append(
                SemanticSpan(
                    id=f"span_{span_counter:04d}",
                    segment_id=segment.id,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    text=chunk.text,
                    label=label,
                    confidence=confidence,
                    source=f"{PASS_NAME}:spacy",
                )
            )
            span_counter += 1
        
        # Process verbs as action spans
        for token in doc:
            if token.pos_ == "VERB" and token.dep_ not in ("aux", "auxpass"):
                # Get verb and its direct object if present
                verb_span_start = token.idx
                verb_span_end = token.idx + len(token.text)
                verb_text = token.text
                
                # Include direct object if present
                for child in token.children:
                    if child.dep_ in ("dobj", "pobj", "attr"):
                        # Extend span to include object
                        obj_end = child.idx + len(child.text)
                        if obj_end > verb_span_end:
                            verb_span_end = obj_end
                            verb_text = segment.text[verb_span_start:verb_span_end]
                
                label, confidence = _classify_span(
                    verb_text, token.dep_, token.pos_, segment.text
                )
                
                # Check if this overlaps with existing spans
                overlaps = any(
                    s.start_char <= verb_span_start < s.end_char or
                    s.start_char < verb_span_end <= s.end_char
                    for s in segment_spans
                )
                
                if not overlaps:
                    segment_spans.append(
                        SemanticSpan(
                            id=f"span_{span_counter:04d}",
                            segment_id=segment.id,
                            start_char=verb_span_start,
                            end_char=verb_span_end,
                            text=verb_text,
                            label=label,
                            confidence=confidence,
                            source=f"{PASS_NAME}:spacy",
                        )
                    )
                    span_counter += 1
        
        # Also check for flagged content in the whole segment and create spans
        sent_lower = segment.text.lower()
        
        # Find and tag legal conclusions
        for term in LEGAL_TERMS:
            if term in sent_lower:
                idx = sent_lower.find(term)
                segment_spans.append(
                    SemanticSpan(
                        id=f"span_{span_counter:04d}",
                        segment_id=segment.id,
                        start_char=idx,
                        end_char=idx + len(term),
                        text=segment.text[idx:idx + len(term)],
                        label=SpanLabel.LEGAL_CONCLUSION,
                        confidence=0.9,
                        source=f"{PASS_NAME}:keyword",
                    )
                )
                span_counter += 1
                flags_detected["legal_conclusions"] += 1
                log.verbose("legal_conclusion_found", 
                    term=term, 
                    segment_id=segment.id,
                )
                ctx.add_diagnostic(
                    level="warning",
                    code="LEGAL_CONCLUSION_DETECTED",
                    message=f"Segment contains legal conclusion language: {segment.text[:50]}...",
                    source=PASS_NAME,
                    affected_ids=[segment.id],
                )
        
        # Find and tag intent attribution
        for term in INTENT_TERMS:
            if term in sent_lower:
                idx = sent_lower.find(term)
                segment_spans.append(
                    SemanticSpan(
                        id=f"span_{span_counter:04d}",
                        segment_id=segment.id,
                        start_char=idx,
                        end_char=idx + len(term),
                        text=segment.text[idx:idx + len(term)],
                        label=SpanLabel.INTENT_ATTRIBUTION,
                        confidence=0.85,
                        source=f"{PASS_NAME}:keyword",
                    )
                )
                span_counter += 1
                flags_detected["intent_attributions"] += 1
                log.verbose("intent_attribution_found", 
                    term=term, 
                    segment_id=segment.id,
                )
                ctx.add_diagnostic(
                    level="warning",
                    code="INTENT_ATTRIBUTION_DETECTED",
                    message=f"Segment contains intent attribution: {segment.text[:50]}...",
                    source=PASS_NAME,
                    affected_ids=[segment.id],
                )
        
        spans.extend(segment_spans)

    log.info("tagged",
        total_spans=len(spans),
        segments=len(ctx.segments),
        legal_conclusions=flags_detected["legal_conclusions"],
        intent_attributions=flags_detected["intent_attributions"],
    )
    
    ctx.spans = spans
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="tagged_spans",
        after=f"{len(spans)} spans across {len(ctx.segments)} segments",
    )

    # Summary of labels
    label_counts = {}
    for span in spans:
        label_counts[span.label.value] = label_counts.get(span.label.value, 0) + 1
    
    log.debug("label_distribution", **label_counts)
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="span_label_summary",
        after=str(label_counts),
    )

    return ctx
