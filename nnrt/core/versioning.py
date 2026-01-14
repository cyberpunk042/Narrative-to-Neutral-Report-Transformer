"""
Versioning — Version constants and compatibility checks.
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
