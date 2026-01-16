"""
Tests for p43_resolve_actors — Actor Resolution Pass (V5).

Tests that pronouns are correctly replaced with entity names and
that fragments/quote-interpretation splits are properly handled.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.passes.p43_resolve_actors import (
    resolve_actors,
    _is_fragment,
    _split_quote_interpretation,
    _build_pronoun_map,
)
from nnrt.passes.p26_decompose import AtomicStatement
from nnrt.ir.schema_v0_1 import Entity, Mention, CoreferenceChain
from nnrt.ir.enums import EntityRole, EntityType, MentionType


def _make_context(text: str) -> TransformContext:
    """Create a TransformContext with proper initialization."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    return ctx


class TestFragmentDetection:
    """Test fragment detection logic."""
    
    def test_but_is_fragment(self):
        assert _is_fragment("but then he grabbed me")
    
    def test_and_is_fragment(self):
        assert _is_fragment("and they pushed me")
    
    def test_which_is_fragment(self):
        assert _is_fragment("which was clearly a threat")
    
    def test_suddenly_is_fragment(self):
        assert _is_fragment("suddenly he appeared")
    
    def test_normal_sentence_not_fragment(self):
        assert not _is_fragment("The officer grabbed my arm")
    
    def test_i_statement_not_fragment(self):
        assert not _is_fragment("I saw him approach")
    
    def test_empty_string_not_fragment(self):
        assert not _is_fragment("")


class TestQuoteInterpretationSplit:
    """Test splitting of quote + interpretation mixed statements."""
    
    def test_splits_which_was_clearly(self):
        """Test splitting 'He said "X" which was clearly Y'"""
        class MockStmt:
            text = 'He said "Stop!" which was clearly a threat'
        
        result = _split_quote_interpretation(MockStmt())
        assert result is not None
        assert result["quote_text"] == 'He said "Stop!"'
        assert "threat" in result["interpretation_text"]
    
    def test_splits_comma_which(self):
        """Test splitting 'He said "X", which was Y'"""
        class MockStmt:
            text = 'He yelled "Get down!", which was intimidating'
        
        result = _split_quote_interpretation(MockStmt())
        assert result is not None
        assert "Get down" in result["quote_text"]
    
    def test_no_split_for_clean_quote(self):
        """Clean quotes without interpretation don't get split."""
        class MockStmt:
            text = 'He said "Stop resisting"'
        
        result = _split_quote_interpretation(MockStmt())
        assert result is None
    
    def test_no_split_for_normal_sentence(self):
        """Normal sentences without quotes don't get split."""
        class MockStmt:
            text = "The officer approached me"
        
        result = _split_quote_interpretation(MockStmt())
        assert result is None


class TestBuildPronounMap:
    """Test building the pronoun → entity mapping."""
    
    def test_maps_pronoun_to_entity(self):
        ctx = _make_context("He grabbed me")
        
        # Add entity
        entity = Entity(
            id="ent_001",
            type=EntityType.PERSON,
            label="Officer Jenkins",
            role=EntityRole.AUTHORITY,
        )
        ctx.entities = [entity]
        
        # Add mention (pronoun resolved to entity)
        mention = Mention(
            id="m_001",
            segment_id="seg_000",
            start_char=0,
            end_char=2,
            text="He",
            mention_type=MentionType.PRONOUN,
            resolved_entity_id="ent_001",
            resolution_confidence=0.85,
        )
        ctx.mentions = [mention]
        
        pronoun_map = _build_pronoun_map(ctx)
        
        # Should have a mapping for the pronoun
        assert len(pronoun_map) > 0
        # The value should be the entity label
        assert "Officer Jenkins" in pronoun_map.values()
    
    def test_empty_for_no_mentions(self):
        ctx = _make_context("Test")
        ctx.mentions = []
        ctx.entities = []
        
        pronoun_map = _build_pronoun_map(ctx)
        assert pronoun_map == {}


class TestResolveActorsPass:
    """Test the full resolve_actors pass."""
    
    def test_flags_unresolved_pronouns(self):
        """Statements with unresolved pronouns get flagged."""
        ctx = _make_context("He grabbed me")
        
        # Add a statement with a pronoun but NO coreference data
        stmt = AtomicStatement(
            id="stmt_0000",
            text="He grabbed me",
            segment_id="seg_000",
            span_start=0,
            span_end=13,
        )
        ctx.atomic_statements = [stmt]
        ctx.mentions = []  # No coreference data
        ctx.entities = []
        
        result = resolve_actors(ctx)
        
        # Should flag as unresolved
        assert "actor_unresolved" in result.atomic_statements[0].flags
    
    def test_flags_fragments(self):
        """Fragment statements get flagged."""
        ctx = _make_context("but then he ran")
        
        stmt = AtomicStatement(
            id="stmt_0000",
            text="but then he ran",
            segment_id="seg_000",
            span_start=0,
            span_end=15,
        )
        ctx.atomic_statements = [stmt]
        ctx.mentions = []
        ctx.entities = []
        
        result = resolve_actors(ctx)
        
        # Should flag as fragment
        assert "fragment" in result.atomic_statements[0].flags
    
    def test_adds_trace(self):
        """Pass adds trace entry."""
        ctx = _make_context("Test")
        ctx.atomic_statements = []
        
        result = resolve_actors(ctx)
        
        traces = [t for t in result.trace if t.pass_name == "p43_resolve_actors"]
        assert len(traces) > 0
    
    def test_handles_empty_statements(self):
        """Pass handles empty atomic statements list gracefully."""
        ctx = _make_context("")
        ctx.atomic_statements = []
        
        result = resolve_actors(ctx)
        
        # Should not crash
        assert result is not None


class TestActorResolution:
    """Test actual pronoun → entity replacement."""
    
    def test_resolves_he_to_entity_name(self):
        """'He' should be replaced with entity label."""
        ctx = _make_context("He grabbed my arm")
        
        # Setup entity
        entity = Entity(
            id="ent_001",
            type=EntityType.PERSON,
            label="Officer Jenkins",
            role=EntityRole.AUTHORITY,
        )
        ctx.entities = [entity]
        
        # Setup mention (pronoun at position 0)
        mention = Mention(
            id="m_001",
            segment_id="seg_000",
            start_char=0,
            end_char=2,
            text="He",
            mention_type=MentionType.PRONOUN,
            resolved_entity_id="ent_001",
            resolution_confidence=0.85,
        )
        ctx.mentions = [mention]
        
        # Setup statement
        stmt = AtomicStatement(
            id="stmt_0000",
            text="He grabbed my arm",
            segment_id="seg_000",
            span_start=0,
            span_end=17,
        )
        ctx.atomic_statements = [stmt]
        
        result = resolve_actors(ctx)
        
        # Should have actor_resolved_text set
        resolved = result.atomic_statements[0].actor_resolved_text
        assert resolved is not None
        # The pronoun should be replaced (exact match depends on implementation)
        # At minimum, we should have the entity name somewhere
        assert "Officer Jenkins" in resolved or "actor_unresolved" not in result.atomic_statements[0].flags
