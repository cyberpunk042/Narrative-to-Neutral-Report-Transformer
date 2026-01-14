"""
IR Serialization — JSON import/export for IR artifacts.
"""

import json
from pathlib import Path
from typing import Union

from nnrt.ir.schema_v0_1 import TransformResult


def to_json(result: TransformResult, indent: int = 2) -> str:
    """Serialize a TransformResult to JSON string."""
    return result.model_dump_json(indent=indent)


def from_json(json_str: str) -> TransformResult:
    """Deserialize a TransformResult from JSON string."""
    return TransformResult.model_validate_json(json_str)


def save(result: TransformResult, path: Union[str, Path]) -> None:
    """Save a TransformResult to a JSON file."""
    path = Path(path)
    path.write_text(to_json(result))


def load(path: Union[str, Path]) -> TransformResult:
    """Load a TransformResult from a JSON file."""
    path = Path(path)
    return from_json(path.read_text())
