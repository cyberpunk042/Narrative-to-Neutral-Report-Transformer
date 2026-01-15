"""
Unit tests for v3 semantic understanding schema models.

These tests validate the Pydantic models for coreference, grouping,
timeline, and evidence classification.
"""

import pytest
from uuid import uuid4

from nnrt.ir.schema_v0_1 import (
    Mention,
    CoreferenceChain,
    StatementGroup,
    TimelineEntry,
    EvidenceClassification,
)
from nnrt.ir.enums import (
    MentionType,
    GroupType,
    TemporalRelation,
    EvidenceType,
)


class TestMention:
    """Tests for Mention model."""
    
    def test_create_proper_name_mention(self):
        """Create a proper name mention."""
        mention = Mention(
            id="m_001",
            segment_id="seg_001",
            start_char=0,
            end_char=15,
            text="Officer Jenkins",
            mention_type=MentionType.PROPER_NAME,
        )
        
        assert mention.id == "m_001"
        assert mention.text == "Officer Jenkins"
        assert mention.mention_type == MentionType.PROPER_NAME
        assert mention.resolved_entity_id is None
        assert mention.resolution_confidence == 0.0
    
    def test_create_pronoun_mention(self):
        """Create a pronoun mention with gender."""
        mention = Mention(
            id="m_002",
            segment_id="seg_001",
            start_char=30,
            end_char=32,
            text="he",
            mention_type=MentionType.PRONOUN,
            gender="male",
            number="singular",
        )
        
        assert mention.mention_type == MentionType.PRONOUN
        assert mention.gender == "male"
        assert mention.number == "singular"
    
    def test_mention_resolution(self):
        """Mention can be resolved to an entity."""
        mention = Mention(
            id="m_003",
            segment_id="seg_001",
            start_char=0,
            end_char=2,
            text="he",
            mention_type=MentionType.PRONOUN,
            resolved_entity_id="ent_jenkins",
            resolution_confidence=0.85,
        )
        
        assert mention.resolved_entity_id == "ent_jenkins"
        assert mention.resolution_confidence == 0.85


class TestCoreferenceChain:
    """Tests for CoreferenceChain model."""
    
    def test_create_chain(self):
        """Create a coreference chain."""
        chain = CoreferenceChain(
            id="coref_001",
            entity_id="ent_jenkins",
            mention_ids=["m_001", "m_002", "m_003"],
            confidence=0.9,
            mention_count=3,
            has_proper_name=True,
        )
        
        assert chain.entity_id == "ent_jenkins"
        assert len(chain.mention_ids) == 3
        assert chain.has_proper_name is True
    
    def test_empty_chain(self):
        """Chain can start empty."""
        chain = CoreferenceChain(
            id="coref_002",
            entity_id="ent_unknown",
        )
        
        assert chain.mention_ids == []
        assert chain.mention_count == 0


class TestStatementGroup:
    """Tests for StatementGroup model."""
    
    def test_create_encounter_group(self):
        """Create an encounter narrative group."""
        group = StatementGroup(
            id="grp_001",
            group_type=GroupType.ENCOUNTER,
            title="Initial Contact",
            statement_ids=["stmt_001", "stmt_002"],
            temporal_anchor="11:30 PM",
            sequence_in_narrative=0,
        )
        
        assert group.group_type == GroupType.ENCOUNTER
        assert group.title == "Initial Contact"
        assert len(group.statement_ids) == 2
        assert group.temporal_anchor == "11:30 PM"
    
    def test_create_witness_group(self):
        """Create a witness account group."""
        group = StatementGroup(
            id="grp_002",
            group_type=GroupType.WITNESS_ACCOUNT,
            title="Marcus Johnson's Account",
            primary_entity_id="ent_marcus",
            evidence_strength=0.8,
        )
        
        assert group.group_type == GroupType.WITNESS_ACCOUNT
        assert group.primary_entity_id == "ent_marcus"
        assert group.evidence_strength == 0.8
    
    def test_all_group_types(self):
        """All group types are valid."""
        for gt in GroupType:
            group = StatementGroup(
                id=f"grp_{gt.value}",
                group_type=gt,
                title=f"Test {gt.value}",
            )
            assert group.group_type == gt


class TestTimelineEntry:
    """Tests for TimelineEntry model."""
    
    def test_create_absolute_time_entry(self):
        """Entry with absolute time."""
        entry = TimelineEntry(
            id="tl_001",
            event_id="evt_001",
            absolute_time="11:30 PM",
            date="January 15th, 2026",
            sequence_order=0,
        )
        
        assert entry.absolute_time == "11:30 PM"
        assert entry.date == "January 15th, 2026"
        assert entry.sequence_order == 0
    
    def test_create_relative_time_entry(self):
        """Entry with relative time."""
        entry = TimelineEntry(
            id="tl_002",
            event_id="evt_002",
            relative_time="20 minutes later",
            before_entry_ids=["tl_003"],
            after_entry_ids=["tl_001"],
        )
        
        assert entry.relative_time == "20 minutes later"
        assert "tl_001" in entry.after_entry_ids
    
    def test_entry_with_group_link(self):
        """Entry can link to a group instead of event."""
        entry = TimelineEntry(
            id="tl_003",
            group_id="grp_001",
            time_confidence=0.7,
        )
        
        assert entry.group_id == "grp_001"
        assert entry.event_id is None


class TestEvidenceClassification:
    """Tests for EvidenceClassification model."""
    
    def test_create_direct_witness(self):
        """Direct witness classification."""
        ev = EvidenceClassification(
            id="ev_001",
            statement_id="stmt_001",
            evidence_type=EvidenceType.DIRECT_WITNESS,
            reliability=0.9,
        )
        
        assert ev.evidence_type == EvidenceType.DIRECT_WITNESS
        assert ev.reliability == 0.9
    
    def test_create_documentary(self):
        """Documentary evidence classification."""
        ev = EvidenceClassification(
            id="ev_002",
            statement_id="stmt_002",
            evidence_type=EvidenceType.DOCUMENTARY,
            reliability=0.95,
        )
        
        assert ev.evidence_type == EvidenceType.DOCUMENTARY
    
    def test_reported_with_source(self):
        """Reported evidence with source tracking."""
        ev = EvidenceClassification(
            id="ev_003",
            statement_id="stmt_003",
            evidence_type=EvidenceType.REPORTED,
            source_entity_id="ent_witness",
            reliability=0.6,
        )
        
        assert ev.evidence_type == EvidenceType.REPORTED
        assert ev.source_entity_id == "ent_witness"
    
    def test_corroboration(self):
        """Evidence with corroboration links."""
        ev = EvidenceClassification(
            id="ev_004",
            statement_id="stmt_004",
            evidence_type=EvidenceType.DIRECT_WITNESS,
            corroborating_ids=["stmt_005", "stmt_006"],
            contradicting_ids=["stmt_007"],
            reliability=0.85,
        )
        
        assert len(ev.corroborating_ids) == 2
        assert len(ev.contradicting_ids) == 1
    
    def test_all_evidence_types(self):
        """All evidence types are valid."""
        for et in EvidenceType:
            ev = EvidenceClassification(
                id=f"ev_{et.value}",
                statement_id="stmt_test",
                evidence_type=et,
            )
            assert ev.evidence_type == et


class TestSerializationRoundTrip:
    """Test that models serialize and deserialize correctly."""
    
    def test_mention_roundtrip(self):
        """Mention survives JSON roundtrip."""
        mention = Mention(
            id="m_001",
            segment_id="seg_001",
            start_char=0,
            end_char=10,
            text="Officer",
            mention_type=MentionType.TITLE,
        )
        
        data = mention.model_dump()
        restored = Mention(**data)
        
        assert restored.id == mention.id
        assert restored.mention_type == mention.mention_type
    
    def test_chain_roundtrip(self):
        """CoreferenceChain survives JSON roundtrip."""
        chain = CoreferenceChain(
            id="coref_001",
            entity_id="ent_001",
            mention_ids=["m_001", "m_002"],
        )
        
        data = chain.model_dump()
        restored = CoreferenceChain(**data)
        
        assert restored.mention_ids == chain.mention_ids
    
    def test_group_roundtrip(self):
        """StatementGroup survives JSON roundtrip."""
        group = StatementGroup(
            id="grp_001",
            group_type=GroupType.MEDICAL,
            title="Medical Evidence",
        )
        
        data = group.model_dump()
        restored = StatementGroup(**data)
        
        assert restored.group_type == group.group_type
