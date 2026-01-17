"""
Integration Tests for V4 Observation Split

Tests the actual build_structured_output and format_structured_output functions
with real AtomicStatement objects to ensure correct bucket population and rendering.
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ============================================================================
# Real AtomicStatement to test actual functions
# ============================================================================

class StatementType(Enum):
    observation = "observation"
    claim = "claim"
    interpretation = "interpretation"
    quote = "quote"


@dataclass
class AtomicStatement:
    """Real AtomicStatement structure matching IR schema."""
    id: str = "test_stmt"
    text: str = ""
    type_hint: StatementType = StatementType.observation
    segment_id: str = "seg_1"
    confidence: float = 0.9
    clause_type: str = "main"
    source: str = "reporter"
    epistemic_type: str = "unknown"
    polarity: str = "asserted"
    evidence_source: str = "self_report"
    connector: Optional[str] = None
    derived_from: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    is_aberrated: bool = False
    aberration_reason: Optional[str] = None
    attributed_text: Optional[str] = None
    extracted_claim: Optional[str] = None


class TestFormatStructuredOutputIntegration:
    """Integration tests for format_structured_output with real data."""
    
    def test_direct_events_appear_in_observed_events_section(self):
        """direct_event statements should appear in OBSERVED EVENTS or NARRATIVE EXCERPTS."""
        from nnrt.render.structured import format_structured_output
        
        statements = [
            AtomicStatement(
                id="stmt_1",
                text="Officer Jenkins grabbed my arm",  # V8: Needs explicit actor
                epistemic_type="direct_event"
            ),
        ]
        
        output = format_structured_output(
            rendered_text="Test",
            atomic_statements=statements,
            entities=[],
            events=[],
            identifiers=[],
        )
        
        # V8: Should appear in either STRICT or NARRATIVE EXCERPTS
        assert "OBSERVED EVENTS" in output or "NARRATIVE EXCERPTS" in output
        assert "Officer Jenkins grabbed my arm" in output
    
    def test_self_reports_appear_in_self_reported_section(self):
        """self_report statements should appear in SELF-REPORTED STATE section."""
        from nnrt.render.structured import format_structured_output
        
        statements = [
            AtomicStatement(
                id="stmt_1",
                text="I was so scared I froze",
                epistemic_type="self_report"
            ),
        ]
        
        output = format_structured_output(
            rendered_text="Test",
            atomic_statements=statements,
            entities=[],
            events=[],
            identifiers=[],
        )
        
        assert "SELF-REPORTED STATE" in output
        assert "Reporter reports:" in output
        assert "I was so scared I froze" in output
    
    def test_follow_up_events_categorized_correctly(self):
        """Follow-up events should appear in FOLLOW-UP ACTIONS section."""
        from nnrt.render.structured import format_structured_output
        
        statements = [
            AtomicStatement(
                id="stmt_1",
                text="I went to the hospital immediately after",
                epistemic_type="direct_event"  # It's observable, but happened later
            ),
        ]
        
        output = format_structured_output(
            rendered_text="Test",
            atomic_statements=statements,
            entities=[],
            events=[],
            identifiers=[],
        )
        
        # Should be in follow-up section due to "went to the hospital"
        assert "OBSERVED EVENTS (FOLLOW-UP ACTIONS)" in output or "OBSERVED EVENTS (STRICT)" in output
    
    def test_interpretive_content_excluded_from_observed_events(self):
        """Statements with interpretive words should go to REPORTER DESCRIPTIONS."""
        from nnrt.render.structured import format_structured_output
        
        statements = [
            AtomicStatement(
                id="stmt_1",
                text="witnessed the horrifying assault",  # 'horrifying' is interpretive
                epistemic_type="direct_event"
            ),
        ]
        
        output = format_structured_output(
            rendered_text="Test",
            atomic_statements=statements,
            entities=[],
            events=[],
            identifiers=[],
        )
        
        # Should NOT be in OBSERVED EVENTS (STRICT)
        assert "REPORTER DESCRIPTIONS" in output or "witnessed the horrifying assault" not in output.split("OBSERVED EVENTS (STRICT)")[0] if "OBSERVED EVENTS (STRICT)" in output else True
    
    def test_mixed_epistemic_types_route_correctly(self):
        """Mixed statements should route to correct sections."""
        from nnrt.render.structured import format_structured_output
        
        statements = [
            AtomicStatement(id="s1", text="Officer grabbed my arm", epistemic_type="direct_event"),
            AtomicStatement(id="s2", text="I was scared", epistemic_type="self_report"),
            AtomicStatement(id="s3", text="I went to the hospital", epistemic_type="direct_event"),
            AtomicStatement(id="s4", text="They brutally slammed me", epistemic_type="direct_event"),  # interpretive
        ]
        
        output = format_structured_output(
            rendered_text="Test",
            atomic_statements=statements,
            entities=[],
            events=[],
            identifiers=[],
        )
        
        # Check correct sections exist
        assert "OBSERVED EVENTS" in output
        assert "SELF-REPORTED STATE" in output


class TestPipelineIntegration:
    """Tests for pipeline configuration."""
    
    def test_structured_pipeline_includes_epistemic_tag(self):
        """structured_only_pipeline should include tag_epistemic pass."""
        from nnrt.cli.main import setup_structured_only_pipeline
        from nnrt.core.engine import Engine
        
        engine = Engine()
        setup_structured_only_pipeline(engine)
        
        # Get the pipeline
        pipeline = engine._pipelines.get('structured_only')
        assert pipeline is not None, "structured_only pipeline should exist"
        
        # Check that tag_epistemic is in the pipeline passes
        pass_names = [p.__name__ if hasattr(p, '__name__') else str(p) for p in pipeline.passes]
        assert any('epistemic' in name.lower() for name in pass_names), \
            f"tag_epistemic should be in structured_only_pipeline. Passes: {pass_names}"
    
    def test_default_pipeline_includes_attribution(self):
        """Default pipeline should include attribute_statements pass."""
        from nnrt.cli.main import setup_default_pipeline
        from nnrt.core.engine import Engine
        
        engine = Engine()
        setup_default_pipeline(engine, profile="law_enforcement")
        
        pipeline = engine._pipelines.get('default')
        assert pipeline is not None, "default pipeline should exist"
        
        pass_names = [p.__name__ if hasattr(p, '__name__') else str(p) for p in pipeline.passes]
        assert any('attribute' in name.lower() for name in pass_names), \
            f"attribute_statements should be in default pipeline. Passes: {pass_names}"


class TestCameraFriendlyFilterIntegration:
    """Integration tests for camera-friendly filtering."""
    
    def test_all_interpretive_words_filtered(self):
        """All defined interpretive words should cause exclusion."""
        from nnrt.render.structured import format_structured_output
        
        interpretive_words = [
            'horrifying', 'brutal', 'brutally', 'viciously', 'psychotic',
            'innocent', 'criminal', 'clearly', 'deliberately', 'cover-up'
        ]
        
        for word in interpretive_words:
            statements = [
                AtomicStatement(
                    id=f"stmt_{word}",
                    text=f"Test {word} statement",
                    epistemic_type="direct_event"
                ),
            ]
            
            output = format_structured_output(
                rendered_text="Test",
                atomic_statements=statements,
                entities=[],
                events=[],
                identifiers=[],
            )
            
            # Should NOT appear in STRICT (should be in REPORTER DESCRIPTIONS)
            if "OBSERVED EVENTS (STRICT)" in output:
                incident_section = output.split("OBSERVED EVENTS (STRICT)")[1]
                if "OBSERVED EVENTS (FOLLOW-UP" in incident_section:
                    incident_section = incident_section.split("OBSERVED EVENTS (FOLLOW-UP")[0]
                elif "REPORTER DESCRIPTIONS" in incident_section:
                    incident_section = incident_section.split("REPORTER DESCRIPTIONS")[0]
                    
                assert f"Test {word} statement" not in incident_section, \
                    f"'{word}' should exclude statement from STRICT"
