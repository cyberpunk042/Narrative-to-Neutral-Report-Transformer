"""
SpaCy Loader — Centralized NLP resource management.

Provides a single shared spaCy model instance across all passes.
This avoids loading the model multiple times and provides a single
point of configuration.
"""

from typing import Optional

# Lazy-loaded spaCy model
_nlp: Optional["spacy.language.Language"] = None

# Default model name
DEFAULT_MODEL = "en_core_web_sm"


def get_nlp(model_name: str = DEFAULT_MODEL) -> "spacy.language.Language":
    """
    Get or load the shared spaCy model.
    
    This function lazy-loads the spaCy model on first call and
    returns the cached instance on subsequent calls.
    
    Args:
        model_name: The spaCy model to load (default: en_core_web_sm)
        
    Returns:
        The loaded spaCy Language model
        
    Raises:
        RuntimeError: If the model cannot be loaded
    """
    global _nlp
    
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load(model_name)
        except OSError:
            raise RuntimeError(
                f"spaCy model '{model_name}' not found. "
                f"Install with: python -m spacy download {model_name}"
            )
    
    return _nlp


def reset_nlp() -> None:
    """
    Reset the cached NLP model.
    
    Useful for testing or changing models at runtime.
    """
    global _nlp
    _nlp = None


def is_loaded() -> bool:
    """Check if the NLP model has been loaded."""
    return _nlp is not None
