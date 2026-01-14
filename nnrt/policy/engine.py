"""
Policy Engine — Deterministic rule evaluation.

Policy rules are explicit, traceable, and deterministic.
They decide what survives into output, not the NLP models.
"""

from dataclasses import dataclass
from typing import Callable, Optional
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import PolicyAction
from nnrt.ir.schema_v0_1 import PolicyDecision


@dataclass
class PolicyRule:
    """A single policy rule."""

    id: str
    name: str
    description: str
    condition: Callable[[TransformContext], bool]
    action: PolicyAction
    reason_template: str


class PolicyEngine:
    """
    Deterministic policy rule engine.
    
    Evaluates rules against the transform context
    and produces explicit policy decisions.
    """

    def __init__(self) -> None:
        self._rules: list[PolicyRule] = []

    def register_rule(self, rule: PolicyRule) -> None:
        """Register a policy rule."""
        self._rules.append(rule)

    def evaluate(self, ctx: TransformContext) -> list[PolicyDecision]:
        """
        Evaluate all rules against context.
        
        Returns:
            List of policy decisions
        """
        decisions: list[PolicyDecision] = []

        for rule in self._rules:
            if rule.condition(ctx):
                decisions.append(
                    PolicyDecision(
                        id=str(uuid4()),
                        rule_id=rule.id,
                        action=rule.action,
                        reason=rule.reason_template,
                        affected_ids=[],  # Will be populated by passes
                    )
                )

        return decisions

    def should_refuse(self, decisions: list[PolicyDecision]) -> bool:
        """Check if any decision requires refusal."""
        return any(d.action == PolicyAction.REFUSE for d in decisions)


# Default policy engine instance
_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the default policy engine."""
    global _engine
    if _engine is None:
        _engine = PolicyEngine()
    return _engine
