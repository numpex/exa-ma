"""
Configuration loading for software harvesting.

Supports YAML config files for controlling which frameworks/applications to include.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FrameworkConfig:
    """Configuration for a single framework."""

    slug: str
    enabled: bool = True
    custom_name: str | None = None
    custom_description: str | None = None
    priority: int = 0  # Higher priority = shown first


@dataclass
class ApplicationConfig:
    """Configuration for a single application."""

    slug: str
    enabled: bool = True
    custom_name: str | None = None
    priority: int = 0


@dataclass
class GenerationConfig:
    """Full generation configuration."""

    # Framework settings
    frameworks: dict[str, FrameworkConfig] = field(default_factory=dict)
    frameworks_default_enabled: bool = True
    frameworks_include_only: list[str] | None = None
    frameworks_exclude: list[str] = field(default_factory=list)

    # Application settings
    applications: dict[str, ApplicationConfig] = field(default_factory=dict)
    applications_default_enabled: bool = True
    applications_include_only: list[str] | None = None
    applications_exclude: list[str] = field(default_factory=list)

    # Filtering
    work_packages: list[int] | None = None  # Filter by WP (None = all)
    eligible_only: bool = True

    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("pages"))
    generate_index: bool = True
    generate_nav: bool = True

    @classmethod
    def from_yaml(cls, path: Path | str) -> "GenerationConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML config file

        Returns:
            GenerationConfig instance
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationConfig":
        """Create config from dictionary."""
        config = cls()

        # Framework settings
        fw_data = data.get("frameworks", {})
        config.frameworks_default_enabled = fw_data.get("default_enabled", True)
        config.frameworks_include_only = fw_data.get("include_only")
        config.frameworks_exclude = fw_data.get("exclude", [])

        # Parse individual framework configs
        for slug, fw_cfg in fw_data.get("items", {}).items():
            if isinstance(fw_cfg, bool):
                config.frameworks[slug] = FrameworkConfig(slug=slug, enabled=fw_cfg)
            elif isinstance(fw_cfg, dict):
                config.frameworks[slug] = FrameworkConfig(
                    slug=slug,
                    enabled=fw_cfg.get("enabled", True),
                    custom_name=fw_cfg.get("name"),
                    custom_description=fw_cfg.get("description"),
                    priority=fw_cfg.get("priority", 0),
                )

        # Application settings
        app_data = data.get("applications", {})
        config.applications_default_enabled = app_data.get("default_enabled", True)
        config.applications_include_only = app_data.get("include_only")
        config.applications_exclude = app_data.get("exclude", [])

        # Parse individual application configs
        for slug, app_cfg in app_data.get("items", {}).items():
            if isinstance(app_cfg, bool):
                config.applications[slug] = ApplicationConfig(slug=slug, enabled=app_cfg)
            elif isinstance(app_cfg, dict):
                config.applications[slug] = ApplicationConfig(
                    slug=slug,
                    enabled=app_cfg.get("enabled", True),
                    custom_name=app_cfg.get("name"),
                    priority=app_cfg.get("priority", 0),
                )

        # Filtering
        filter_data = data.get("filter", {})
        config.work_packages = filter_data.get("work_packages")
        config.eligible_only = filter_data.get("eligible_only", True)

        # Output settings
        output_data = data.get("output", {})
        if "dir" in output_data:
            config.output_dir = Path(output_data["dir"])
        config.generate_index = output_data.get("generate_index", True)
        config.generate_nav = output_data.get("generate_nav", True)

        return config

    def is_framework_enabled(self, slug: str) -> bool:
        """Check if a framework should be included."""
        # Check explicit include_only list
        if self.frameworks_include_only is not None:
            return slug in self.frameworks_include_only

        # Check exclude list
        if slug in self.frameworks_exclude:
            return False

        # Check individual config
        if slug in self.frameworks:
            return self.frameworks[slug].enabled

        # Default
        return self.frameworks_default_enabled

    def is_application_enabled(self, slug: str) -> bool:
        """Check if an application should be included."""
        # Check explicit include_only list
        if self.applications_include_only is not None:
            return slug in self.applications_include_only

        # Check exclude list
        if slug in self.applications_exclude:
            return False

        # Check individual config
        if slug in self.applications:
            return self.applications[slug].enabled

        # Default
        return self.applications_default_enabled

    def get_framework_name(self, slug: str, default: str) -> str:
        """Get display name for framework (custom or default)."""
        if slug in self.frameworks and self.frameworks[slug].custom_name:
            return self.frameworks[slug].custom_name
        return default

    def get_application_name(self, slug: str, default: str) -> str:
        """Get display name for application (custom or default)."""
        if slug in self.applications and self.applications[slug].custom_name:
            return self.applications[slug].custom_name
        return default


# Default config template for users
DEFAULT_CONFIG_TEMPLATE = """# Exa-MA Software Generation Configuration
# This file controls which frameworks and applications are included in generated docs.

frameworks:
  # Set to false to exclude frameworks by default (whitelist mode)
  default_enabled: true

  # Only include these frameworks (if set, ignores default_enabled)
  # include_only:
  #   - feelpp
  #   - freefempp
  #   - hpddm

  # Exclude these frameworks
  exclude: []
    # - some-framework

  # Per-framework settings
  items:
    feelpp:
      enabled: true
      priority: 10  # Higher = shown first
    freefempp:
      enabled: true
      priority: 9
    hpddm:
      enabled: true
      priority: 8
    arcane:
      enabled: true
    cgal:
      enabled: true
    composyx:
      enabled: true
    hawen:
      enabled: true
    mahyco:
      enabled: true
    samurai:
      enabled: true
    scimba:
      enabled: true
    trust_platform:
      enabled: true
    uranie:
      enabled: true

applications:
  default_enabled: true
  exclude: []
  items: {}

filter:
  # Only include items from specific work packages
  # work_packages: [1, 2, 3]
  eligible_only: true

output:
  dir: pages
  generate_index: true
  generate_nav: true
"""


def create_default_config(path: Path | str) -> Path:
    """Create a default configuration file.

    Args:
        path: Path to write config file

    Returns:
        Path to created file
    """
    path = Path(path)
    path.write_text(DEFAULT_CONFIG_TEMPLATE)
    return path
