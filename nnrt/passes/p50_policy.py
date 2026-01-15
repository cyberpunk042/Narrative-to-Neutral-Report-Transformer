"""
Pass 50 — Policy Evaluation

Evaluates policy rules against the transformation context.
Rules are loaded from YAML configuration files.

This pass:
- Finds all rule matches across segments
- Records policy decisions for traceability
- Does NOT modify content (p70_render does that)
- May flag content for refusal
"""

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import DiagnosticLevel
from nnrt.policy.engine import PolicyEngine, get_policy_engine

PASS_NAME = "p50_policy"
log = get_pass_logger(PASS_NAME)


def evaluate_policy(ctx: TransformContext) -> TransformContext:
    """
    Evaluate policy rules against segments.
    
    This pass:
    - Loads the configured policy ruleset
    - Finds matches in each segment
    - Records policy decisions
    - Adds diagnostics for flagged content
    """
    # Get the policy engine
    engine = get_policy_engine()
    
    log.verbose("starting_evaluation", 
        segments=len(ctx.segments),
        rules_loaded=len(engine.ruleset.rules) if engine.ruleset else 0,
    )
    
    # Evaluate each segment
    total_matches = 0
    refusal_count = 0
    
    for segment in ctx.segments:
        matches = engine.find_matches(segment.text)
        total_matches += len(matches)
        
        if matches:
            log.debug("segment_matches", 
                segment_id=segment.id, 
                match_count=len(matches),
            )
        
        # Record decisions
        for match in matches:
            decision = engine._create_decision(match)
            decision.affected_ids = [segment.id]
            ctx.policy_decisions.append(decision)
            
            # Log each match
            log.verbose("rule_matched",
                rule_id=match.rule.id,
                action=match.rule.action.value,
                matched_text=match.matched_text[:30],
                segment_id=segment.id,
            )
            
            # Add diagnostic if rule specifies one
            if match.rule.diagnostic:
                ctx.add_diagnostic(
                    level=match.rule.diagnostic.level,
                    code=match.rule.diagnostic.code,
                    message=f"{match.rule.diagnostic.message}: '{match.matched_text}'",
                    source=PASS_NAME,
                    affected_ids=[segment.id],
                )
            elif engine.ruleset.settings.always_diagnose:
                # Add info diagnostic for all matches
                ctx.add_diagnostic(
                    level="info",
                    code=f"POLICY_{match.rule.action.value.upper()}",
                    message=f"{match.rule.description}: '{match.matched_text}'",
                    source=PASS_NAME,
                    affected_ids=[segment.id],
                )
        
        # Check for refusal
        if engine.should_refuse(matches):
            refusal_count += 1
            log.warning("segment_refused",
                segment_id=segment.id,
                text_preview=segment.text[:50],
            )
            ctx.add_diagnostic(
                level="error",
                code="TRANSFORMATION_REFUSED",
                message=f"Segment cannot be transformed: {segment.text[:50]}...",
                source=PASS_NAME,
                affected_ids=[segment.id],
            )
    
    log.info("evaluated",
        total_matches=total_matches,
        decisions=len(ctx.policy_decisions),
        refusals=refusal_count,
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="evaluated_policy",
        after=f"{total_matches} matches, {len(ctx.policy_decisions)} decisions",
    )
    
    return ctx

