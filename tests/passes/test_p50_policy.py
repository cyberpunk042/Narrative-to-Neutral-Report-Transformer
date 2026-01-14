"""
Unit tests for p50_policy pass.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment
from nnrt.passes.p50_policy import evaluate_policy


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with a segment."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestPolicyEvaluation:
    """Tests for policy rule evaluation."""
    
    def test_finds_policy_matches(self):
        """Verify policy matches are found for problematic text."""
        ctx = _make_context("He intentionally grabbed my arm.")
        
        evaluate_policy(ctx)
        
        # Should have at least one policy decision
        assert len(ctx.policy_decisions) >= 1
    
    def test_creates_policy_decisions(self):
        """Verify PolicyDecision objects are created."""
        ctx = _make_context("He deliberately pushed me.")
        
        evaluate_policy(ctx)
        
        if ctx.policy_decisions:
            decision = ctx.policy_decisions[0]
            assert hasattr(decision, 'rule_id')
            assert hasattr(decision, 'action')
            assert hasattr(decision, 'affected_ids')
    
    def test_links_decision_to_segment(self):
        """Verify decisions are linked to affected segments."""
        ctx = _make_context("He intentionally pushed me.")
        
        evaluate_policy(ctx)
        
        if ctx.policy_decisions:
            assert "seg_1" in ctx.policy_decisions[0].affected_ids


class TestCleanText:
    """Tests for text without policy violations."""
    
    def test_minimal_decisions_for_neutral_text(self):
        """Verify neutral text has minimal policy decisions."""
        ctx = _make_context("The vehicle was parked on the street.")
        
        evaluate_policy(ctx)
        
        # Should have few or no decisions
        assert len(ctx.policy_decisions) <= 2


class TestMultipleSegments:
    """Tests for multiple segments."""
    
    def test_evaluates_all_segments(self):
        """Verify all segments are evaluated."""
        req = TransformRequest(text="Multiple sentences.")
        ctx = TransformContext(request=req, raw_text="Multiple sentences.")
        ctx.segments = [
            Segment(id="seg_1", text="He intentionally hit me.", start_char=0, end_char=24),
            Segment(id="seg_2", text="The car was parked.", start_char=25, end_char=44),
        ]
        
        evaluate_policy(ctx)
        
        # First segment should have decisions, second may not
        segments_with_decisions = set()
        for d in ctx.policy_decisions:
            segments_with_decisions.update(d.affected_ids)
        
        assert "seg_1" in segments_with_decisions


class TestTracing:
    """Tests for trace entries."""
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        ctx = _make_context("Hello world.")
        
        evaluate_policy(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p50_policy" in trace_passes
