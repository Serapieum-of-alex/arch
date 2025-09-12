"""
Test Package 1

A comprehensive test package that exercises a wide range of Python language
features for static analysis and AST-based crawlers.

Exposed submodules:
- advanced: metaclasses, protocols, async patterns, descriptors.

This module intentionally contains diverse constructs: type aliases, __all__,
relative and absolute imports, module attributes, and annotations.
"""
from __future__ import annotations

# Absolute and relative imports
from typing import Final, TypeAlias

# Re-export selected names from submodules to test package-level exposure
from .advanced import Pluggable, BasePlugin, ConcretePlugin

# Public API
__all__ = [
    "Pluggable",
    "BasePlugin",
    "ConcretePlugin",
]

# Module-level constants and variables with annotations
__version__: Final[str] = "0.1.0"
DEFAULT_TIMEOUT: float = 1.5
StrList: TypeAlias = list[str]

# Simple side-effect-free lambda for coverage
_id = lambda x: x  # noqa: E731

# Optional run hook
if __name__ == "__main__":  # pragma: no cover - only for manual runs
    print(f"test-package-small v{__version__} loaded; 2 + 2 = {_id(4)}")
