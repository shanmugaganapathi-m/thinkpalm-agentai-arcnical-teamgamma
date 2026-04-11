"""
Arcnical - Clinical architecture reviews for your codebase

A tool combining deterministic static analysis with retrieval-driven LLM review
to generate architecture feedback that a senior engineer would meaningfully agree with.

Version: 0.2.0
Schema: 2.0
"""

__version__ = "0.2.0"
__schema_version__ = "2.0"
__author__ = "Arcnical Team"

from arcnical.schema import Report, SchemaValidator

__all__ = [
    "Report",
    "SchemaValidator",
    "__version__",
    "__schema_version__",
]
