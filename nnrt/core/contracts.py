"""
Contracts — Type definitions and interfaces for pipeline components.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from nnrt.core.context import TransformContext


class Pass(Protocol):
    """Protocol for pipeline passes."""

    def __call__(self, ctx: TransformContext) -> TransformContext:
        """Apply the pass to the context."""
        ...


class Validator(ABC):
    """Abstract base for validators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Validator name for diagnostics."""
        ...

    @abstractmethod
    def validate(self, ctx: TransformContext) -> list[str]:
        """
        Validate the context.
        
        Returns:
            List of error messages (empty if valid)
        """
        ...
