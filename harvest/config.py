"""
Unified configuration loader for Exa-MA harvesting.

Provides a single configuration model that consolidates all data sources:
- HAL publications
- GitHub deliverables
- Google Sheets (software, team)
- News/events

This module uses Pydantic for validation and supports:
- Loading from exama.yaml
- Backward compatibility with existing separate config files
- CLI argument overrides
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# Default config file name
DEFAULT_CONFIG_FILE = "exama.yaml"


class ProjectConfig(BaseModel):
    """Project-level configuration."""

    name: str = "Exa-MA"
    anr_id: str = "ANR-22-EXNU-0002"


class PublicationsConfig(BaseModel):
    """HAL publications configuration."""

    type: str = "hal"
    query: str = "anrProjectReference_s:ANR-22-EXNU-0002"
    domains: list[str] = Field(default_factory=lambda: ["math", "info", "stat", "phys"])
    years: list[int] = Field(default_factory=lambda: [2023, 2024, 2025, 2026])


class DeliverableItem(BaseModel):
    """Single deliverable configuration."""

    id: str
    repo: str
    title: str
    description: str = ""
    workpackages: list[str] = Field(default_factory=list)
    featured_versions: list[str] = Field(default_factory=list)


class DeliverablesSettings(BaseModel):
    """Deliverables settings."""

    max_releases: int = 5
    include_prereleases: bool = False
    latest_only: bool = False


class DeliverablesConfig(BaseModel):
    """GitHub deliverables configuration."""

    type: str = "github"
    settings: DeliverablesSettings = Field(default_factory=DeliverablesSettings)
    items: list[DeliverableItem] = Field(default_factory=list)

    def to_legacy_format(self) -> dict[str, Any]:
        """Convert to legacy deliverables.yaml format for backward compatibility."""
        return {
            "settings": self.settings.model_dump(),
            "deliverables": [item.model_dump() for item in self.items],
        }


class SoftwareSheetsConfig(BaseModel):
    """Sheet names for software data."""

    frameworks: str = "Frameworks"
    packaging: str = "Packaging"
    applications: str = "Applications"


class SoftwareConfig(BaseModel):
    """Software (Google Sheets) configuration."""

    type: str = "google_sheets"
    sheet_id: str = "19v57jpek52nQV2V0tBBON5ivGCz7Bqf3Gw-fHroVHkA"
    sheets: SoftwareSheetsConfig = Field(default_factory=SoftwareSheetsConfig)


class TeamFilterConfig(BaseModel):
    """Team filtering options."""

    funded_only: bool = True
    active_only: bool = False


class TeamConfig(BaseModel):
    """Team (Google Sheets) configuration."""

    type: str = "google_sheets"
    sheet_id: str = "1-QuexB1IiP2O1ebNhp1OrQb6hOx8BXA5"
    sheet_name: str = "All Exa-MA"
    filter: TeamFilterConfig = Field(default_factory=TeamFilterConfig)


class PartnersConfig(BaseModel):
    """External Partners (Google Sheets) configuration."""

    type: str = "google_sheets"
    sheet_id: str = "1bigC5N-5Zg2SGfUvpyMvYQPHvrSCqY2K"
    sheet_name: str = "Overview"


class NewsEvent(BaseModel):
    """Single news/event item."""

    id: str
    type: str
    status: str
    title: str
    date: str
    end_date: str | None = None
    location: str | None = None
    icon: str = "calendar"
    description: str = ""
    url: str | None = None
    page: str | None = None
    time: str | None = None
    link_text: str | None = None  # Custom link text for URL/page


class NewsConfig(BaseModel):
    """News and events configuration."""

    type: str = "yaml"
    events: list[NewsEvent] = Field(default_factory=list)
    # Alternative: reference to external file (relative to config file)
    file: str | None = None

    def load_events_from_file(self, config_dir: Path) -> list[NewsEvent]:
        """Load events from external file if specified.

        Args:
            config_dir: Directory containing the config file

        Returns:
            List of NewsEvent objects
        """
        if not self.file:
            return self.events

        file_path = config_dir / self.file
        if not file_path.exists():
            return self.events

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        events_data = data.get("events", [])
        return [NewsEvent.model_validate(e) for e in events_data]


class OutputConfig(BaseModel):
    """Output directory configuration."""

    partials_dir: str = "docs/modules/ROOT/partials"
    software_pages_dir: str = "docs/modules/software/pages"


class SourcesConfig(BaseModel):
    """All data sources configuration."""

    publications: PublicationsConfig = Field(default_factory=PublicationsConfig)
    deliverables: DeliverablesConfig = Field(default_factory=DeliverablesConfig)
    software: SoftwareConfig = Field(default_factory=SoftwareConfig)
    team: TeamConfig = Field(default_factory=TeamConfig)
    partners: PartnersConfig = Field(default_factory=PartnersConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)


class ExaMAConfig(BaseModel):
    """Root configuration model for Exa-MA harvest."""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    # Internal: path to config file (not serialized)
    _config_path: Path | None = None

    @classmethod
    def from_yaml(cls, path: Path | str) -> "ExaMAConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to the YAML config file

        Returns:
            ExaMAConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls.model_validate(data)
        config._config_path = path
        return config

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExaMAConfig":
        """Create config from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def load(
        cls,
        config_path: Path | str | None = None,
        search_paths: list[Path | str] | None = None,
    ) -> "ExaMAConfig":
        """Load configuration with fallback search.

        Args:
            config_path: Explicit path to config file
            search_paths: List of directories to search for exama.yaml

        Returns:
            ExaMAConfig instance (defaults if no config found)
        """
        # If explicit path given, use it
        if config_path:
            return cls.from_yaml(config_path)

        # Search for config file
        if search_paths is None:
            search_paths = [
                Path.cwd(),
                Path(__file__).parent.parent,  # exama/ directory
            ]

        for search_dir in search_paths:
            config_file = Path(search_dir) / DEFAULT_CONFIG_FILE
            if config_file.exists():
                return cls.from_yaml(config_file)

        # Return defaults if no config found
        return cls()

    def get_publications_config(self) -> PublicationsConfig:
        """Get publications configuration."""
        return self.sources.publications

    def get_deliverables_config(self) -> DeliverablesConfig:
        """Get deliverables configuration."""
        return self.sources.deliverables

    def get_software_config(self) -> SoftwareConfig:
        """Get software configuration."""
        return self.sources.software

    def get_team_config(self) -> TeamConfig:
        """Get team configuration."""
        return self.sources.team

    def get_partners_config(self) -> PartnersConfig:
        """Get partners configuration."""
        return self.sources.partners

    def get_news_config(self) -> NewsConfig:
        """Get news configuration."""
        return self.sources.news

    def get_news_events(self) -> list[NewsEvent]:
        """Get news events, loading from external file if specified.

        Returns:
            List of NewsEvent objects
        """
        news_config = self.sources.news

        # If file is specified, load from external file
        if news_config.file and self._config_path:
            config_dir = self._config_path.parent
            return news_config.load_events_from_file(config_dir)

        return news_config.events

    def get_config_dir(self) -> Path | None:
        """Get the directory containing the config file."""
        return self._config_path.parent if self._config_path else None


def load_config(config_path: Path | str | None = None) -> ExaMAConfig:
    """Convenience function to load configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        ExaMAConfig instance
    """
    return ExaMAConfig.load(config_path)


def merge_with_legacy_deliverables(
    config: ExaMAConfig,
    legacy_path: Path | str,
) -> ExaMAConfig:
    """Merge unified config with legacy deliverables.yaml.

    If the unified config has no deliverables items but a legacy
    deliverables.yaml exists, load from there.

    Args:
        config: Current ExaMAConfig
        legacy_path: Path to legacy deliverables.yaml

    Returns:
        Updated ExaMAConfig
    """
    legacy_path = Path(legacy_path)

    # Only merge if unified config has no deliverables
    if config.sources.deliverables.items:
        return config

    if not legacy_path.exists():
        return config

    with open(legacy_path, "r", encoding="utf-8") as f:
        legacy_data = yaml.safe_load(f) or {}

    # Convert legacy format to new format
    settings_data = legacy_data.get("settings", {})
    items_data = legacy_data.get("deliverables", [])

    config.sources.deliverables.settings = DeliverablesSettings.model_validate(settings_data)
    config.sources.deliverables.items = [
        DeliverableItem.model_validate(item) for item in items_data
    ]

    return config


def merge_with_legacy_news(
    config: ExaMAConfig,
    legacy_path: Path | str,
) -> ExaMAConfig:
    """Merge unified config with legacy news.yaml.

    If the unified config has no events but a legacy news.yaml exists,
    load from there.

    Args:
        config: Current ExaMAConfig
        legacy_path: Path to legacy news.yaml

    Returns:
        Updated ExaMAConfig
    """
    legacy_path = Path(legacy_path)

    # Only merge if unified config has no events
    if config.sources.news.events:
        return config

    if not legacy_path.exists():
        return config

    with open(legacy_path, "r", encoding="utf-8") as f:
        legacy_data = yaml.safe_load(f) or {}

    # Convert legacy format to new format
    events_data = legacy_data.get("events", [])
    config.sources.news.events = [
        NewsEvent.model_validate(event) for event in events_data
    ]

    return config
