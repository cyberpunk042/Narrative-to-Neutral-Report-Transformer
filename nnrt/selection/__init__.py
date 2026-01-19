"""
Selection Module — Stage 2

Provides selection layer functionality for choosing which atoms
to include in output based on selection mode.
"""

from nnrt.selection.models import SelectionMode, SelectionResult
from nnrt.selection.utils import build_selection_from_result

__all__ = ["SelectionMode", "SelectionResult", "build_selection_from_result"]

