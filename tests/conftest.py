"""Shared test fixtures.

NLP-model availability guard
----------------------------
The pipeline's NLP passes require spaCy's ``en_core_web_sm`` language model,
which is a separate data download (``python -m spacy download en_core_web_sm``)
that CI does not install by default. Without it, every test that exercises the
NLP engine raises ``OSError: [E050] Can't find model`` at ``spacy.load`` time.

Rather than let those surface as *failures*, we skip them when the model is
absent: a test that can't run its subject because an optional data dependency is
missing is a *skip*, not a failure. Tests that never touch the NLP engine are
unaffected — the guard only intercepts ``spacy.load``. Install the model (or the
``nlp`` extra) and the same tests run normally.
"""
from __future__ import annotations

import pytest

SPACY_MODEL = "en_core_web_sm"


def _model_available() -> bool:
    try:
        import spacy
        spacy.load(SPACY_MODEL)
        return True
    except Exception:
        return False


_NLP_MODEL_AVAILABLE = _model_available()


@pytest.fixture(autouse=True)
def _skip_when_spacy_model_missing(monkeypatch):
    """Turn "NLP model not installed" into a per-test skip at ``spacy.load``.

    ``pytest.skip`` raises ``Skipped`` (a ``BaseException`` subclass), so it
    propagates cleanly through the pipeline's ``except OSError`` / ``except
    Exception`` handlers and is recorded as a skip on whichever test reached the
    NLP engine — nothing else is affected."""
    if _NLP_MODEL_AVAILABLE:
        return
    import spacy

    def _skip_load(*_args, **_kwargs):
        pytest.skip(
            f"spaCy model {SPACY_MODEL!r} not installed "
            f"(run `python -m spacy download {SPACY_MODEL}` or install the nlp extra)"
        )

    monkeypatch.setattr(spacy, "load", _skip_load)
