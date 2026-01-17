"""Passes — Pipeline stages for NNRT transformation."""

from nnrt.passes.p00_normalize import normalize
from nnrt.passes.p10_segment import segment
from nnrt.passes.p20_tag_spans import tag_spans
from nnrt.passes.p22_classify_statements import classify_statements
from nnrt.passes.p25_annotate_context import annotate_context
from nnrt.passes.p26_decompose import decompose
from nnrt.passes.p27_classify_atomic import classify_atomic
from nnrt.passes.p28_link_provenance import link_provenance
from nnrt.passes.p30_extract_identifiers import extract_identifiers
from nnrt.passes.p32_extract_entities import extract_entities
from nnrt.passes.p34_extract_events import extract_events
from nnrt.passes.p40_build_ir import build_ir
from nnrt.passes.p42_coreference import resolve_coreference
from nnrt.passes.p43_resolve_actors import resolve_actors
from nnrt.passes.p50_policy import evaluate_policy
from nnrt.passes.p60_augment_ir import augment_ir
from nnrt.passes.p70_render import render
from nnrt.passes.p72_safety_scrub import safety_scrub
from nnrt.passes.p75_cleanup_punctuation import cleanup_punctuation
from nnrt.passes.p80_package import package

__all__ = [
    "normalize",
    "segment",
    "tag_spans",
    "classify_statements",
    "annotate_context",
    "decompose",
    "classify_atomic",
    "link_provenance",
    "extract_identifiers",
    "extract_entities",
    "extract_events",
    "build_ir",
    "resolve_coreference",
    "resolve_actors",
    "evaluate_policy",
    "augment_ir",
    "render",
    "safety_scrub",
    "cleanup_punctuation",
    "package",
]

