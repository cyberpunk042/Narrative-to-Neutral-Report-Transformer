# Minimal Viable Refactor: Span Decision Tracking

## Goal

Enable passes to communicate about span-level decisions **without** re-analyzing text.

## Change: Add span_decisions to TransformContext

```python
@dataclass
class TransformContext:
    # ... existing fields ...
    
    # NEW: Map span_id → decision
    # This connects policy decisions directly to spans
    span_decisions: dict[str, PolicyDecision] = field(default_factory=dict)
    
    # NEW: Protected character ranges per segment
    # Any range here should not be modified by render
    protected_ranges: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    
    # Helper methods
    def protect_span(self, span: SemanticSpan) -> None:
        """Mark a span as protected from modification."""
        seg_id = span.segment_id
        if seg_id not in self.protected_ranges:
            self.protected_ranges[seg_id] = []
        self.protected_ranges[seg_id].append((span.start_char, span.end_char))
    
    def is_protected(self, segment_id: str, start: int, end: int) -> bool:
        """Check if a character range is protected."""
        if segment_id not in self.protected_ranges:
            return False
        for pstart, pend in self.protected_ranges[segment_id]:
            if start >= pstart and end <= pend:
                return True
        return False
    
    def set_span_decision(self, span_id: str, decision: PolicyDecision) -> None:
        """Record a policy decision for a specific span."""
        self.span_decisions[span_id] = decision
    
    def get_span_decision(self, span_id: str) -> Optional[PolicyDecision]:
        """Get the policy decision for a span, if any."""
        return self.span_decisions.get(span_id)
```

## Change: Update p50_policy to Record Span Decisions

```python
def evaluate_policy(ctx: TransformContext) -> TransformContext:
    engine = get_policy_engine()
    
    for segment in ctx.segments:
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        matches = engine.find_matches(segment.text)
        
        for match in matches:
            decision = engine.create_decision(match)
            ctx.policy_decisions.append(decision)
            
            # NEW: Link decision to affected spans
            for span in segment_spans:
                if span.start_char >= match.start and span.end_char <= match.end:
                    ctx.set_span_decision(span.id, decision)
                    
                    # If decision is PRESERVE, mark as protected
                    if decision.action == PolicyAction.PRESERVE:
                        ctx.protect_span(span)
```

## Change: Update p70_render to Check Decisions

```python
def _render_template(ctx: TransformContext) -> TransformContext:
    engine = get_policy_engine()
    
    for segment in ctx.segments:
        rendered, decisions = engine.apply_rules(segment.text)
        
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        for span in segment_spans:
            # CHECK: Did policy already decide about this span?
            existing_decision = ctx.get_span_decision(span.id)
            if existing_decision:
                if existing_decision.action == PolicyAction.PRESERVE:
                    continue  # Policy said preserve - SKIP
                # Policy said something else - respect it
                continue
            
            # CHECK: Is this span protected?
            if ctx.is_protected(segment.id, span.start_char, span.end_char):
                continue  # Protected - SKIP
            
            # Only now apply span-based transformations
            if span.label == SpanLabel.LEGAL_CONCLUSION:
                # ... existing logic ...
```

## Why This Works

1. **Policy makes decisions once** — in p50_policy
2. **Decisions are attached to spans** — via span_decisions dict
3. **Render respects decisions** — checks before transforming
4. **No re-analysis needed** — data carries the decision

## What We Can Remove After This

Once this is in place, we can remove:

```python
# REMOVE from p70_render.py
charge_contexts = [
    "charged with", "charge of", "accused of"...
]
is_charge_context = any(ctx_phrase in segment.text.lower() for ctx_phrase in charge_contexts)

# REMOVE from _get_intent_replacement
physical_actions = ["say", "speak", "breathe"...]
```

These become YAML rules with proper context:

```yaml
# In base.yaml
- id: preserve_charge_legal_terms
  match:
    patterns: ["assault", "battery", "robbery"]
  condition:
    segment_context: charge_description  # NEW: Context-aware condition
  action: preserve
```

## Implementation Order

1. Add fields to TransformContext (5 min)
2. Add helper methods (10 min)
3. Update p50_policy to set span_decisions (15 min)
4. Update p70_render to check span_decisions (15 min)
5. Run tests - should still pass (5 min)
6. Remove hardcoded exceptions (10 min)
7. Run tests again (5 min)

**Total: ~1 hour for minimal viable refactor**
