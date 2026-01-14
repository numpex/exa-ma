"""
Software and application harvesting module for Exa-MA.

This module provides tools to:
- Fetch software and application metadata from Google Sheets or Excel files
- Evaluate software against defined criteria
- Generate documentation pages (AsciiDoc, Markdown)
"""

from .cache import CachedFetcher, SoftwareCache
from .cli import main
from .fetcher import ExcelFetcher, GoogleSheetsFetcher, SoftwareDataSource, create_fetcher
from .models import (
    Application,
    ApplicationCollection,
    ApplicationStatus,
    ApplicationType,
    PackagingInfo,
    SoftwareCollection,
    SoftwarePackage,
    WorkPackageInfo,
)

__all__ = [
    "Application",
    "ApplicationCollection",
    "ApplicationStatus",
    "ApplicationType",
    "CachedFetcher",
    "ExcelFetcher",
    "GoogleSheetsFetcher",
    "PackagingInfo",
    "SoftwareCache",
    "SoftwareCollection",
    "SoftwareDataSource",
    "SoftwarePackage",
    "WorkPackageInfo",
    "create_fetcher",
    "main",
]
