"""
Exa-MA Harvest - Tools for harvesting publications and deliverables.

This package provides CLI tools to:
- Harvest publications from HAL (Hyper Articles en Ligne)
- Harvest deliverable releases from GitHub
- Generate AsciiDoc output for the Exa-MA website
"""

__version__ = "1.0.0"

from .hal import fetch_publications, output_asciidoc as hal_to_asciidoc
from .releases import fetch_all_deliverables, load_config

__all__ = [
    "fetch_publications",
    "hal_to_asciidoc",
    "fetch_all_deliverables",
    "load_config",
]
