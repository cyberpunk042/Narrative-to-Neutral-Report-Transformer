"""
Unit tests for p48_classify_evidence pass.

Test-driven development: these tests define expected behavior before implementation.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Entity
from nnrt.ir.enums import EntityRole, EntityType, EvidenceType, StatementType
from nnrt.passes.p26_decompose import AtomicStatement


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with segments."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.normalized_text = text
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


def _make_statement(id: str, text: str, type_hint: StatementType = StatementType.CLAIM, 
                    segment_id: str = "seg_1") -> AtomicStatement:
    """Helper to create an atomic statement."""
    return AtomicStatement(
        id=id,
        text=text,
        segment_id=segment_id,
        span_start=0,
        span_end=len(text),
        clause_type="main",
        type_hint=type_hint,
    )


class TestDirectWitnessEvidence:
    """Tests for classifying direct witness evidence."""
    
    def test_first_person_observation_is_direct(self):
        """First-person observations should be DIRECT_WITNESS."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("I saw Officer Jenkins grab my arm.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I saw Officer Jenkins grab my arm", StatementType.OBSERVATION),
        ]
        ctx.entities = [
            Entity(id="ent_reporter", type=EntityType.PERSON, role=EntityRole.REPORTER, label="Reporter")
        ]
        
        classify_evidence(ctx)
        
        assert len(ctx.evidence_classifications) >= 1
        classification = next((c for c in ctx.evidence_classifications if c.statement_id == "stmt_001"), None)
        assert classification is not None
        assert classification.evidence_type == EvidenceType.DIRECT_WITNESS
    
    def test_i_felt_is_direct(self):
        """First-person sensory experiences should be DIRECT_WITNESS."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("I felt a sharp pain in my shoulder.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I felt a sharp pain in my shoulder"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classification = next((c for c in ctx.evidence_classifications if c.statement_id == "stmt_001"), None)
        assert classification is not None
        assert classification.evidence_type == EvidenceType.DIRECT_WITNESS
    
    def test_direct_witness_high_reliability(self):
        """Direct witness evidence should have higher reliability."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("I saw him hit me.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I saw him hit me", StatementType.OBSERVATION),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classification = ctx.evidence_classifications[0]
        assert classification.reliability >= 0.7


class TestReportedEvidence:
    """Tests for classifying reported/hearsay evidence."""
    
    def test_he_said_is_reported(self):
        """'He said' patterns should be REPORTED."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("He told me that the officer used excessive force.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "He told me that the officer used excessive force"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classification = next((c for c in ctx.evidence_classifications if c.statement_id == "stmt_001"), None)
        assert classification is not None
        assert classification.evidence_type == EvidenceType.REPORTED
    
    def test_witness_said_is_reported(self):
        """Witness statements should be REPORTED with source entity."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("Marcus said he saw the whole thing.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Marcus said he saw the whole thing"),
        ]
        ctx.entities = [
            Entity(id="ent_marcus", type=EntityType.PERSON, role=EntityRole.WITNESS, label="Marcus")
        ]
        
        classify_evidence(ctx)
        
        classification = ctx.evidence_classifications[0]
        assert classification.evidence_type == EvidenceType.REPORTED
        assert classification.source_entity_id == "ent_marcus"


class TestDocumentaryEvidence:
    """Tests for classifying documentary evidence."""
    
    def test_medical_records_is_documentary(self):
        """Medical records should be DOCUMENTARY."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("The medical report documented multiple bruises.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "The medical report documented multiple bruises"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classification = ctx.evidence_classifications[0]
        assert classification.evidence_type == EvidenceType.DOCUMENTARY
    
    def test_official_records_is_documentary(self):
        """Official records should be DOCUMENTARY."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("The police report states that force was used.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "The police report states that force was used"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classification = ctx.evidence_classifications[0]
        assert classification.evidence_type == EvidenceType.DOCUMENTARY
    
    def test_documentary_has_higher_reliability(self):
        """Documentary evidence should have high reliability."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("The body camera footage shows the incident.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "The body camera footage shows the incident"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classification = ctx.evidence_classifications[0]
        assert classification.reliability >= 0.8


class TestPhysicalEvidence:
    """Tests for classifying physical evidence."""
    
    def test_injuries_are_physical(self):
        """Physical injuries should be PHYSICAL evidence."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("I had visible bruises on my arm.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I had visible bruises on my arm"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classification = ctx.evidence_classifications[0]
        assert classification.evidence_type == EvidenceType.PHYSICAL


class TestCorroboration:
    """Tests for detecting corroboration between statements."""
    
    def test_detects_corroboration(self):
        """Should detect when statements corroborate each other."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        # First person saw + document confirms = corroboration
        ctx = _make_context("I saw him push me. The video footage shows him push me.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I saw him push me", StatementType.OBSERVATION),
            _make_statement("stmt_002", "The video footage shows him push me"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        # At least one statement should have corroborating_ids
        has_corroboration = any(len(c.corroborating_ids) > 0 for c in ctx.evidence_classifications)
        assert has_corroboration


class TestEdgeCases:
    """Tests for edge cases and robustness."""
    
    def test_no_statements_no_crash(self):
        """Should handle case with no statements gracefully."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("Some text.")
        ctx.atomic_statements = []
        
        classify_evidence(ctx)
        
        assert ctx.evidence_classifications == []
    
    def test_adds_trace(self):
        """Should add trace entry."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("I saw something.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I saw something"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p48_classify_evidence" in trace_passes
    
    def test_all_statements_get_classified(self):
        """Every statement should get a classification."""
        from nnrt.passes.p48_classify_evidence import classify_evidence
        
        ctx = _make_context("Something happened. Then something else.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Something happened"),
            _make_statement("stmt_002", "Then something else"),
        ]
        ctx.entities = []
        
        classify_evidence(ctx)
        
        classified_ids = {c.statement_id for c in ctx.evidence_classifications}
        assert "stmt_001" in classified_ids
        assert "stmt_002" in classified_ids
