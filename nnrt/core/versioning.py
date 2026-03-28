"""
nnrt.core.versioning — Version constants and IR compatibility helpers.

Exposes two version constants drawn from the top-level ``nnrt`` package:

- ``PACKAGE_VERSION`` — the semantic version of the installed ``nnrt`` package
  (e.g. ``"0.3.0"``).
- ``IR_VERSION`` — the version of the Intermediate Representation schema in use
  (e.g. ``"0.1.0"``). IR versions are defined in ``nnrt.ir.schema_v0_1``.

Provides a single compatibility helper:

- ``check_ir_compatibility(ir_version)`` — returns ``True`` when the supplied
  IR version string shares the same *major.minor* as the current ``IR_VERSION``.
  Patch-level differences are tolerated; major or minor mismatches are not.

Typical use-case: validating serialised ``TransformResult`` payloads loaded
from disk or received over the wire before attempting to deserialise them with
the current schema.
"""

from nnrt import __ir_version__, __version__

PACKAGE_VERSION = __version__
IR_VERSION = __ir_version__


def check_ir_compatibility(ir_version: str) -> bool:
    """
    Check if an IR version is compatible with this package.
    
    Currently requires exact match on major.minor.
    """
    current_parts = IR_VERSION.split(".")
    check_parts = ir_version.split(".")

    # Major and minor must match
    return current_parts[0] == check_parts[0] and current_parts[1] == check_parts[1]
