"""
Exa-MA Harvest - Tools for harvesting publications, deliverables, and team data.

This package provides CLI tools to:
- Harvest publications from HAL (Hyper Articles en Ligne)
- Harvest deliverable releases from GitHub
- Harvest recruited personnel from Google Sheets
- Generate AsciiDoc output for the Exa-MA website

Configuration is managed through exama.yaml (unified) or individual config files.
"""

__version__ = "1.0.0"

from .config import (
    ExaMAConfig,
    load_config as load_exama_config,
    PublicationsConfig,
    DeliverablesConfig,
    SoftwareConfig,
    TeamConfig,
    NewsConfig,
)
from .hal import fetch_publications, output_asciidoc as hal_to_asciidoc
from .releases import fetch_all_deliverables, load_config
from .team import (
    fetch_recruited,
    fetch_recruited_with_config,
    generate_recruited_section,
    generate_team_asciidoc,
    generate_person_page,
    RecruitedPerson,
    RecruitedCollection,
    GenderStats,
    PositionType,
    Gender,
)

__all__ = [
    # Config
    "ExaMAConfig",
    "load_exama_config",
    "PublicationsConfig",
    "DeliverablesConfig",
    "SoftwareConfig",
    "TeamConfig",
    "NewsConfig",
    # HAL
    "fetch_publications",
    "hal_to_asciidoc",
    # Releases
    "fetch_all_deliverables",
    "load_config",
    # Team
    "fetch_recruited",
    "fetch_recruited_with_config",
    "generate_recruited_section",
    "generate_team_asciidoc",
    "generate_person_page",
    "RecruitedPerson",
    "RecruitedCollection",
    "GenderStats",
    "PositionType",
    "Gender",
]
