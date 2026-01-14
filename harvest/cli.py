"""
Combined CLI for Exa-MA harvesting tools.

This module provides a unified command-line interface for running all
harvesting operations: HAL publications and GitHub deliverable releases.

Supports unified configuration from exama.yaml.
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config as load_exama_config, ExaMAConfig
from .hal import fetch_publications, output_asciidoc as hal_asciidoc, output_json as hal_json
from .releases import (
    DEFAULT_CONFIG,
    fetch_all_deliverables,
    load_config,
    output_asciidoc as releases_asciidoc,
    output_json as releases_json,
)
from .team import (
    fetch_recruited,
    fetch_recruited_with_config,
    generate_recruited_section,
    generate_team_asciidoc,
    generate_person_page,
    DEFAULT_SHEET_ID,
    DEFAULT_SHEET_NAME,
)
from .news import (
    load_config_with_fallback as load_news_config,
    output_partials as news_output_partials,
    generate_upcoming_cards,
    generate_recent_table,
    DEFAULT_CONFIG as NEWS_DEFAULT_CONFIG,
)

# Default unified config path
DEFAULT_EXAMA_CONFIG = Path(__file__).parent.parent / "exama.yaml"


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


def harvest_team(args: argparse.Namespace) -> int:
    """Run team/recruited personnel harvesting."""
    # Use unified config if --config is specified or exama.yaml exists
    exama_config_path = getattr(args, 'config', None)

    if exama_config_path or DEFAULT_EXAMA_CONFIG.exists():
        collection = fetch_recruited_with_config(
            config_path=exama_config_path or DEFAULT_EXAMA_CONFIG,
            funded_only=args.funded_only if not getattr(args, 'all_funding', False) else False,
            active_only=args.active_only,
        )
    else:
        collection = fetch_recruited(
            sheet_id=args.sheet_id,
            sheet_name=args.sheet_name,
            funded_only=args.funded_only,
            active_only=args.active_only,
        )

    personnel = collection.unique_personnel()
    if not personnel:
        print("No recruited personnel found.")
        return 1

    # Print statistics
    print(f"\nRecruited Personnel Statistics:")
    print(f"  Total unique: {len(personnel)}")
    print(f"  Active: {len([p for p in personnel if p.is_active])}")

    stats = collection.gender_stats
    print(f"\n  Gender breakdown:")
    print(f"    Male: {stats.male} ({stats.male_percentage:.1f}%)")
    print(f"    Female: {stats.female} ({stats.female_percentage:.1f}%)")

    by_pos = collection.by_position()
    print(f"\n  By position:")
    for pos, people in by_pos.items():
        unique = list({p.full_name: p for p in people}.values())
        print(f"    {pos.value}: {len(unique)}")

    # Generate output
    if args.format == "json":
        import json
        data = {
            "personnel": [p.model_dump(mode="json") for p in personnel],
            "statistics": {
                "total": len(personnel),
                "active": len([p for p in personnel if p.is_active]),
                "gender": {"male": stats.male, "female": stats.female, "unknown": stats.unknown},
                "by_position": {pos.value: len(list({p.full_name: p for p in ppl}.values()))
                               for pos, ppl in by_pos.items()},
            },
        }
        output = json.dumps(data, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output)
            print(f"\nJSON output written to: {args.output}")
        else:
            print("\n" + output)
    else:
        # AsciiDoc output
        output_dir = Path(args.pages_dir) if args.pages_dir else None
        content = generate_recruited_section(
            collection,
            active_only=args.active_only,
            generate_individual_pages=args.pages_dir is not None,
            output_dir=output_dir,
        )

        if args.output:
            Path(args.output).write_text(content)
            print(f"\nAsciiDoc output written to: {args.output}")
        else:
            print("\n" + content)

        if output_dir:
            # Count generated pages
            pages = list(output_dir.glob("*.adoc"))
            print(f"\nGenerated {len(pages)} individual person pages in: {output_dir}")

    return 0


def harvest_news(args: argparse.Namespace) -> int:
    """Run news/events harvesting."""
    config = load_news_config(args.config)
    events = config.get("events", [])

    config_source = args.config if args.config else "exama.yaml or news.yaml"
    print(f"Loaded {len(events)} events from {config_source}")

    if not events:
        print("No events found.")
        return 1

    # Count by status
    upcoming = len([e for e in events if e.get("status") == "upcoming"])
    recent = len([e for e in events if e.get("status") == "recent"])
    archived = len([e for e in events if e.get("status") == "archived"])
    print(f"  Upcoming: {upcoming}, Recent: {recent}, Archived: {archived}")

    if args.partials_dir:
        news_output_partials(config, args.partials_dir)
    else:
        # Print to stdout
        print("\n=== Upcoming Events ===")
        for line in generate_upcoming_cards(events):
            print(line)
        print("\n=== Recent Events ===")
        for line in generate_recent_table(events):
            print(line)

    return 0


def harvest_all(args: argparse.Namespace) -> int:
    """Run all harvesting operations."""
    print("=" * 60)
    print("Exa-MA Harvest - Running all harvesting operations")
    print("=" * 60)

    # Load unified config if available
    exama_config = None
    exama_config_path = getattr(args, 'config', None)
    if exama_config_path:
        try:
            exama_config = load_exama_config(exama_config_path)
            print(f"Using unified config: {exama_config_path}")
        except FileNotFoundError:
            print(f"Warning: Config file not found: {exama_config_path}")
    elif DEFAULT_EXAMA_CONFIG.exists():
        try:
            exama_config = load_exama_config(DEFAULT_EXAMA_CONFIG)
            print(f"Using unified config: {DEFAULT_EXAMA_CONFIG}")
        except Exception as e:
            print(f"Warning: Could not load default config: {e}")

    # Determine output directory
    output_dir = Path(args.output_dir) if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    errors = 0

    # HAL Publications
    print("\n[1/4] Harvesting HAL publications...")
    print("-" * 40)

    if exama_config:
        pub_config = exama_config.get_publications_config()
        years = pub_config.years
        domains = pub_config.domains
    else:
        years = [int(y.strip()) for y in args.years.split(",")]
        domains = [d.strip() for d in args.domains.split(",")] if args.domains else None

    publications = fetch_publications(years=years, domains=domains)

    if publications:
        print(f"Found {len(publications)} publications")
        hal_output = output_dir / "publications-hal.adoc"
        hal_asciidoc(publications, hal_output, partial=True)
    else:
        print("No publications found!")
        errors += 1

    # GitHub Releases
    print("\n[2/4] Harvesting GitHub releases...")
    print("-" * 40)

    if exama_config and exama_config.sources.deliverables.items:
        config = exama_config.get_deliverables_config().to_legacy_format()
    else:
        config = load_config(getattr(args, 'deliverables_config', None) or DEFAULT_CONFIG)

    releases = fetch_all_deliverables(config, latest_only=False)

    if releases:
        print(f"Found {len(releases)} releases")
        releases_output = output_dir / "deliverables-releases.adoc"
        releases_asciidoc(releases, config, releases_output)
    else:
        print("No releases found!")
        errors += 1

    # Team (recruited personnel)
    print("\n[3/4] Harvesting team data...")
    print("-" * 40)

    try:
        if exama_config:
            collection = fetch_recruited_with_config(config_path=exama_config_path or DEFAULT_EXAMA_CONFIG)
        else:
            collection = fetch_recruited()

        personnel = collection.unique_personnel()
        if personnel:
            print(f"Found {len(personnel)} recruited personnel")
            team_output = output_dir / "recruited-personnel.adoc"
            content = generate_recruited_section(collection)
            team_output.write_text(content)
            print(f"  Saved to: {team_output}")
        else:
            print("No recruited personnel found!")
    except Exception as e:
        print(f"Error harvesting team data: {e}")
        errors += 1

    # News and Events
    print("\n[4/4] Harvesting news and events...")
    print("-" * 40)

    news_events = []
    try:
        news_config = load_news_config(exama_config_path if exama_config_path else None)
        news_events = news_config.get("events", [])
        if news_events:
            print(f"Found {len(news_events)} events")
            upcoming = len([e for e in news_events if e.get("status") == "upcoming"])
            recent = len([e for e in news_events if e.get("status") == "recent"])
            archived = len([e for e in news_events if e.get("status") == "archived"])
            print(f"  Upcoming: {upcoming}, Recent: {recent}, Archived: {archived}")
            news_output_partials(news_config, output_dir)
        else:
            print("No events found!")
    except Exception as e:
        print(f"Error harvesting news: {e}")
        errors += 1

    # Summary
    print("\n" + "=" * 60)
    print("Harvesting complete!")
    print(f"  Publications: {len(publications) if publications else 0}")
    print(f"  Releases: {len(releases) if releases else 0}")
    print(f"  Personnel: {len(personnel) if 'personnel' in dir() and personnel else 0}")
    print(f"  Events: {len(news_events) if news_events else 0}")
    if errors:
        print(f"  Errors: {errors}")
    print("=" * 60)

    return errors


def main():
    """Main entry point for the combined CLI."""
    parser = argparse.ArgumentParser(
        prog="exa-ma-harvest",
        description="Exa-MA Harvesting Tools - Collect publications, deliverables, and team data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  exa-ma-harvest hal -o publications.adoc
  exa-ma-harvest releases -o deliverables.adoc --latest-only
  exa-ma-harvest team --funded-only
  exa-ma-harvest news --partials-dir ./partials
  exa-ma-harvest all --output-dir ./output
  exa-ma-harvest all --config exama.yaml

Configuration:
  All commands can use a unified exama.yaml config file. If exama.yaml
  exists in the current directory or the exama/ directory, it will be
  used automatically. Use --config to specify a custom path.

Legacy individual commands (deprecated, use subcommands above):
  exa-ma-harvest-hal      - Harvest HAL publications
  exa-ma-harvest-releases - Harvest GitHub releases
  exa-ma-harvest-news     - Generate news pages
  exa-ma-harvest-software - Harvest software metadata
""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to unified exama.yaml config file",
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

    # Team subcommand
    team_parser = subparsers.add_parser(
        "team", help="Harvest recruited personnel from Google Sheets"
    )
    team_parser.add_argument(
        "-o", "--output", help="Output file path (prints to stdout if not specified)"
    )
    team_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "asciidoc"],
        default="asciidoc",
        help="Output format (default: asciidoc)",
    )
    team_parser.add_argument(
        "--sheet-id",
        default=DEFAULT_SHEET_ID,
        help=f"Google Sheets document ID (default: {DEFAULT_SHEET_ID})",
    )
    team_parser.add_argument(
        "--sheet-name",
        default=DEFAULT_SHEET_NAME,
        help=f"Sheet name to read (default: {DEFAULT_SHEET_NAME})",
    )
    team_parser.add_argument(
        "--funded-only",
        action="store_true",
        default=True,
        help="Only include personnel funded by Exa-MA (default: True)",
    )
    team_parser.add_argument(
        "--all-funding",
        action="store_true",
        help="Include all personnel regardless of funding",
    )
    team_parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only include currently active personnel",
    )
    team_parser.add_argument(
        "--pages-dir",
        help="Directory for individual person pages (generates xref links)",
    )

    # News subcommand
    news_parser = subparsers.add_parser(
        "news", help="Generate news and events pages"
    )
    news_parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to config file (default: exama.yaml or news.yaml)",
    )
    news_parser.add_argument(
        "--partials-dir",
        type=Path,
        help="Output directory for Antora partial files",
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
    elif args.command == "team":
        # Handle --all-funding flag
        if hasattr(args, 'all_funding') and args.all_funding:
            args.funded_only = False
        return harvest_team(args)
    elif args.command == "news":
        return harvest_news(args)
    elif args.command == "all":
        return harvest_all(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
