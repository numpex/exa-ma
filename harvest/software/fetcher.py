"""
Data fetchers for software and application metadata.

Supports fetching from:
- Local Excel files (.xlsx)
- Google Sheets (via API or public export URL)
- Unified exama.yaml configuration
"""

from __future__ import annotations

import io
import math
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    Application,
    ApplicationCollection,
    ApplicationStatus,
    ApplicationType,
    BenchmarkStatus,
    PackagingInfo,
    SoftwareCollection,
    SoftwarePackage,
    WorkPackageInfo,
)

# Import unified config (conditional to avoid circular imports)
try:
    from ..config import ExaMAConfig, load_config as load_exama_config
    HAS_UNIFIED_CONFIG = True
except ImportError:
    HAS_UNIFIED_CONFIG = False

# Default unified config path
DEFAULT_UNIFIED_CONFIG = Path(__file__).parent.parent.parent / "exama.yaml"


def is_nan(value: Any) -> bool:
    """Check if value is NaN or empty."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def clean_string(value: Any) -> str | None:
    """Clean and return string value, or None if empty."""
    if is_nan(value):
        return None
    return str(value).strip()


def parse_bool(value: Any) -> bool:
    """Parse various boolean representations."""
    if is_nan(value):
        return False
    if isinstance(value, bool):
        return value
    str_val = str(value).lower().strip()
    return str_val in ("true", "yes", "1", "x", "available")


class SoftwareDataSource(ABC):
    """Abstract base class for software data sources."""

    @abstractmethod
    def fetch(self) -> SoftwareCollection:
        """Fetch software data and return a collection."""
        pass

    @abstractmethod
    def fetch_packaging(self) -> dict[str, PackagingInfo]:
        """Fetch packaging info, keyed by software name."""
        pass


class ExcelFetcher(SoftwareDataSource):
    """Fetch software and application data from Excel files."""

    # Column mappings from Excel to model fields (Software/Frameworks sheet)
    COLUMN_MAP = {
        "Name": "name",
        "Description": "description",
        "Partner": "partner",
        "Consortium": "consortium",
        "Emails": "emails",
        "Compte Github": "github_account",
        "Repository": "repository",
        "License": "license",
        "Interfaces": "interfaces",
        "Docs": "docs_url",
        "Channels": "channels",
        "Training": "training_available",
        "Training URL": "training_url",
        "Languages": "languages",
        "Parallelism": "parallelism",
        "Data": "data_formats",
        "Resilience": "resilience",
        "Bottlenecks": "bottlenecks",
        "DevOps": "devops",
        "API": "api_info",
        "Metadata": "metadata_info",
        "Benchmarked": "benchmark_status",
        "Comments": "comments",
    }

    PACKAGING_COLUMN_MAP = {
        "Software Name": "software_name",
        "Version": "version",
        "Spack Available": "spack_available",
        "Spack Timeline": "spack_timeline",
        "Spack Info Source": "spack_url",
        "Guix-HPC Available": "guix_available",
        "Guix-HPC Timeline": "guix_timeline",
        "Guix-HPC Info Source": "guix_url",
        "PETSc packaging available": "petsc_available",
        "PETSc-Packaging Timeline": "petsc_timeline",
        "PETSC package info source": "petsc_url",
        "Docker Available": "docker_available",
        "Docker Timeline": "docker_timeline",
        "Docker Info Source": "docker_url",
        "Apptainer Available": "apptainer_available",
        "Apptainer Timeline": "apptainer_timeline",
        "Apptainer Info Source": "apptainer_url",
        "Notes": "notes",
        "Last Updated": "last_updated",
    }

    # Column mappings for Applications sheet
    APPLICATION_COLUMN_MAP = {
        "id": "id",
        "name": "name",
        "Partners": "partners",
        "PC": "pc",
        "Responsible (Permanent)": "responsible",
        "WP7 Engineer": "wp7_engineer",
        "work_package": "work_packages",
        "application_type": "application_type",
        "purpose": "purpose",
        "Method-Algorithm WP1": "methods_wp1",
        "Method-Algorithm WP2": "methods_wp2",
        "Method-Algorithm WP3": "methods_wp3",
        "Method-Algorithm WP4": "methods_wp4",
        "Method-Algorithm WP5": "methods_wp5",
        "Method-Algorithm WP6": "methods_wp6",
        "WP7": "wp7_topics",
        "inputs": "inputs",
        "outputs": "outputs",
        "metrics": "metrics",
        "status": "status",
        "Benchmark scope": "benchmark_scope",
        "Framework": "frameworks",
        "parallel_framework": "parallel_frameworks",
        "spec_due": "spec_due",
        "proto_due": "proto_due",
        "repo_url": "repo_url",
        "tex_url": "tex_url",
        "notes": "notes",
    }

    def __init__(
        self,
        file_path: str | Path | None = None,
        software_sheet: str = "Frameworks",  # Updated: was "Software"
        packaging_sheet: str = "Packaging",
        applications_sheet: str = "Applications",
    ):
        """Initialize Excel fetcher.

        Args:
            file_path: Path to the Excel file (optional for Google Sheets mode)
            software_sheet: Name of the main software/frameworks sheet
            packaging_sheet: Name of the packaging info sheet
            applications_sheet: Name of the applications sheet
        """
        self.file_path = Path(file_path) if file_path else None
        self.software_sheet = software_sheet
        self.packaging_sheet = packaging_sheet
        self.applications_sheet = applications_sheet

        if self.file_path and not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")

    def _load_dataframe(self, sheet_name: str):
        """Load a sheet as a pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for Excel support. "
                "Install with: pip install pandas openpyxl"
            )

        return pd.read_excel(self.file_path, sheet_name=sheet_name)

    def _parse_software_row(self, row: dict, packaging: dict[str, PackagingInfo]) -> SoftwarePackage:
        """Parse a single row into a SoftwarePackage."""
        # Build kwargs from column mapping
        kwargs: dict[str, Any] = {}

        for excel_col, model_field in self.COLUMN_MAP.items():
            value = row.get(excel_col)

            if model_field == "benchmark_status":
                kwargs[model_field] = BenchmarkStatus.from_string(clean_string(value))
            elif model_field == "training_available":
                kwargs[model_field] = parse_bool(value)
            elif model_field in ("emails", "languages", "parallelism", "data_formats",
                                  "devops", "channels", "bottlenecks"):
                # These are handled by the validator in the model
                kwargs[model_field] = value
            else:
                kwargs[model_field] = clean_string(value)

        # Parse work packages
        work_packages = []
        for wp_num in range(1, 8):
            wp_info = WorkPackageInfo.from_excel_row(row, wp_num)
            if wp_info:
                work_packages.append(wp_info)
        kwargs["work_packages"] = work_packages

        # Link packaging info
        name = kwargs.get("name", "")
        if name and name in packaging:
            kwargs["packaging"] = packaging[name]

        return SoftwarePackage(**kwargs)

    def _parse_packaging_row(self, row: dict) -> PackagingInfo | None:
        """Parse a packaging row into PackagingInfo."""
        software_name = clean_string(row.get("Software Name"))
        if not software_name:
            return None

        kwargs: dict[str, Any] = {"software_name": software_name}

        for excel_col, model_field in self.PACKAGING_COLUMN_MAP.items():
            if model_field == "software_name":
                continue

            value = row.get(excel_col)

            if model_field.endswith("_available"):
                kwargs[model_field] = parse_bool(value)
            elif model_field == "last_updated":
                if not is_nan(value):
                    if isinstance(value, datetime):
                        kwargs[model_field] = value
                    else:
                        try:
                            kwargs[model_field] = datetime.fromisoformat(str(value))
                        except (ValueError, TypeError):
                            pass
            else:
                kwargs[model_field] = clean_string(value)

        return PackagingInfo(**kwargs)

    def fetch_packaging(self) -> dict[str, PackagingInfo]:
        """Fetch all packaging info, keyed by software name."""
        df = self._load_dataframe(self.packaging_sheet)
        packaging = {}

        for _, row in df.iterrows():
            info = self._parse_packaging_row(row.to_dict())
            if info:
                packaging[info.software_name] = info

        return packaging

    def fetch(self) -> SoftwareCollection:
        """Fetch all software data."""
        # First fetch packaging info
        packaging = self.fetch_packaging()

        # Then fetch software data
        df = self._load_dataframe(self.software_sheet)
        packages = []

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            name = clean_string(row_dict.get("Name"))
            if not name:
                continue

            try:
                package = self._parse_software_row(row_dict, packaging)
                packages.append(package)
            except Exception as e:
                print(f"Warning: Failed to parse software '{name}': {e}")
                continue

        return SoftwareCollection(
            packages=packages,
            source_file=str(self.file_path) if self.file_path else "unknown",
            fetched_at=datetime.now(),
        )

    def _parse_application_row(self, row: dict) -> Application:
        """Parse a single row into an Application."""
        kwargs: dict[str, Any] = {}

        for excel_col, model_field in self.APPLICATION_COLUMN_MAP.items():
            value = row.get(excel_col)

            if model_field == "application_type":
                kwargs[model_field] = ApplicationType.from_string(clean_string(value))
            elif model_field == "status":
                kwargs[model_field] = ApplicationStatus.from_string(clean_string(value))
            elif model_field in ("spec_due", "proto_due"):
                if not is_nan(value):
                    if isinstance(value, datetime):
                        kwargs[model_field] = value
                    else:
                        try:
                            kwargs[model_field] = datetime.fromisoformat(str(value).split()[0])
                        except (ValueError, TypeError):
                            pass
            elif model_field in (
                "partners", "pc", "responsible", "work_packages",
                "methods_wp1", "methods_wp2", "methods_wp3", "methods_wp4",
                "methods_wp5", "methods_wp6", "wp7_topics",
                "inputs", "outputs", "metrics", "benchmark_scope",
                "frameworks", "parallel_frameworks"
            ):
                # These are handled by the validator in the model
                kwargs[model_field] = value
            else:
                kwargs[model_field] = clean_string(value)

        return Application(**kwargs)

    def fetch_applications(self) -> ApplicationCollection:
        """Fetch all application data."""
        if not self.file_path:
            raise ValueError("file_path is required for Excel fetching")

        df = self._load_dataframe(self.applications_sheet)
        applications = []

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            app_id = clean_string(row_dict.get("id"))
            if not app_id:
                continue

            try:
                app = self._parse_application_row(row_dict)
                applications.append(app)
            except Exception as e:
                print(f"Warning: Failed to parse application '{app_id}': {e}")
                continue

        return ApplicationCollection(
            applications=applications,
            source_file=str(self.file_path),
            fetched_at=datetime.now(),
        )


class GoogleSheetsFetcher(SoftwareDataSource):
    """Fetch software and application data from Google Sheets.

    Fetches the spreadsheet as XLSX to access all sheets by name.
    """

    # Google Sheets export URL format
    EXPORT_URL_TEMPLATE = (
        "https://docs.google.com/spreadsheets/d/{sheet_id}/export"
        "?format={format}"
    )

    def __init__(
        self,
        sheet_id: str,
        software_sheet: str = "Frameworks",
        packaging_sheet: str = "Packaging",
        applications_sheet: str = "Applications",
    ):
        """Initialize Google Sheets fetcher.

        Args:
            sheet_id: The Google Sheets document ID (from URL)
            software_sheet: Name of the software/frameworks sheet
            packaging_sheet: Name of the packaging sheet
            applications_sheet: Name of the applications sheet
        """
        self.sheet_id = sheet_id
        self.software_sheet = software_sheet
        self.packaging_sheet = packaging_sheet
        self.applications_sheet = applications_sheet
        self._excel_data: bytes | None = None

    def _fetch_excel(self) -> bytes:
        """Fetch the spreadsheet as XLSX bytes."""
        if self._excel_data is not None:
            return self._excel_data

        url = self.EXPORT_URL_TEMPLATE.format(
            sheet_id=self.sheet_id,
            format="xlsx"
        )

        try:
            response = urllib.request.urlopen(url)
            self._excel_data = response.read()
            return self._excel_data
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch Google Sheet. "
                f"Ensure the sheet is publicly accessible. Error: {e}"
            )

    def _load_sheet(self, sheet_name: str):
        """Load a specific sheet as pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required. Install with: pip install pandas")

        data = self._fetch_excel()
        return pd.read_excel(io.BytesIO(data), sheet_name=sheet_name)

    def get_sheet_names(self) -> list[str]:
        """Get list of available sheet names."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required. Install with: pip install pandas")

        data = self._fetch_excel()
        xl = pd.ExcelFile(io.BytesIO(data))
        return xl.sheet_names

    def fetch_packaging(self) -> dict[str, PackagingInfo]:
        """Fetch packaging info from Google Sheets."""
        try:
            df = self._load_sheet(self.packaging_sheet)
        except Exception:
            return {}

        excel_fetcher = ExcelFetcher()
        packaging = {}

        for _, row in df.iterrows():
            info = excel_fetcher._parse_packaging_row(row.to_dict())
            if info:
                packaging[info.software_name] = info

        return packaging

    def fetch(self) -> SoftwareCollection:
        """Fetch software/frameworks data from Google Sheets."""
        packaging = self.fetch_packaging()
        df = self._load_sheet(self.software_sheet)

        excel_fetcher = ExcelFetcher()
        packages = []

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            name = clean_string(row_dict.get("Name"))
            if not name:
                continue

            try:
                package = excel_fetcher._parse_software_row(row_dict, packaging)
                packages.append(package)
            except Exception as e:
                print(f"Warning: Failed to parse software '{name}': {e}")
                continue

        return SoftwareCollection(
            packages=packages,
            source_file=f"google-sheets:{self.sheet_id}",
            fetched_at=datetime.now(),
        )

    def fetch_applications(self) -> ApplicationCollection:
        """Fetch applications from Google Sheets."""
        df = self._load_sheet(self.applications_sheet)

        excel_fetcher = ExcelFetcher()
        applications = []

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            app_id = clean_string(row_dict.get("id"))
            if not app_id:
                continue

            try:
                app = excel_fetcher._parse_application_row(row_dict)
                applications.append(app)
            except Exception as e:
                print(f"Warning: Failed to parse application '{app_id}': {e}")
                continue

        return ApplicationCollection(
            applications=applications,
            source_file=f"google-sheets:{self.sheet_id}",
            fetched_at=datetime.now(),
        )


def create_fetcher(
    source: str,
    **kwargs,
) -> ExcelFetcher | GoogleSheetsFetcher:
    """Factory function to create the appropriate fetcher.

    Args:
        source: Either a file path or "sheets:<sheet_id>"

    Returns:
        Configured data source fetcher (ExcelFetcher or GoogleSheetsFetcher)
    """
    if source.startswith("sheets:"):
        sheet_id = source.replace("sheets:", "")
        return GoogleSheetsFetcher(sheet_id=sheet_id, **kwargs)
    else:
        return ExcelFetcher(file_path=source, **kwargs)


def create_fetcher_from_config(
    config_path: Path | str | None = None,
    **kwargs,
) -> GoogleSheetsFetcher:
    """Create a fetcher using unified exama.yaml configuration.

    Args:
        config_path: Optional path to exama.yaml config file
        **kwargs: Additional arguments passed to GoogleSheetsFetcher

    Returns:
        Configured GoogleSheetsFetcher

    Raises:
        ValueError: If unified config is not available
    """
    if not HAS_UNIFIED_CONFIG:
        raise ValueError(
            "Unified config module not available. "
            "Use create_fetcher() with explicit source."
        )

    # Try to load config
    try:
        config = load_exama_config(config_path)
    except FileNotFoundError:
        # Try default location
        if DEFAULT_UNIFIED_CONFIG.exists():
            config = load_exama_config(DEFAULT_UNIFIED_CONFIG)
        else:
            raise ValueError(
                f"No config file found. Provide config_path or create {DEFAULT_UNIFIED_CONFIG}"
            )

    software_config = config.get_software_config()

    return GoogleSheetsFetcher(
        sheet_id=software_config.sheet_id,
        software_sheet=software_config.sheets.frameworks,
        packaging_sheet=software_config.sheets.packaging,
        applications_sheet=software_config.sheets.applications,
        **kwargs,
    )
