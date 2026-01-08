"""
Generate Exa-MA news and events pages from YAML configuration.

This module reads news/events from a YAML file and generates AsciiDoc partials
for the Antora website.
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Default config path (relative to this module)
DEFAULT_CONFIG = Path(__file__).parent.parent / "news.yaml"

# Icon mapping for event types
TYPE_ICONS = {
    "assembly": "users",
    "conference": "chalkboard-teacher",
    "training": "laptop-code",
    "webinar": "box",
    "workshop": "users",
    "external": "building",
}

# Icon roles for styling
TYPE_ROLES = {
    "assembly": "text-primary",
    "conference": "text-info",
    "training": "text-success",
    "webinar": "text-warning",
    "workshop": "text-primary",
    "external": "text-info",
}


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        if HAS_YAML:
            return yaml.safe_load(f)
        else:
            raise ImportError("PyYAML is required for news generation")


def format_date_range(event: dict) -> str:
    """Format date or date range for display."""
    start = event.get("date", "")
    end = event.get("end_date", "")

    if not start:
        return "TBD"

    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        start_fmt = start_dt.strftime("%b %d, %Y")

        if end:
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            # Same month
            if start_dt.month == end_dt.month and start_dt.year == end_dt.year:
                return f"{start_dt.strftime('%b %d')}-{end_dt.strftime('%d, %Y')}"
            # Different months
            return f"{start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d, %Y')}"

        return start_fmt
    except ValueError:
        return start


def generate_upcoming_cards(events: list[dict]) -> list[str]:
    """Generate card layout for upcoming events."""
    upcoming = [e for e in events if e.get("status") == "upcoming"]

    if not upcoming:
        return ["_No upcoming events scheduled._"]

    lines = ["[.grid.grid-2.gap-2.items-start]", "--"]

    for event in upcoming:
        icon = event.get("icon", TYPE_ICONS.get(event.get("type", ""), "calendar"))
        role = TYPE_ROLES.get(event.get("type", ""), "text-primary")
        title = event.get("title", "Untitled Event")
        date_str = format_date_range(event)
        location = event.get("location", "")
        description = event.get("description", "").strip().replace("\n", " ")

        # Build link
        if event.get("page"):
            link = f"xref:{event['page']}[View full agenda and details →]"
        elif event.get("url"):
            link = f"{event['url']}[Event details and registration →]"
        else:
            link = ""

        lines.append("[.card]")
        lines.append("====")
        lines.append(f"icon:{icon}[size=2x,role={role}] *{title}*")
        lines.append("")
        if location:
            lines.append(f"*{date_str}* | {location}")
        else:
            lines.append(f"*{date_str}*")
        lines.append("")
        lines.append(description)
        lines.append("")
        if link:
            lines.append(link)
        lines.append("====")
        lines.append("")

    lines.append("--")
    return lines


def generate_event_table(events: list[dict], table_class: str = "") -> list[str]:
    """Generate table layout for a list of events."""
    if not events:
        return ["_No events._"]

    # Sort by date descending
    events = sorted(events, key=lambda x: x.get("date", ""), reverse=True)

    # Add optional CSS class for styling
    class_attr = f".{table_class}," if table_class else ""
    lines = [f"[{class_attr}cols=\"1,5\",frame=none,grid=rows]", "|==="]

    for event in events:
        icon = event.get("icon", TYPE_ICONS.get(event.get("type", ""), "calendar"))
        title = event.get("title", "Untitled Event")
        date_str = format_date_range(event)
        location = event.get("location", "")
        description = event.get("description", "").strip().replace("\n", " ")

        # Build link
        if event.get("page"):
            link_text = f"xref:{event['page']}[Read full recap →]"
        elif event.get("url"):
            link_text = f"{event['url']}[Event details and presentations]"
        else:
            link_text = ""

        # Format location
        location_str = f" – {location}" if location else ""

        lines.append(f"|icon:{icon}[size=2x] *{date_str}*")
        lines.append(f"|**{title}**{location_str} +")
        lines.append(f"{description} +")
        if link_text:
            lines.append(link_text)
        lines.append("")

    lines.append("|===")
    return lines


def generate_recent_table(events: list[dict]) -> list[str]:
    """Generate table layout for recent events."""
    recent = [e for e in events if e.get("status") == "recent"]
    return generate_event_table(recent)


def get_event_year(event: dict) -> int | None:
    """Extract year from event date."""
    date_str = event.get("date", "")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").year
        except ValueError:
            pass
    return None


def generate_archive_by_year(events: list[dict]) -> dict[int, list[str]]:
    """Generate archive content grouped by year."""
    archived = [e for e in events if e.get("status") == "archived"]

    # Group by year
    by_year: dict[int, list[dict]] = {}
    for event in archived:
        year = get_event_year(event)
        if year:
            by_year.setdefault(year, []).append(event)

    results = {}
    sorted_years = sorted(by_year.keys(), reverse=True)
    for idx, year in enumerate(sorted_years):
        year_events = by_year[year]
        # Alternate between year-even and year-odd for styling
        table_class = "year-even" if idx % 2 == 0 else "year-odd"
        lines = [
            f"// Year: {year}, Events: {len(year_events)}",
            "",
        ]
        lines.extend(generate_event_table(year_events, table_class))
        results[year] = lines

    return results


def output_partials(config: dict, output_dir: Path) -> dict[str, str]:
    """Generate partial files for news/events."""
    output_dir.mkdir(parents=True, exist_ok=True)
    events = config.get("events", [])

    results = {}

    # Generate upcoming events partial
    upcoming_lines = [
        f"// Events: {len([e for e in events if e.get('status') == 'upcoming'])} upcoming",
        "",
    ]
    upcoming_lines.extend(generate_upcoming_cards(events))

    upcoming_content = "\n".join(upcoming_lines)
    upcoming_path = output_dir / "news-upcoming.adoc"
    upcoming_path.write_text(upcoming_content, encoding="utf-8")
    print(f"  Saved partial: {upcoming_path}")
    results["upcoming"] = upcoming_content

    # Generate recent events partial
    recent_lines = [
        f"// Events: {len([e for e in events if e.get('status') == 'recent'])} recent",
        "",
    ]
    recent_lines.extend(generate_recent_table(events))

    recent_content = "\n".join(recent_lines)
    recent_path = output_dir / "news-recent.adoc"
    recent_path.write_text(recent_content, encoding="utf-8")
    print(f"  Saved partial: {recent_path}")
    results["recent"] = recent_content

    # Generate archive partials by year
    archive_by_year = generate_archive_by_year(events)
    for year, lines in archive_by_year.items():
        archive_content = "\n".join(lines)
        archive_path = output_dir / f"news-archive-{year}.adoc"
        archive_path.write_text(archive_content, encoding="utf-8")
        print(f"  Saved partial: {archive_path}")
        results[f"archive-{year}"] = archive_content

    # Generate archive index partial (list of years with event counts)
    if archive_by_year:
        index_lines = [
            f"// Archive years: {len(archive_by_year)}",
            "",
        ]
        for year in sorted(archive_by_year.keys(), reverse=True):
            archived_count = len([e for e in events if e.get("status") == "archived" and get_event_year(e) == year])
            index_lines.append(f"* <<{year},{year}>> ({archived_count} events)")

        index_content = "\n".join(index_lines)
        index_path = output_dir / "news-archive-index.adoc"
        index_path.write_text(index_content, encoding="utf-8")
        print(f"  Saved partial: {index_path}")
        results["archive-index"] = index_content

    return results


def main():
    """Main entry point for news generation."""
    parser = argparse.ArgumentParser(
        description="Generate Exa-MA news and events from YAML configuration"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to news YAML file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--partials-dir",
        type=Path,
        help="Output directory for Antora partial files",
    )

    args = parser.parse_args()

    config = load_config(args.config)
    events = config.get("events", [])

    print(f"Loaded {len(events)} events from {args.config}")

    if args.partials_dir:
        output_partials(config, args.partials_dir)
    else:
        # Print to stdout
        print("\n=== Upcoming Events ===")
        for line in generate_upcoming_cards(events):
            print(line)
        print("\n=== Recent Events ===")
        for line in generate_recent_table(events):
            print(line)


if __name__ == "__main__":
    main()
