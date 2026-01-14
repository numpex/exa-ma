"""
Documentation generators for Exa-MA.

This package provides generators to create documentation pages from
software and application metadata in various formats (AsciiDoc, Markdown).
"""

from .asciidoc import AsciidocGenerator
from .base import BaseGenerator, GeneratorConfig

__all__ = [
    "AsciidocGenerator",
    "BaseGenerator",
    "GeneratorConfig",
]
