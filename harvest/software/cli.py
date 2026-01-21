"""
CLI for software and application metadata harvesting.

Provides commands to:
- Fetch software and application metadata from Excel or Google Sheets
- List software packages and applications with their criteria status
- Export data in various formats (JSON, YAML)

Supports configuration from:
- Command line arguments (highest priority)
- Unified exama.yaml config file
- Default values (fallback)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cache import CachedFetcher, SoftwareCache
from .config import GenerationConfig, create_default_config
from .fetcher import (
    ExcelFetcher,
    GoogleSheetsFetcher,
    create_fetcher,
    create_fetcher_from_config,
    HAS_UNIFIED_CONFIG,
    DEFAULT_UNIFIED_CONFIG,
)
from .models import Application, ApplicationCollection, SoftwareCollection, SoftwarePackage

# Lazy import for generators to avoid circular imports
def get_generator():
    """Lazy import of AsciidocGenerator."""
    from ..generators.asciidoc import AsciidocGenerator
    from ..generators.base import GeneratorConfig
    return AsciidocGenerator, GeneratorConfig


def format_checkmark(value: bool) -> str:
    """Format boolean as checkmark."""
    return "[x]" if value else "[ ]"


def print_package_summary(pkg: SoftwarePackage, verbose: bool = False) -> None:
    """Print a summary of a single package."""
    status = "ELIGIBLE" if pkg.is_eligible_for_page else "SKIP"
    print(f"\n{'=' * 60}")
    print(f"{pkg.name} ({status})")
    print(f"{'=' * 60}")

    if pkg.description:
        desc = pkg.description[:100] + "..." if len(pkg.description) > 100 else pkg.description
        print(f"  {desc}")

    print(f"\n  Repository:    {pkg.repository or 'N/A'}")
    print(f"  License:       {pkg.license or 'N/A'}")
    print(f"  Docs:          {pkg.docs_url or 'N/A'}")
    print(f"  Benchmark:     {pkg.benchmark_status.value if pkg.benchmark_status else 'N/A'}")

    if verbose:
        print(f"\n  Criteria:")
        print(f"    {format_checkmark(pkg.has_public_repository)} Public repository")
        print(f"    {format_checkmark(pkg.supports_pull_requests)} Supports PRs")
        print(f"    {format_checkmark(pkg.has_floss_license)} FLOSS license")
        print(f"    {format_checkmark(pkg.has_ci)} CI configured")
        print(f"    {format_checkmark(pkg.has_unit_tests)} Unit tests")
        print(f"    {format_checkmark(pkg.has_packages)} Packages exist")
        print(f"    {format_checkmark(pkg.has_benchmarking)} Benchmarking")

        if pkg.work_packages:
            print(f"\n  Work Packages:")
            for wp in pkg.work_packages:
                bench = " (benchmarked)" if wp.benchmarked else ""
                print(f"    WP{wp.wp_number}: {', '.join(wp.topics[:3])}{bench}")

        if pkg.packaging:
            print(f"\n  Packaging:")
            if pkg.packaging.spack_available:
                print(f"    Spack: {pkg.packaging.spack_url or 'available'}")
            if pkg.packaging.guix_available:
                print(f"    Guix: {pkg.packaging.guix_url or 'available'}")
            if pkg.packaging.docker_available:
                print(f"    Docker: {pkg.packaging.docker_url or 'available'}")


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch and display software data."""
    try:
        fetcher = create_fetcher(args.source)

        if args.cache:
            cache = SoftwareCache(ttl_seconds=args.cache_ttl)
            cached_fetcher = CachedFetcher(fetcher, cache)
            collection = cached_fetcher.fetch(force_refresh=args.refresh)
        else:
            collection = fetcher.fetch()

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return 1

    print(f"Fetched {len(collection.packages)} software packages")
    print(f"  Eligible for pages: {len(collection.eligible_packages)}")

    if args.list:
        for pkg in collection.packages:
            print_package_summary(pkg, verbose=args.verbose)

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List software packages."""
    try:
        fetcher = create_fetcher(args.source)
        collection = fetcher.fetch()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    packages = collection.packages

    # Apply filters
    if args.eligible_only:
        packages = [p for p in packages if p.is_eligible_for_page]

    if args.wp:
        packages = [
            p for p in packages
            if any(wp.wp_number == args.wp for wp in p.work_packages)
        ]

    # Output format
    if args.format == "json":
        data = [p.model_dump(mode="json") for p in packages]
        print(json.dumps(data, indent=2, default=str))
    elif args.format == "names":
        for pkg in packages:
            print(pkg.name)
    else:
        print(f"{'Name':<25} {'License':<20} {'Benchmark':<15} {'Eligible'}")
        print("-" * 70)
        for pkg in packages:
            status = pkg.benchmark_status.value[:12] if pkg.benchmark_status else "N/A"
            elig = "Yes" if pkg.is_eligible_for_page else "No"
            lic = (pkg.license[:17] + "...") if pkg.license and len(pkg.license) > 20 else (pkg.license or "N/A")
            print(f"{pkg.name:<25} {lic:<20} {status:<15} {elig}")

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export software data to file."""
    try:
        fetcher = create_fetcher(args.source)
        collection = fetcher.fetch()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    packages = collection.eligible_packages if args.eligible_only else collection.packages

    if args.format == "json":
        data = {
            "packages": [p.model_dump(mode="json") for p in packages],
            "source": collection.source_file,
            "fetched_at": collection.fetched_at.isoformat() if collection.fetched_at else None,
        }
        output = json.dumps(data, indent=2, default=str)
    else:
        # YAML format
        try:
            import yaml
            data = {
                "packages": [p.model_dump(mode="json") for p in packages],
                "source": collection.source_file,
            }
            output = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        except ImportError:
            print("Error: PyYAML required for YAML export", file=sys.stderr)
            return 1

    if args.output:
        Path(args.output).write_text(output)
        print(f"Exported {len(packages)} packages to {args.output}")
    else:
        print(output)

    return 0


def cmd_cache(args: argparse.Namespace) -> int:
    """Manage the software cache."""
    cache = SoftwareCache()

    if args.action == "stats":
        stats = cache.get_stats()
        print("Cache Statistics:")
        print(f"  Directory: {stats['cache_dir']}")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Valid: {stats['valid_entries']}")
        print(f"  Expired: {stats['expired_entries']}")
        print(f"  Size: {stats['total_size_bytes'] / 1024:.1f} KB")

    elif args.action == "clear":
        count = cache.clear()
        print(f"Cleared {count} cache entries")

    return 0


def print_application_summary(app: Application, verbose: bool = False) -> None:
    """Print a summary of a single application."""
    status_str = app.status.value.upper()
    print(f"\n{'=' * 60}")
    print(f"{app.name} [{app.id}] ({status_str})")
    print(f"{'=' * 60}")

    if app.purpose:
        purpose = app.purpose[:100] + "..." if len(app.purpose) > 100 else app.purpose
        print(f"  {purpose}")

    print(f"\n  Type:          {app.application_type.value}")
    print(f"  Work Packages: {', '.join(app.work_packages) or 'N/A'}")
    print(f"  Frameworks:    {', '.join(app.frameworks) or 'N/A'}")
    print(f"  Repository:    {app.repo_url or 'N/A'}")

    if verbose:
        print(f"\n  Partners: {', '.join(app.partners) or 'N/A'}")
        print(f"  Responsible: {', '.join(app.responsible) or 'N/A'}")

        if app.methods_wp1:
            print(f"\n  Methods WP1: {', '.join(app.methods_wp1[:5])}")
        if app.methods_wp2:
            print(f"  Methods WP2: {', '.join(app.methods_wp2[:5])}")
        if app.methods_wp3:
            print(f"  Methods WP3: {', '.join(app.methods_wp3[:5])}")

        if app.metrics:
            print(f"\n  Metrics: {', '.join(app.metrics)}")
        if app.benchmark_scope:
            print(f"  Benchmark Scope: {', '.join(app.benchmark_scope)}")

        if app.spec_due:
            print(f"\n  Spec Due: {app.spec_due.strftime('%Y-%m-%d')}")
        if app.proto_due:
            print(f"  Proto Due: {app.proto_due.strftime('%Y-%m-%d')}")


def cmd_applications(args: argparse.Namespace) -> int:
    """List or export applications."""
    try:
        fetcher = create_fetcher(args.source)

        # Check if fetcher supports applications
        if not hasattr(fetcher, 'fetch_applications'):
            print("Error: Data source does not support applications", file=sys.stderr)
            return 1

        collection = fetcher.fetch_applications()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    applications = collection.applications

    # Apply filters
    if args.benchmark_ready:
        applications = [a for a in applications if a.is_benchmark_ready]

    if args.framework:
        framework_lower = args.framework.lower()
        applications = [
            a for a in applications
            if any(framework_lower in f.lower() for f in a.frameworks)
        ]

    if args.wp:
        wp_filter = args.wp.upper()
        applications = [
            a for a in applications
            if any(wp_filter in w.upper() for w in a.work_packages)
        ]

    # Output format
    if args.format == "json":
        data = [a.model_dump(mode="json") for a in applications]
        print(json.dumps(data, indent=2, default=str))
    elif args.format == "names":
        for app in applications:
            print(f"{app.id}: {app.name}")
    elif args.format == "verbose":
        for app in applications:
            print_application_summary(app, verbose=True)
    else:
        # Table format
        print(f"{'ID':<25} {'Name':<20} {'Type':<18} {'Status':<15} {'WPs'}")
        print("-" * 90)
        for app in applications:
            app_type = app.application_type.value[:16]
            status = app.status.value[:13]
            wps = ', '.join(app.work_packages)[:15]
            name = app.name[:18] + ".." if len(app.name) > 20 else app.name
            print(f"{app.id:<25} {name:<20} {app_type:<18} {status:<15} {wps}")

    print(f"\nTotal: {len(applications)} applications")
    if not args.benchmark_ready:
        ready_count = len([a for a in applications if a.is_benchmark_ready])
        print(f"Benchmark ready: {ready_count}")

    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate documentation pages."""
    # Load config file if specified
    gen_config = None
    if args.config:
        try:
            gen_config = GenerationConfig.from_yaml(args.config)
            print(f"Loaded config from: {args.config}")
        except FileNotFoundError:
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1

    try:
        # Try unified exama.yaml config if no explicit source provided
        if args.source is None and HAS_UNIFIED_CONFIG:
            exama_config_path = getattr(args, 'exama_config', None)
            try:
                fetcher = create_fetcher_from_config(exama_config_path)
                print(f"Using software config from: {exama_config_path or DEFAULT_UNIFIED_CONFIG}")
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                print("Use -s/--source to specify a data source, or create exama.yaml", file=sys.stderr)
                return 1
        elif args.source:
            fetcher = create_fetcher(args.source)
        else:
            print("Error: No data source specified.", file=sys.stderr)
            print("Use -s/--source or create exama.yaml config file.", file=sys.stderr)
            return 1

        # Fetch data
        print("Fetching data...")
        frameworks = fetcher.fetch()
        print(f"  Frameworks: {len(frameworks.packages)}")

        applications = None
        if hasattr(fetcher, 'fetch_applications'):
            applications = fetcher.fetch_applications()
            print(f"  Applications: {len(applications.applications)}")

    except Exception as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return 1

    # Apply config-based filtering
    if gen_config:
        print("\nApplying config filters...")

        # Filter frameworks based on config
        filtered_pkgs = [
            p for p in frameworks.packages
            if gen_config.is_framework_enabled(p.slug)
        ]
        frameworks = SoftwareCollection(
            packages=filtered_pkgs,
            source_file=frameworks.source_file,
            fetched_at=frameworks.fetched_at,
        )
        print(f"  Frameworks after config filter: {len(frameworks.packages)}")

        # Filter applications based on config
        if applications:
            filtered_apps = [
                a for a in applications.applications
                if gen_config.is_application_enabled(a.slug)
            ]
            applications = ApplicationCollection(
                applications=filtered_apps,
                source_file=applications.source_file,
                fetched_at=applications.fetched_at,
            )
            print(f"  Applications after config filter: {len(applications.applications)}")

    # Apply work package filter if specified
    if args.filter_wp:
        wp_num = args.filter_wp
        print(f"\nFiltering for WP{wp_num}...")

        # Filter frameworks
        filtered_pkgs = [
            p for p in frameworks.packages
            if any(wp.wp_number == wp_num for wp in p.work_packages)
        ]
        frameworks = SoftwareCollection(
            packages=filtered_pkgs,
            source_file=frameworks.source_file,
            fetched_at=frameworks.fetched_at,
        )
        print(f"  Frameworks after filter: {len(frameworks.packages)}")

        # Filter applications
        if applications:
            filtered_apps = [
                a for a in applications.applications
                if f"WP{wp_num}" in a.work_packages
            ]
            applications = ApplicationCollection(
                applications=filtered_apps,
                source_file=applications.source_file,
                fetched_at=applications.fetched_at,
            )
            print(f"  Applications after filter: {len(applications.applications)}")

    # Setup generator
    AsciidocGenerator, GeneratorConfig = get_generator()

    config = GeneratorConfig(
        output_dir=Path(args.output),
        include_eligible_only=not args.all,
        generate_index=not args.no_index,
        generate_nav=not args.no_nav,
        work_packages=[args.filter_wp] if args.filter_wp else None,
    )

    generator = AsciidocGenerator(config)

    # Dry run mode - just show what would be generated
    if args.dry_run:
        print(f"\n[DRY RUN] Would generate to {args.output}/")

        packages = (
            frameworks.eligible_packages
            if not args.all
            else frameworks.packages
        )
        apps = []
        if applications:
            apps = (
                applications.eligible_applications
                if not args.all
                else applications.applications
            )

        if args.what in ("all", "frameworks"):
            print(f"\nFramework pages ({len(packages)} files):")
            for pkg in packages:
                print(f"  - frameworks/{pkg.slug}.adoc")

        if args.what in ("all", "applications") and apps:
            print(f"\nApplication pages ({len(apps)} files):")
            for app in apps:
                print(f"  - applications/{app.slug}.adoc")

        if args.what == "all" and not args.no_index:
            print(f"\nIndex pages:")
            print(f"  - frameworks.adoc")
            if applications:
                print(f"  - applications.adoc")

        if args.what == "all" and not args.no_nav:
            print(f"\nNavigation:")
            print(f"  - nav.adoc")

        return 0

    # Determine output directory structure
    output_dir = Path(args.output)
    if args.antora:
        # Antora expects pages/ subdirectory for content
        print(f"\nUsing Antora module structure...")

    # Generate pages
    print(f"\nGenerating pages to {output_dir}/")

    try:
        if args.what in ("all", "frameworks"):
            frameworks_dir = output_dir / "frameworks"
            print(f"\nGenerating framework pages...")
            written = generator.write_framework_pages(frameworks, frameworks_dir, applications)
            print(f"  Written: {len(written)} files")

        if args.what in ("all", "applications") and applications:
            apps_dir = output_dir / "applications"
            print(f"\nGenerating application pages...")
            written = generator.write_application_pages(applications, apps_dir)
            print(f"  Written: {len(written)} files")

        if args.what == "all" and not args.no_index:
            print(f"\nGenerating index pages...")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Frameworks index
            frameworks_index = generator.generate_frameworks_index(frameworks, applications)
            frameworks_index_path = output_dir / "frameworks.adoc"
            frameworks_index_path.write_text(frameworks_index)
            print(f"  Generated: {frameworks_index_path}")

            # Applications index
            if applications:
                apps_index = generator.generate_applications_index(applications, frameworks)
                apps_index_path = output_dir / "applications.adoc"
                apps_index_path.write_text(apps_index)
                print(f"  Generated: {apps_index_path}")

        if args.what == "all" and not args.no_nav:
            print(f"\nGenerating navigation...")
            nav_content = generator.generate_nav(frameworks, applications)
            # For Antora, nav goes one level up from pages
            nav_path = output_dir.parent / "nav.adoc" if args.antora else output_dir / "nav.adoc"
            nav_path.write_text(nav_content)
            print(f"  Generated: {nav_path}")

    except Exception as e:
        print(f"Error generating pages: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    print("\nGeneration complete!")
    return 0


def cmd_init_config(args: argparse.Namespace) -> int:
    """Create a default configuration file."""
    output_path = Path(args.output)

    if output_path.exists():
        print(f"Config file already exists: {output_path}")
        response = input("Overwrite? [y/N] ").strip().lower()
        if response != "y":
            print("Cancelled.")
            return 0

    try:
        create_default_config(output_path)
        print(f"Created config file: {output_path}")
        print("\nEdit this file to customize which frameworks and applications to include.")
        print("Then use: exa-ma-harvest-software generate -c harvest-config.yaml ...")
    except Exception as e:
        print(f"Error creating config file: {e}", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="exa-ma-harvest-software",
        description="Harvest and manage Exa-MA software and application metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch frameworks from local Excel file
  exa-ma-harvest-software fetch docs/software/stack/software.xlsx

  # List all eligible packages
  exa-ma-harvest-software list -s software.xlsx --eligible-only

  # Export to JSON
  exa-ma-harvest-software export -s software.xlsx -f json -o software.json

  # Fetch from Google Sheets (public)
  exa-ma-harvest-software fetch sheets:19v57jpek52nQV2V0tBBON5ivGCz7Bqf3Gw-fHroVHkA

  # List applications from Google Sheets
  exa-ma-harvest-software applications -s sheets:19v57jpek52nQV2V0tBBON5ivGCz7Bqf3Gw-fHroVHkA

  # List benchmark-ready applications
  exa-ma-harvest-software applications -s sheets:... --benchmark-ready

  # Filter applications by framework
  exa-ma-harvest-software applications -s sheets:... --framework Feel++

  # Generate documentation pages
  exa-ma-harvest-software generate -s sheets:... -o docs/modules/software/pages/

  # Generate only frameworks
  exa-ma-harvest-software generate -s sheets:... -o output/ --what frameworks

  # Use caching
  exa-ma-harvest-software fetch software.xlsx --cache --cache-ttl 7200

  # View cache stats
  exa-ma-harvest-software cache stats
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch software data")
    fetch_parser.add_argument(
        "source",
        help="Excel file path or 'sheets:<sheet_id>' for Google Sheets",
    )
    fetch_parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all packages after fetching",
    )
    fetch_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed criteria status",
    )
    fetch_parser.add_argument(
        "--cache",
        action="store_true",
        help="Enable caching",
    )
    fetch_parser.add_argument(
        "--cache-ttl",
        type=int,
        default=3600,
        help="Cache TTL in seconds (default: 3600)",
    )
    fetch_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh, ignoring cache",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List software packages")
    list_parser.add_argument(
        "-s", "--source",
        required=True,
        help="Data source (Excel path or sheets:<id>)",
    )
    list_parser.add_argument(
        "-f", "--format",
        choices=["table", "json", "names"],
        default="table",
        help="Output format (default: table)",
    )
    list_parser.add_argument(
        "--eligible-only",
        action="store_true",
        help="Only show packages eligible for page generation",
    )
    list_parser.add_argument(
        "--wp",
        type=int,
        choices=range(1, 8),
        help="Filter by work package number",
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export software data")
    export_parser.add_argument(
        "-s", "--source",
        required=True,
        help="Data source",
    )
    export_parser.add_argument(
        "-f", "--format",
        choices=["json", "yaml"],
        default="json",
        help="Output format (default: json)",
    )
    export_parser.add_argument(
        "-o", "--output",
        help="Output file path (prints to stdout if not specified)",
    )
    export_parser.add_argument(
        "--eligible-only",
        action="store_true",
        help="Only export eligible packages",
    )

    # Cache command
    cache_parser = subparsers.add_parser("cache", help="Manage cache")
    cache_parser.add_argument(
        "action",
        choices=["stats", "clear"],
        help="Cache action",
    )

    # Applications command
    apps_parser = subparsers.add_parser("applications", help="List/export applications")
    apps_parser.add_argument(
        "-s", "--source",
        required=True,
        help="Data source (Excel path or sheets:<id>)",
    )
    apps_parser.add_argument(
        "-f", "--format",
        choices=["table", "json", "names", "verbose"],
        default="table",
        help="Output format (default: table)",
    )
    apps_parser.add_argument(
        "--benchmark-ready",
        action="store_true",
        help="Only show applications ready for benchmarking",
    )
    apps_parser.add_argument(
        "--framework",
        help="Filter by framework name (e.g., 'Feel++')",
    )
    apps_parser.add_argument(
        "--wp",
        help="Filter by work package (e.g., 'WP1')",
    )

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate documentation pages")
    gen_parser.add_argument(
        "-s", "--source",
        required=True,
        help="Data source (Excel path or sheets:<id>)",
    )
    gen_parser.add_argument(
        "-o", "--output",
        default="pages",
        help="Output directory (default: pages)",
    )
    gen_parser.add_argument(
        "--what",
        choices=["all", "frameworks", "applications"],
        default="all",
        help="What to generate (default: all)",
    )
    gen_parser.add_argument(
        "--all",
        action="store_true",
        help="Include all packages, not just eligible ones",
    )
    gen_parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip generating index pages",
    )
    gen_parser.add_argument(
        "--no-nav",
        action="store_true",
        help="Skip generating navigation file",
    )
    gen_parser.add_argument(
        "--filter-wp",
        type=int,
        choices=range(1, 8),
        metavar="N",
        help="Only include items from work package N (1-7)",
    )
    gen_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be generated without writing files",
    )
    gen_parser.add_argument(
        "--antora",
        action="store_true",
        help="Output directly to Antora module structure",
    )
    gen_parser.add_argument(
        "-c", "--config",
        help="YAML config file for controlling which items to include",
    )

    # Init-config command
    init_config_parser = subparsers.add_parser(
        "init-config",
        help="Create a default configuration file",
    )
    init_config_parser.add_argument(
        "-o", "--output",
        default="harvest-config.yaml",
        help="Output file path (default: harvest-config.yaml)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "fetch":
        return cmd_fetch(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "export":
        return cmd_export(args)
    elif args.command == "cache":
        return cmd_cache(args)
    elif args.command == "applications":
        return cmd_applications(args)
    elif args.command == "generate":
        return cmd_generate(args)
    elif args.command == "init-config":
        return cmd_init_config(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
