"""
Unit tests for p46_group_statements pass.

Test-driven development: these tests define expected behavior before implementation.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Entity
from nnrt.ir.enums import EntityRole, EntityType, GroupType, StatementType
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


class TestEncounterGrouping:
    """Tests for grouping encounter-related statements."""
    
    def test_groups_physical_actions(self):
        """Physical actions during incident should be ENCOUNTER."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("Officer Jenkins grabbed my arm. He pushed me against the car.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Officer Jenkins grabbed my arm"),
            _make_statement("stmt_002", "He pushed me against the car"),
        ]
        ctx.entities = [
            Entity(id="ent_1", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        group_statements(ctx)
        
        assert len(ctx.statement_groups) >= 1
        encounter = next((g for g in ctx.statement_groups if g.group_type == GroupType.ENCOUNTER), None)
        assert encounter is not None
        assert len(encounter.statement_ids) >= 2
    
    def test_encounter_gets_title(self):
        """Encounter groups should have descriptive title."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("The officer arrested me.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "The officer arrested me"),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        encounter = next((g for g in ctx.statement_groups if g.group_type == GroupType.ENCOUNTER), None)
        if encounter:
            assert encounter.title is not None
            assert len(encounter.title) > 0


class TestMedicalGrouping:
    """Tests for grouping medical statements."""
    
    def test_groups_medical_treatment(self):
        """Medical treatment statements should be MEDICAL."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("Dr. Foster examined my injuries. She documented bruises on my arm.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Dr. Foster examined my injuries"),
            _make_statement("stmt_002", "She documented bruises on my arm"),
        ]
        ctx.entities = [
            Entity(id="ent_1", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Dr. Foster")
        ]
        
        group_statements(ctx)
        
        medical = next((g for g in ctx.statement_groups if g.group_type == GroupType.MEDICAL), None)
        assert medical is not None
        assert len(medical.statement_ids) >= 1
    
    def test_medical_mentions_hospital(self):
        """Hospital mentions should trigger MEDICAL group."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("I was treated at St. Mary's Hospital.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I was treated at St. Mary's Hospital"),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        medical = next((g for g in ctx.statement_groups if g.group_type == GroupType.MEDICAL), None)
        assert medical is not None


class TestWitnessGrouping:
    """Tests for grouping witness account statements."""
    
    def test_groups_witness_observations(self):
        """Witness observations should be WITNESS_ACCOUNT."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("Marcus saw the incident. He started recording with his phone.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Marcus saw the incident", StatementType.OBSERVATION),
            _make_statement("stmt_002", "He started recording with his phone"),
        ]
        ctx.entities = [
            Entity(id="ent_1", type=EntityType.PERSON, role=EntityRole.WITNESS, label="Marcus")
        ]
        
        group_statements(ctx)
        
        witness = next((g for g in ctx.statement_groups if g.group_type == GroupType.WITNESS_ACCOUNT), None)
        assert witness is not None
        assert witness.primary_entity_id == "ent_1"


class TestOfficialGrouping:
    """Tests for grouping official/administrative statements."""
    
    def test_groups_complaint_filing(self):
        """Complaint filing should be OFFICIAL."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("I filed a complaint with Internal Affairs. The investigation took months.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I filed a complaint with Internal Affairs"),
            _make_statement("stmt_002", "The investigation took months"),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        official = next((g for g in ctx.statement_groups if g.group_type == GroupType.OFFICIAL), None)
        assert official is not None


class TestEmotionalGrouping:
    """Tests for grouping emotional impact statements."""
    
    def test_groups_emotional_impact(self):
        """Emotional impact statements should be EMOTIONAL."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("I was terrified. I couldn't sleep for weeks.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "I was terrified"),
            _make_statement("stmt_002", "I couldn't sleep for weeks"),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        emotional = next((g for g in ctx.statement_groups if g.group_type == GroupType.EMOTIONAL), None)
        assert emotional is not None


class TestQuoteGrouping:
    """Tests for grouping direct quotes."""
    
    def test_quotes_stay_as_quote_group(self):
        """Direct quotes should be in QUOTE group."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context('He yelled "Stop resisting!"')
        ctx.atomic_statements = [
            _make_statement("stmt_001", '"Stop resisting!"', StatementType.QUOTE),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        quote_group = next((g for g in ctx.statement_groups if g.group_type == GroupType.QUOTE), None)
        assert quote_group is not None


class TestGroupSequencing:
    """Tests for group ordering."""
    
    def test_groups_have_sequence_order(self):
        """Groups should have sequence order based on narrative position."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("Officer grabbed me. I was treated at hospital. I filed a complaint.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Officer grabbed me"),
            _make_statement("stmt_002", "I was treated at hospital"),
            _make_statement("stmt_003", "I filed a complaint"),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        # All groups should have sequence_in_narrative
        for group in ctx.statement_groups:
            assert group.sequence_in_narrative >= 0


class TestEdgeCases:
    """Tests for edge cases and robustness."""
    
    def test_no_statements_no_crash(self):
        """Should handle case with no statements gracefully."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("Some text.")
        ctx.atomic_statements = []
        
        group_statements(ctx)
        
        assert ctx.statement_groups == []
    
    def test_adds_trace(self):
        """Should add trace entry."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("Officer grabbed me.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Officer grabbed me"),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p46_group_statements" in trace_passes
    
    def test_ungrouped_statements_get_default(self):
        """Statements that don't match any pattern should get a group."""
        from nnrt.passes.p46_group_statements import group_statements
        
        ctx = _make_context("Something happened.")
        ctx.atomic_statements = [
            _make_statement("stmt_001", "Something happened"),
        ]
        ctx.entities = []
        
        group_statements(ctx)
        
        # Every statement should be in at least one group
        all_grouped_ids = set()
        for group in ctx.statement_groups:
            all_grouped_ids.update(group.statement_ids)
        
        assert "stmt_001" in all_grouped_ids
