"""
Template Renderer — Deterministic rendering from IR.

Uses templates to produce neutral text from IR structures.
This is the safest rendering option - fully deterministic.
"""

from typing import Optional

from nnrt.ir.schema_v0_1 import TransformResult


class TemplateRenderer:
    """
    Template-based renderer.
    
    Produces neutral text by applying templates to IR structures.
    Fully deterministic - same IR always produces same output.
    """

    def render(self, result: TransformResult) -> str:
        """
        Render IR to neutral text.
        
        Args:
            result: The TransformResult containing IR
            
        Returns:
            Rendered neutral text
        """
        # Stub: just concatenate segment texts
        if not result.segments:
            return ""

        return " ".join(seg.text for seg in result.segments)

    def render_with_annotations(self, result: TransformResult) -> str:
        """
        Render IR with inline annotations.
        
        Useful for debugging and review.
        """
        if not result.segments:
            return ""

        lines: list[str] = []
        for seg in result.segments:
            lines.append(f"[{seg.id}] {seg.text}")

        return "\n".join(lines)
