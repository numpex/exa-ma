"""
Base classes for documentation generators.

Provides abstract base class and configuration for all generators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..software.models import Application, ApplicationCollection, SoftwareCollection, SoftwarePackage


@dataclass
class GeneratorConfig:
    """Configuration for documentation generators."""

    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("pages"))
    nav_output: Path | None = None

    # Template settings
    template_dir: Path | None = None

    # Content settings
    include_eligible_only: bool = True
    generate_index: bool = True
    generate_nav: bool = True

    # Page attributes
    page_layout: str = "default"
    page_tags: list[str] = field(default_factory=lambda: ["software"])

    # Filtering
    work_packages: list[int] | None = None  # Filter by WP (None = all)
    frameworks: list[str] | None = None  # Filter by framework (None = all)


class BaseGenerator(ABC):
    """Abstract base class for documentation generators."""

    def __init__(self, config: GeneratorConfig | None = None):
        """Initialize generator with configuration.

        Args:
            config: Generator configuration (uses defaults if None)
        """
        self.config = config or GeneratorConfig()

    @abstractmethod
    def generate_framework_page(
        self,
        package: SoftwarePackage,
        applications: ApplicationCollection | None = None,
    ) -> str:
        """Generate a single framework/software page.

        Args:
            package: The software package to generate page for
            applications: Optional applications for cross-referencing

        Returns:
            Generated page content as string
        """
        pass

    @abstractmethod
    def generate_application_page(self, app: Application) -> str:
        """Generate a single application page.

        Args:
            app: The application to generate page for

        Returns:
            Generated page content as string
        """
        pass

    @abstractmethod
    def generate_frameworks_index(
        self,
        collection: SoftwareCollection,
        applications: ApplicationCollection | None = None,
    ) -> str:
        """Generate frameworks index/overview page.

        Args:
            collection: All software packages
            applications: Optional applications for cross-referencing

        Returns:
            Generated index page content
        """
        pass

    @abstractmethod
    def generate_applications_index(
        self,
        collection: ApplicationCollection,
        frameworks: SoftwareCollection | None = None,
    ) -> str:
        """Generate applications index/overview page.

        Args:
            collection: All applications
            frameworks: Optional frameworks for cross-referencing

        Returns:
            Generated index page content
        """
        pass

    @abstractmethod
    def generate_nav(
        self,
        frameworks: SoftwareCollection | None = None,
        applications: ApplicationCollection | None = None,
    ) -> str:
        """Generate navigation file.

        Args:
            frameworks: Software packages for navigation
            applications: Applications for navigation

        Returns:
            Generated navigation content
        """
        pass

    def write_framework_pages(
        self,
        collection: SoftwareCollection,
        output_dir: Path | None = None,
        applications: ApplicationCollection | None = None,
    ) -> list[Path]:
        """Generate and write all framework pages.

        Args:
            collection: Software collection
            output_dir: Output directory (uses config default if None)
            applications: Optional applications for cross-referencing

        Returns:
            List of written file paths
        """
        output_dir = output_dir or self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        packages = (
            collection.eligible_packages
            if self.config.include_eligible_only
            else collection.packages
        )

        written = []
        for package in packages:
            content = self.generate_framework_page(package, applications)
            filename = f"{package.slug}.adoc"
            filepath = output_dir / filename
            filepath.write_text(content)
            written.append(filepath)
            print(f"  Generated: {filepath}")

        return written

    def write_application_pages(
        self,
        collection: ApplicationCollection,
        output_dir: Path | None = None,
    ) -> list[Path]:
        """Generate and write all application pages.

        Args:
            collection: Application collection
            output_dir: Output directory (uses config default if None)

        Returns:
            List of written file paths
        """
        output_dir = output_dir or self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        applications = (
            collection.eligible_applications
            if self.config.include_eligible_only
            else collection.applications
        )

        written = []
        for app in applications:
            content = self.generate_application_page(app)
            filename = f"{app.slug}.adoc"
            filepath = output_dir / filename
            filepath.write_text(content)
            written.append(filepath)
            print(f"  Generated: {filepath}")

        return written

    def write_all(
        self,
        frameworks: SoftwareCollection,
        applications: ApplicationCollection,
        output_dir: Path | None = None,
    ) -> dict[str, list[Path]]:
        """Generate and write all pages including index and nav.

        Args:
            frameworks: Software/frameworks collection
            applications: Applications collection
            output_dir: Base output directory

        Returns:
            Dictionary with 'frameworks', 'applications', 'index', 'nav' keys
        """
        output_dir = output_dir or self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        result: dict[str, list[Path]] = {
            "frameworks": [],
            "applications": [],
            "index": [],
            "nav": [],
        }

        # Generate framework pages (with cross-referencing to applications)
        frameworks_dir = output_dir / "frameworks"
        print(f"\nGenerating framework pages to {frameworks_dir}/")
        result["frameworks"] = self.write_framework_pages(frameworks, frameworks_dir, applications)

        # Generate application pages
        apps_dir = output_dir / "applications"
        print(f"\nGenerating application pages to {apps_dir}/")
        result["applications"] = self.write_application_pages(applications, apps_dir)

        # Generate index pages
        if self.config.generate_index:
            print(f"\nGenerating index pages...")

            # Frameworks index
            frameworks_index = self.generate_frameworks_index(frameworks, applications)
            frameworks_index_path = output_dir / "frameworks.adoc"
            frameworks_index_path.write_text(frameworks_index)
            result["index"].append(frameworks_index_path)
            print(f"  Generated: {frameworks_index_path}")

            # Applications index
            apps_index = self.generate_applications_index(applications, frameworks)
            apps_index_path = output_dir / "applications.adoc"
            apps_index_path.write_text(apps_index)
            result["index"].append(apps_index_path)
            print(f"  Generated: {apps_index_path}")

        # Generate nav
        if self.config.generate_nav:
            print(f"\nGenerating navigation...")
            nav_content = self.generate_nav(frameworks, applications)
            nav_path = self.config.nav_output or (output_dir / "nav.adoc")
            nav_path.write_text(nav_content)
            result["nav"].append(nav_path)
            print(f"  Generated: {nav_path}")

        return result
