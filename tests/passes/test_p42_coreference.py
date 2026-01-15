"""
Unit tests for p42_coreference pass.

Test-driven development: these tests define expected behavior before implementation.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Entity
from nnrt.ir.enums import EntityRole, EntityType, MentionType


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with segments."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.normalized_text = text
    # Create a single segment for the full text
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestMentionExtraction:
    """Tests for extracting mentions from text."""
    
    def test_extracts_proper_names(self):
        """Should extract PERSON entities as proper name mentions."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Officer Jenkins approached the vehicle.")
        # Pre-populate with an entity (from p32)
        ctx.entities = [
            Entity(id="ent_1", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        resolve_coreference(ctx)
        
        # Should have at least one mention
        assert len(ctx.mentions) >= 1
        jenkins_mention = next((m for m in ctx.mentions if "Jenkins" in m.text), None)
        assert jenkins_mention is not None
        assert jenkins_mention.mention_type == MentionType.PROPER_NAME
    
    def test_extracts_pronouns(self):
        """Should extract pronouns as mentions."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Officer Jenkins arrived. He approached the vehicle.")
        ctx.entities = [
            Entity(id="ent_1", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        resolve_coreference(ctx)
        
        # Should find the pronoun "He"
        pronoun_mention = next((m for m in ctx.mentions if m.text.lower() == "he"), None)
        assert pronoun_mention is not None
        assert pronoun_mention.mention_type == MentionType.PRONOUN


class TestPronounResolution:
    """Tests for resolving pronouns to entities."""
    
    def test_resolves_he_to_male_entity(self):
        """'He' should resolve to a male entity."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Officer Jenkins grabbed my arm. He then pushed me.")
        ctx.entities = [
            Entity(id="ent_jenkins", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        resolve_coreference(ctx)
        
        # Find the "He" mention
        he_mention = next((m for m in ctx.mentions if m.text == "He"), None)
        assert he_mention is not None
        assert he_mention.resolved_entity_id == "ent_jenkins"
    
    def test_resolves_she_to_female_entity(self):
        """'She' should resolve to a female entity."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Dr. Foster examined me. She documented the injuries.")
        ctx.entities = [
            Entity(id="ent_foster", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Dr. Foster")
        ]
        
        resolve_coreference(ctx)
        
        she_mention = next((m for m in ctx.mentions if m.text == "She"), None)
        assert she_mention is not None
        assert she_mention.resolved_entity_id == "ent_foster"
    
    def test_first_person_resolves_to_reporter(self):
        """'I', 'me', 'my' should resolve to reporter entity."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("I was walking home. He grabbed my arm.")
        ctx.entities = [
            Entity(id="ent_reporter", type=EntityType.PERSON, role=EntityRole.REPORTER, label="Reporter"),
            Entity(id="ent_officer", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer")
        ]
        
        resolve_coreference(ctx)
        
        i_mention = next((m for m in ctx.mentions if m.text == "I"), None)
        my_mention = next((m for m in ctx.mentions if m.text == "my"), None)
        
        assert i_mention is not None
        assert i_mention.resolved_entity_id == "ent_reporter"
        assert my_mention is not None
        assert my_mention.resolved_entity_id == "ent_reporter"


class TestCoreferenceChains:
    """Tests for building coreference chains."""
    
    def test_builds_chain_for_entity(self):
        """Should build a chain linking all mentions of an entity."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Officer Jenkins arrived. He approached me. Jenkins spoke.")
        ctx.entities = [
            Entity(id="ent_jenkins", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        resolve_coreference(ctx)
        
        # Should have a chain for Jenkins
        jenkins_chain = next((c for c in ctx.coreference_chains if c.entity_id == "ent_jenkins"), None)
        assert jenkins_chain is not None
        assert len(jenkins_chain.mention_ids) >= 2  # At least "Officer Jenkins" and "He"
    
    def test_chain_has_proper_name_flag(self):
        """Chain should indicate if it has a proper name mention."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Officer Jenkins arrived. He spoke.")
        ctx.entities = [
            Entity(id="ent_jenkins", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        resolve_coreference(ctx)
        
        jenkins_chain = next((c for c in ctx.coreference_chains if c.entity_id == "ent_jenkins"), None)
        assert jenkins_chain is not None
        assert jenkins_chain.has_proper_name is True


class TestRecencyResolution:
    """Tests for recency-based pronoun resolution."""
    
    def test_pronoun_resolves_to_nearest_entity(self):
        """Pronouns should prefer the most recently mentioned entity."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        # Two officers mentioned, "He" after Rodriguez should resolve to Rodriguez
        ctx = _make_context("Officer Jenkins spoke first. Officer Rodriguez arrived later. He approached.")
        ctx.entities = [
            Entity(id="ent_jenkins", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins"),
            Entity(id="ent_rodriguez", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Rodriguez")
        ]
        
        resolve_coreference(ctx)
        
        he_mention = next((m for m in ctx.mentions if m.text == "He"), None)
        assert he_mention is not None
        # Should resolve to Rodriguez (most recent)
        assert he_mention.resolved_entity_id == "ent_rodriguez"


class TestEdgeCases:
    """Tests for edge cases and robustness."""
    
    def test_no_entities_no_crash(self):
        """Should handle case with no entities gracefully."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Someone did something.")
        ctx.entities = []
        
        # Should not crash
        resolve_coreference(ctx)
        
        assert ctx.coreference_chains == []
    
    def test_no_pronouns_still_builds_chains(self):
        """Should build chains even with only proper names."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Officer Jenkins arrived. Jenkins spoke to Marcus.")
        ctx.entities = [
            Entity(id="ent_jenkins", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        resolve_coreference(ctx)
        
        # Should have a chain with proper name mentions
        assert len(ctx.coreference_chains) >= 1
    
    def test_adds_trace(self):
        """Should add trace entry."""
        from nnrt.passes.p42_coreference import resolve_coreference
        
        ctx = _make_context("Officer Jenkins arrived.")
        ctx.entities = [
            Entity(id="ent_1", type=EntityType.PERSON, role=EntityRole.AUTHORITY, label="Officer Jenkins")
        ]
        
        resolve_coreference(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p42_coreference" in trace_passes
