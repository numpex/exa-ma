"""
AsciiDoc generator for Exa-MA documentation.

Generates Antora-compatible AsciiDoc pages from software and application metadata.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .base import BaseGenerator, GeneratorConfig

if TYPE_CHECKING:
    from ..software.models import Application, ApplicationCollection, SoftwareCollection, SoftwarePackage


class AsciidocGenerator(BaseGenerator):
    """Generate AsciiDoc pages using Jinja2 templates."""

    # Default template directory (relative to this file)
    DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"

    def __init__(self, config: GeneratorConfig | None = None):
        """Initialize AsciiDoc generator.

        Args:
            config: Generator configuration
        """
        super().__init__(config)

        # Setup Jinja2 environment
        template_dir = self.config.template_dir or self.DEFAULT_TEMPLATE_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["prepend"] = lambda s, prefix: f"{prefix}{s}" if s else ""
        self.env.filters["format_date"] = self._format_date

    @staticmethod
    def _format_date(value, fmt: str = "%Y-%m-%d") -> str:
        """Format a date value, handling None and NaT."""
        if value is None:
            return "N/A"
        # Check for pandas NaT
        try:
            import pandas as pd
            if pd.isna(value):
                return "N/A"
        except (ImportError, TypeError):
            pass
        # Check for datetime
        try:
            return value.strftime(fmt)
        except (AttributeError, ValueError):
            return str(value) if value else "N/A"

    def generate_framework_page(
        self,
        package: SoftwarePackage,
        applications: ApplicationCollection | None = None,
    ) -> str:
        """Generate a framework/software page.

        Args:
            package: The software package
            applications: Optional applications for cross-referencing

        Returns:
            Generated AsciiDoc content
        """
        template = self.env.get_template("framework.adoc.j2")

        # Find applications that use this framework
        used_by = []
        if applications:
            package_name_lower = package.name.lower()
            for app in applications.applications:
                for fw in app.frameworks:
                    if fw.lower() == package_name_lower or package_name_lower in fw.lower():
                        used_by.append(app)
                        break

        return template.render(package=package, used_by_applications=used_by)

    def generate_application_page(self, app: Application) -> str:
        """Generate an application page.

        Args:
            app: The application

        Returns:
            Generated AsciiDoc content
        """
        template = self.env.get_template("application.adoc.j2")
        return template.render(app=app)

    def _compute_framework_stats(self, collection: SoftwareCollection) -> dict:
        """Compute statistics for frameworks."""
        packages = collection.packages

        return {
            "total": len(packages),
            "eligible": len(collection.eligible_packages),
            "with_spack": sum(
                1 for p in packages
                if p.packaging and p.packaging.spack_available
            ),
            "with_guix": sum(
                1 for p in packages
                if p.packaging and p.packaging.guix_available
            ),
            "with_ci": sum(1 for p in packages if p.has_ci),
            "with_unit_tests": sum(1 for p in packages if p.has_unit_tests),
            "with_floss": sum(1 for p in packages if p.has_floss_license),
        }

    def _group_frameworks_by_wp(
        self, packages: list[SoftwarePackage]
    ) -> dict[int, list[SoftwarePackage]]:
        """Group frameworks by work package.

        Args:
            packages: List of packages to group (should be pre-filtered)
        """
        by_wp: dict[int, list[SoftwarePackage]] = defaultdict(list)

        for pkg in packages:
            for wp in pkg.work_packages:
                by_wp[wp.wp_number].append(pkg)

        return dict(sorted(by_wp.items()))

    def _compute_framework_usage(
        self,
        applications: ApplicationCollection,
    ) -> dict[str, list[Application]]:
        """Compute which applications use which frameworks."""
        usage: dict[str, list[Application]] = defaultdict(list)

        for app in applications.applications:
            for framework in app.frameworks:
                usage[framework].append(app)

        return dict(sorted(usage.items()))

    def generate_frameworks_index(
        self,
        collection: SoftwareCollection,
        applications: ApplicationCollection | None = None,
    ) -> str:
        """Generate frameworks index page.

        Args:
            collection: Software collection
            applications: Optional applications for cross-referencing

        Returns:
            Generated AsciiDoc content
        """
        template = self.env.get_template("frameworks_index.adoc.j2")

        packages = (
            collection.eligible_packages
            if self.config.include_eligible_only
            else collection.packages
        )

        # Build framework name to package mapping for cross-referencing
        framework_name_map = {pkg.name.lower(): pkg for pkg in packages}

        # Compute which applications use which frameworks (with package references)
        framework_usage = {}
        if applications:
            # Use eligible applications only when configured
            app_list = (
                applications.eligible_applications
                if self.config.include_eligible_only
                else applications.applications
            )
            for app in app_list:
                for fw_name in app.frameworks:
                    # Try to find matching package
                    fw_lower = fw_name.lower()
                    pkg = framework_name_map.get(fw_lower)
                    if not pkg:
                        # Try partial matching
                        for name, p in framework_name_map.items():
                            if fw_lower in name or name in fw_lower:
                                pkg = p
                                break

                    if pkg:
                        if pkg.slug not in framework_usage:
                            framework_usage[pkg.slug] = {"package": pkg, "apps": []}
                        framework_usage[pkg.slug]["apps"].append(app)

        context = {
            "packages": packages,
            "stats": self._compute_framework_stats(collection),
            "by_work_package": self._group_frameworks_by_wp(packages),
            "applications": applications,
            "framework_usage": framework_usage,
        }

        return template.render(**context)

    def _compute_application_stats(self, collection: ApplicationCollection) -> dict:
        """Compute statistics for applications."""
        apps = collection.applications

        return {
            "total": len(apps),
            "benchmark_ready": len(collection.benchmark_ready),
            "mini_apps": sum(
                1 for a in apps
                if a.application_type.value == "mini-app"
            ),
            "extended_mini_apps": sum(
                1 for a in apps
                if a.application_type.value == "extended-mini-app"
            ),
            "demonstrators": sum(
                1 for a in apps
                if a.application_type.value == "demonstrator"
            ),
        }

    def _group_applications_by_type(
        self, applications: list[Application]
    ) -> dict[str, list[Application]]:
        """Group applications by type."""
        by_type: dict[str, list[Application]] = defaultdict(list)

        for app in applications:
            by_type[app.application_type.value].append(app)

        return dict(sorted(by_type.items()))

    def _group_applications_by_framework(
        self, applications: list[Application]
    ) -> dict[str, list[Application]]:
        """Group applications by framework."""
        by_framework: dict[str, list[Application]] = defaultdict(list)

        for app in applications:
            for framework in app.frameworks:
                by_framework[framework].append(app)

        return dict(sorted(by_framework.items()))

    def generate_applications_index(
        self,
        collection: ApplicationCollection,
        frameworks: SoftwareCollection | None = None,
    ) -> str:
        """Generate applications index page.

        Args:
            collection: Application collection
            frameworks: Optional frameworks for cross-referencing

        Returns:
            Generated AsciiDoc content
        """
        template = self.env.get_template("applications_index.adoc.j2")

        applications = (
            collection.eligible_applications
            if self.config.include_eligible_only
            else collection.applications
        )

        context = {
            "applications": applications,
            "stats": self._compute_application_stats(collection),
            "by_type": self._group_applications_by_type(applications),
            "by_framework": self._group_applications_by_framework(applications),
            "frameworks": frameworks,
        }

        return template.render(**context)

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
        template = self.env.get_template("nav.adoc.j2")

        framework_list = []
        if frameworks:
            framework_list = (
                frameworks.eligible_packages
                if self.config.include_eligible_only
                else frameworks.packages
            )

        app_list = []
        if applications:
            app_list = (
                applications.eligible_applications
                if self.config.include_eligible_only
                else applications.applications
            )

        return template.render(
            frameworks=framework_list,
            applications=app_list,
        )
