"""
Unit tests for p30_extract_identifiers pass.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment
from nnrt.ir.enums import IdentifierType
from nnrt.passes.p30_extract_identifiers import extract_identifiers


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with a segment."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestBadgeNumberExtraction:
    """Tests for badge number extraction."""
    
    def test_extracts_badge_number(self):
        """Verify badge numbers are extracted."""
        ctx = _make_context("Officer Badge #12345 approached me.")
        
        extract_identifiers(ctx)
        
        badge_ids = [i for i in ctx.identifiers if i.type == IdentifierType.BADGE_NUMBER]
        assert len(badge_ids) >= 1
        assert "12345" in badge_ids[0].value
    
    def test_extracts_badge_with_keyword(self):
        """Verify 'Badge number:' format works."""
        ctx = _make_context("Badge number: 98765 was recorded.")
        
        extract_identifiers(ctx)
        
        badge_ids = [i for i in ctx.identifiers if i.type == IdentifierType.BADGE_NUMBER]
        assert len(badge_ids) >= 1
    
    def test_extracts_unit_number(self):
        """Verify unit numbers are extracted as badge type."""
        ctx = _make_context("Unit #42 responded to the call.")
        
        extract_identifiers(ctx)
        
        badge_ids = [i for i in ctx.identifiers if i.type == IdentifierType.BADGE_NUMBER]
        assert len(badge_ids) >= 1


class TestTimeExtraction:
    """Tests for time extraction."""
    
    def test_extracts_time_with_am_pm(self):
        """Verify time with AM/PM is extracted."""
        ctx = _make_context("The incident occurred at 3:45 PM.")
        
        extract_identifiers(ctx)
        
        time_ids = [i for i in ctx.identifiers if i.type == IdentifierType.TIME]
        assert len(time_ids) >= 1
        assert "3:45" in time_ids[0].value
    
    def test_extracts_time_24h(self):
        """Verify 24-hour time format is extracted."""
        ctx = _make_context("At 14:30 we received the report.")
        
        extract_identifiers(ctx)
        
        time_ids = [i for i in ctx.identifiers if i.type == IdentifierType.TIME]
        assert len(time_ids) >= 1


class TestDateExtraction:
    """Tests for date extraction."""
    
    def test_extracts_slash_date(self):
        """Verify MM/DD/YYYY format is extracted."""
        ctx = _make_context("On 01/15/2026 at the location.")
        
        extract_identifiers(ctx)
        
        date_ids = [i for i in ctx.identifiers if i.type == IdentifierType.DATE]
        assert len(date_ids) >= 1
        assert "01/15/2026" in date_ids[0].value
    
    def test_extracts_text_date(self):
        """Verify 'January 15, 2026' format is extracted."""
        ctx = _make_context("On January 15, 2026 I was stopped.")
        
        extract_identifiers(ctx)
        
        date_ids = [i for i in ctx.identifiers if i.type == IdentifierType.DATE]
        assert len(date_ids) >= 1


class TestNameExtraction:
    """Tests for name extraction via NER."""
    
    def test_extracts_person_name(self):
        """Verify person names are extracted."""
        ctx = _make_context("Officer John Smith approached the vehicle.")
        
        extract_identifiers(ctx)
        
        name_ids = [i for i in ctx.identifiers if i.type == IdentifierType.NAME]
        assert len(name_ids) >= 1


class TestMultipleIdentifiers:
    """Tests for extracting multiple identifiers."""
    
    def test_extracts_multiple_types(self):
        """Verify multiple identifier types in one text."""
        ctx = _make_context(
            "On 01/15/2026 at 3:30 PM, Officer Badge #12345 stopped me."
        )
        
        extract_identifiers(ctx)
        
        # Should have date, time, and badge
        types = {i.type for i in ctx.identifiers}
        assert IdentifierType.DATE in types
        assert IdentifierType.TIME in types
        assert IdentifierType.BADGE_NUMBER in types


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_no_segments_adds_warning(self):
        """Verify missing segments produce warning."""
        req = TransformRequest(text="Hello")
        ctx = TransformContext(request=req, raw_text="Hello")
        ctx.segments = []  # No segments
        
        extract_identifiers(ctx)
        
        assert len(ctx.diagnostics) > 0
        assert ctx.diagnostics[0].code == "NO_SEGMENTS"
    
    def test_no_identifiers_in_simple_text(self):
        """Verify simple text without identifiers."""
        ctx = _make_context("Hello world.")
        
        extract_identifiers(ctx)
        
        # May have some NER false positives, but should be minimal
        assert len(ctx.identifiers) <= 2
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        ctx = _make_context("Badge #12345")
        
        extract_identifiers(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p30_extract_identifiers" in trace_passes
