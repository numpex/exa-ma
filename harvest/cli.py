"""
Combined CLI for Exa-MA harvesting tools.

This module provides a unified command-line interface for running all
harvesting operations: HAL publications and GitHub deliverable releases.
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .hal import fetch_publications, output_asciidoc as hal_asciidoc, output_json as hal_json
from .releases import (
    DEFAULT_CONFIG,
    fetch_all_deliverables,
    load_config,
    output_asciidoc as releases_asciidoc,
    output_json as releases_json,
)


def harvest_hal(args: argparse.Namespace) -> int:
    """Run HAL publications harvesting."""
    years = [int(y.strip()) for y in args.years.split(",")]

    domains = None
    if args.domains:
        domains = [d.strip() for d in args.domains.split(",")]

    publications = fetch_publications(
        query=args.query,
        domains=domains,
        years=years,
    )

    if not publications:
        print("No publications found.")
        return 1

    print(f"\nTotal publications retrieved: {len(publications)}")

    if args.format == "json":
        hal_json(publications, args.output)
    else:
        hal_asciidoc(publications, args.output)

    return 0


def harvest_releases(args: argparse.Namespace) -> int:
    """Run GitHub releases harvesting."""
    config = load_config(args.config)
    releases = fetch_all_deliverables(config, latest_only=args.latest_only)

    if not releases:
        print("No releases found.")
        return 1

    print(f"\nTotal releases retrieved: {len(releases)}")

    if args.format == "json":
        releases_json(releases, config, args.output)
    else:
        releases_asciidoc(releases, config, args.output)

    return 0


def harvest_all(args: argparse.Namespace) -> int:
    """Run all harvesting operations."""
    print("=" * 60)
    print("Exa-MA Harvest - Running all harvesting operations")
    print("=" * 60)

    # Determine output directory
    output_dir = Path(args.output_dir) if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    errors = 0

    # HAL Publications
    print("\n[1/2] Harvesting HAL publications...")
    print("-" * 40)

    years = [int(y.strip()) for y in args.years.split(",")]
    domains = [d.strip() for d in args.domains.split(",")] if args.domains else None

    publications = fetch_publications(years=years, domains=domains)

    if publications:
        print(f"Found {len(publications)} publications")
        hal_output = output_dir / "publications-hal.adoc"
        hal_asciidoc(publications, hal_output)
    else:
        print("No publications found!")
        errors += 1

    # GitHub Releases
    print("\n[2/2] Harvesting GitHub releases...")
    print("-" * 40)

    config = load_config(args.config)
    releases = fetch_all_deliverables(config, latest_only=False)

    if releases:
        print(f"Found {len(releases)} releases")
        releases_output = output_dir / "deliverables-releases.adoc"
        releases_asciidoc(releases, config, releases_output)
    else:
        print("No releases found!")
        errors += 1

    # Summary
    print("\n" + "=" * 60)
    print("Harvesting complete!")
    print(f"  Publications: {len(publications) if publications else 0}")
    print(f"  Releases: {len(releases) if releases else 0}")
    if errors:
        print(f"  Errors: {errors}")
    print("=" * 60)

    return errors


def main():
    """Main entry point for the combined CLI."""
    parser = argparse.ArgumentParser(
        prog="exa-ma-harvest",
        description="Exa-MA Harvesting Tools - Collect publications and deliverables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  exa-ma-harvest-all hal -o publications.adoc
  exa-ma-harvest-all releases -o deliverables.adoc --latest-only
  exa-ma-harvest-all all --output-dir ./output

Individual commands are also available:
  exa-ma-harvest-hal      - Harvest HAL publications
  exa-ma-harvest-releases - Harvest GitHub releases
""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # HAL subcommand
    hal_parser = subparsers.add_parser("hal", help="Harvest publications from HAL")
    hal_parser.add_argument(
        "-o", "--output", help="Output file path (prints to stdout if not specified)"
    )
    hal_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "csv", "asciidoc", "bibtex"],
        default="asciidoc",
        help="Output format (default: asciidoc)",
    )
    hal_parser.add_argument(
        "-q",
        "--query",
        default="anrProjectReference_s:ANR-22-EXNU-0002",
        help="Search query (default: anrProjectReference_s:ANR-22-EXNU-0002)",
    )
    hal_parser.add_argument(
        "-y",
        "--years",
        default="2023,2024,2025",
        help="Comma-separated years to filter (default: 2023,2024,2025)",
    )
    hal_parser.add_argument(
        "-d",
        "--domains",
        help="Comma-separated domains (default: math,info,stat,phys)",
    )

    # Releases subcommand
    releases_parser = subparsers.add_parser(
        "releases", help="Harvest deliverable releases from GitHub"
    )
    releases_parser.add_argument(
        "-o", "--output", help="Output file path (prints to stdout if not specified)"
    )
    releases_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "asciidoc"],
        default="asciidoc",
        help="Output format (default: asciidoc)",
    )
    releases_parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to config YAML file (default: {DEFAULT_CONFIG})",
    )
    releases_parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Show only the latest release per deliverable",
    )

    # All subcommand (run everything)
    all_parser = subparsers.add_parser("all", help="Run all harvesting operations")
    all_parser.add_argument(
        "--output-dir",
        help="Output directory for generated files (default: current directory)",
    )
    all_parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to deliverables config YAML file",
    )
    all_parser.add_argument(
        "-y",
        "--years",
        default="2023,2024,2025",
        help="Comma-separated years for HAL (default: 2023,2024,2025)",
    )
    all_parser.add_argument(
        "-d",
        "--domains",
        help="Comma-separated domains for HAL (default: math,info,stat,phys)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "hal":
        return harvest_hal(args)
    elif args.command == "releases":
        return harvest_releases(args)
    elif args.command == "all":
        return harvest_all(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
