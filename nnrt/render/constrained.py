"""
Constrained LLM Renderer — Optional fluent rendering from IR.

Uses a small instruction model (Flan-T5-small by default) to
produce more fluent neutral text from the IR.

Per LLM policy:
- Generator input is IR ONLY, never raw input text
- LLM proposes candidates, does not decide
- All outputs are reviewable and rejectable
- Ambiguity must be preserved, not resolved
- Temperature=0 for determinism

Configuration:
- NNRT_LLM_MODEL: Override the default model (default: google/flan-t5-small)
- NNRT_LLM_DEVICE: Force device selection (cpu, cuda, auto)
"""

import os
from dataclasses import dataclass
from typing import Optional
import logging

from nnrt.ir.schema_v0_1 import Segment, SemanticSpan, Entity, Event
from nnrt.ir.enums import SpanLabel, EntityRole

logger = logging.getLogger(__name__)


# ============================================================================
# Model Configuration
# ============================================================================

def _get_model_name() -> str:
    """
    Get the model name from configuration.
    
    Priority:
    1. NNRT_LLM_MODEL environment variable
    2. Default fallback
    
    This enables users to:
    - Use a different HuggingFace model
    - Point to a local model path
    - Use custom fine-tuned models
    """
    return os.environ.get("NNRT_LLM_MODEL", "google/flan-t5-small")


def _get_device_preference() -> str:
    """
    Get device preference from configuration.
    
    Options:
    - "auto": Use GPU if available, else CPU (default)
    - "cuda": Force GPU (fails if unavailable)
    - "cpu": Force CPU
    """
    return os.environ.get("NNRT_LLM_DEVICE", "auto")


# Lazy-loaded model and tokenizer
_model = None
_tokenizer = None
_loaded_model_name: Optional[str] = None


DEFAULT_MODEL = "google/flan-t5-small"


@dataclass
class RenderCandidate:
    """A candidate rendering from the LLM."""
    text: str
    confidence: float
    source: str = "llm"


def _get_model():
    """Lazy-load the model and tokenizer."""
    global _model, _tokenizer, _loaded_model_name
    
    model_name = _get_model_name()
    
    # Reload if model name changed
    if _model is not None and _loaded_model_name == model_name:
        return _model, _tokenizer
    
    try:
        from transformers import T5ForConditionalGeneration, T5Tokenizer
        import torch
        
        logger.info(f"Loading LLM model: {model_name}")
        _tokenizer = T5Tokenizer.from_pretrained(model_name)
        _model = T5ForConditionalGeneration.from_pretrained(model_name)
        _loaded_model_name = model_name
        
        # Device selection
        device_pref = _get_device_preference()
        if device_pref == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("NNRT_LLM_DEVICE=cuda but CUDA not available")
            _model = _model.cuda()
            logger.info("Using GPU for LLM inference (forced)")
        elif device_pref == "auto" and torch.cuda.is_available():
            _model = _model.cuda()
            logger.info("Using GPU for LLM inference (auto-detected)")
        else:
            logger.info("Using CPU for LLM inference")
        
    except ImportError as e:
        raise RuntimeError(
            "LLM rendering requires transformers and torch. "
            "Install with: pip install transformers torch"
        ) from e
    
    return _model, _tokenizer


def reset_model() -> None:
    """
    Reset the loaded model.
    
    Call this after changing NNRT_LLM_MODEL environment variable
    to force reloading with the new model.
    """
    global _model, _tokenizer, _loaded_model_name
    _model = None
    _tokenizer = None
    _loaded_model_name = None


def is_available() -> bool:
    """Check if LLM rendering is available."""
    try:
        from transformers import T5ForConditionalGeneration
        return True
    except ImportError:
        return False


def render_segment_llm(
    segment: Segment,
    spans: list[SemanticSpan],
    entities: list[Entity],
    events: list[Event],
    num_candidates: int = 1,
) -> list[RenderCandidate]:
    """
    Render a segment using the LLM.
    
    The LLM only sees structured IR data, never the raw text.
    This ensures it cannot hallucinate or add information.
    
    Args:
        segment: The segment to render
        spans: Spans within this segment
        entities: Entities referenced in this segment
        events: Events in this segment
        num_candidates: Number of candidate renderings to generate
        
    Returns:
        List of candidate renderings
    """
    model, tokenizer = _get_model()
    
    # Build structured prompt from IR (NOT from raw text)
    prompt = _build_ir_prompt(segment, spans, entities, events)
    
    # Generate with constrained settings
    import torch
    
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            num_beams=num_candidates,
            num_return_sequences=num_candidates,
            temperature=1.0,  # Beam search doesn't use temperature
            do_sample=False,  # Deterministic
            early_stopping=True,
        )
    
    candidates = []
    for i, output in enumerate(outputs):
        text = tokenizer.decode(output, skip_special_tokens=True)
        candidates.append(RenderCandidate(
            text=text,
            confidence=1.0 - (i * 0.1),  # Decrease confidence for later beams
            source=f"flan-t5:{i}",
        ))
    
    return candidates


def _build_ir_prompt(
    segment: Segment,
    spans: list[SemanticSpan],
    entities: list[Entity],
    events: list[Event],
) -> str:
    """
    Build a structured prompt from IR components.
    
    The prompt describes WHAT to render, not HOW.
    The LLM's job is to produce fluent text from this structure.
    """
    lines = [
        "Rewrite the following observations into neutral, factual language.",
        "Preserve all details exactly. Do not add or infer anything.",
        "Use first-person perspective. Be concise.",
        "",
        "Observations:",
    ]
    
    # Add spans as structured observations
    for span in spans:
        if span.label in (SpanLabel.OBSERVATION, SpanLabel.ACTION, SpanLabel.STATEMENT):
            lines.append(f"- {span.text}")
        elif span.label == SpanLabel.TEMPORAL:
            lines.append(f"- Time: {span.text}")
        elif span.label == SpanLabel.SPATIAL:
            lines.append(f"- Location: {span.text}")
        elif span.label == SpanLabel.INTERPRETATION:
            lines.append(f"- Described as: {span.text}")
    
    # Add entities
    if entities:
        lines.append("")
        lines.append("Persons mentioned:")
        for entity in entities:
            role_desc = _role_description(entity.role)
            lines.append(f"- {role_desc}")
    
    # Add events
    if events:
        lines.append("")
        lines.append("Events:")
        for event in events:
            lines.append(f"- {event.description}")
    
    lines.append("")
    lines.append("Neutral rewrite:")
    
    return "\n".join(lines)


def _role_description(role: EntityRole) -> str:
    """Get a neutral description for an entity role."""
    descriptions = {
        EntityRole.REPORTER: "The narrator",
        EntityRole.SUBJECT: "Another person",
        EntityRole.AUTHORITY: "An authority figure",
        EntityRole.WITNESS: "A witness",
        EntityRole.INSTITUTION: "An organization",
        EntityRole.UNKNOWN: "A person",
    }
    return descriptions.get(role, "A person")


def validate_llm_output(
    original_segment: Segment,
    candidate: RenderCandidate,
    spans: list[SemanticSpan],
) -> tuple[bool, list[str]]:
    """
    Validate that LLM output doesn't add new information.
    
    Per LLM policy, the output must be a transformation of
    existing content, not a generation of new content.
    
    Returns:
        Tuple of (is_valid, list_of_violations)
    """
    violations = []
    
    # Check 1: Output shouldn't be much longer than input
    if len(candidate.text) > len(original_segment.text) * 1.5:
        violations.append("Output significantly longer than input - may contain additions")
    
    # Check 2: Key factual terms should be preserved
    original_words = set(original_segment.text.lower().split())
    output_words = set(candidate.text.lower().split())
    
    # Common words that are OK to add/remove
    common_words = {
        "the", "a", "an", "is", "was", "were", "are", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after",
        "and", "but", "or", "nor", "so", "yet", "that", "this",
    }
    
    # Check for new significant words
    new_words = output_words - original_words - common_words
    significant_new = [w for w in new_words if len(w) > 4]
    
    if len(significant_new) > 3:
        violations.append(f"New terms introduced: {', '.join(significant_new[:5])}")
    
    # Check 3: Intent/judgment language shouldn't be added
    forbidden_additions = [
        "intentionally", "deliberately", "clearly", "obviously",
        "must have", "tried to", "wanted to",
    ]
    
    output_lower = candidate.text.lower()
    original_lower = original_segment.text.lower()
    
    for term in forbidden_additions:
        if term in output_lower and term not in original_lower:
            violations.append(f"Added forbidden term: '{term}'")
    
    is_valid = len(violations) == 0
    return is_valid, violations


class ConstrainedLLMRenderer:
    """
    High-level interface for constrained LLM rendering.
    
    This class manages:
    - Model loading and inference
    - Candidate generation
    - Output validation
    - Fallback to template rendering
    """
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
    
    def render(
        self,
        segment: Segment,
        spans: list[SemanticSpan],
        entities: list[Entity] = None,
        events: list[Event] = None,
        fallback_text: str = None,
    ) -> str:
        """
        Render a segment to neutral text.
        
        If LLM output fails validation, returns fallback_text.
        
        Args:
            segment: Segment to render
            spans: Spans within segment
            entities: Related entities
            events: Related events
            fallback_text: Text to use if LLM fails validation
            
        Returns:
            Rendered neutral text
        """
        entities = entities or []
        events = events or []
        
        try:
            candidates = render_segment_llm(
                segment, spans, entities, events, num_candidates=1
            )
            
            if not candidates:
                logger.warning("LLM returned no candidates")
                return fallback_text or segment.text
            
            # Validate the best candidate
            best = candidates[0]
            is_valid, violations = validate_llm_output(segment, best, spans)
            
            if is_valid:
                return best.text
            else:
                logger.warning(f"LLM output failed validation: {violations}")
                return fallback_text or segment.text
                
        except Exception as e:
            logger.error(f"LLM rendering failed: {e}")
            return fallback_text or segment.text
