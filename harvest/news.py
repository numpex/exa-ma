"""
Generate Exa-MA news and events pages from YAML configuration.

This module reads news/events from a YAML file and generates AsciiDoc partials
for the Antora website.

Supports configuration from:
- Command line arguments (highest priority)
- Unified exama.yaml config file
- Legacy news.yaml (backward compatibility)
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

# Import unified config (conditional to avoid circular imports)
try:
    from .config import ExaMAConfig, load_config as load_exama_config, merge_with_legacy_news
    HAS_UNIFIED_CONFIG = True
except ImportError:
    HAS_UNIFIED_CONFIG = False


# Default config path (relative to this module)
DEFAULT_CONFIG = Path(__file__).parent.parent / "news.yaml"
DEFAULT_UNIFIED_CONFIG = Path(__file__).parent.parent / "exama.yaml"
DEFAULT_PARTIALS_DIR = Path("docs/modules/ROOT/partials")
DEFAULT_PAGES_DIR = Path(__file__).parent.parent / "docs/modules/ROOT/pages"


def resolve_partials_dir(config_path: Path | None = None) -> Path:
    """Resolve the default Antora partials directory."""
    unified_config = config_path or DEFAULT_UNIFIED_CONFIG
    if unified_config.exists():
        config = load_config(unified_config)
        partials_dir = config.get("output", {}).get("partials_dir")
        if partials_dir:
            return Path(partials_dir)
    return DEFAULT_PARTIALS_DIR

# Icon mapping for event types
TYPE_ICONS = {
    "assembly": "users",
    "conference": "chalkboard-teacher",
    "training": "laptop-code",
    "webinar": "box",
    "workshop": "users",
    "external": "building",
    "announcement": "bullhorn",
}

# Icon roles for styling
TYPE_ROLES = {
    "assembly": "text-primary",
    "conference": "text-info",
    "training": "text-success",
    "webinar": "text-warning",
    "workshop": "text-primary",
    "external": "text-info",
    "announcement": "text-success",
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


def truncate_text(text: str, limit: int = 240) -> str:
    """Trim long descriptions for compact homepage cards."""
    text = " ".join(text.strip().split())
    if len(text) <= limit:
        return text

    trimmed = text[:limit].rsplit(" ", 1)[0].rstrip(" .,;:")
    return f"{trimmed}..."


def event_title_link(event: dict, title: str) -> str:
    """Return a linked event title when a page or external URL is available."""
    if event.get("page") and (DEFAULT_PAGES_DIR / event["page"]).exists():
        return f"xref:{event['page']}[{title}]"
    if event.get("url"):
        return f"{event['url']}[{title}]"
    return title


def event_detail_link(event: dict, page_label: str, url_label: str) -> str:
    """Return a detail link, avoiding xrefs to pages that are not present."""
    if event.get("page") and (DEFAULT_PAGES_DIR / event["page"]).exists():
        return f"xref:{event['page']}[{page_label}]"
    if event.get("url"):
        return f"{event['url']}[{url_label}]"
    return ""


def generate_home_cards(events: list[dict], limit: int = 4) -> list[str]:
    """Generate compact cards for the homepage from upcoming and recent events."""
    upcoming = sorted(
        [e for e in events if e.get("status") == "upcoming"],
        key=lambda x: x.get("date", ""),
    )
    recent = sorted(
        [e for e in events if e.get("status") == "recent"],
        key=lambda x: x.get("date", ""),
        reverse=True,
    )
    selected = upcoming[:limit]
    if len(selected) < limit:
        selected.extend(recent[: limit - len(selected)])

    if not selected:
        return ["_No news or events listed._"]

    lines = ["[.grid.grid-2.gap-2]", "===="]
    for event in selected:
        icon = event.get("icon", TYPE_ICONS.get(event.get("type", ""), "calendar"))
        role = TYPE_ROLES.get(event.get("type", ""), "text-primary")
        title = event.get("title", "Untitled Event")
        title_link = event_title_link(event, title)
        date_str = format_date_range(event)
        location = event.get("location", "")
        description = truncate_text(event.get("summary") or event.get("description", ""))
        date_line = f"*{date_str}*"
        if location:
            date_line = f"{date_line} | {location}"

        lines.extend(
            [
                "[.text-center]",
                "____",
                f"icon:{icon}[size=2x,role={role}] {date_line} +",
                f"{title_link} - {description}",
                "____",
                "",
            ]
        )

    lines.append("====")
    return lines


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

        custom_link_text = event.get("link_text")
        link = event_detail_link(
            event,
            custom_link_text or "View full agenda and details →",
            custom_link_text or "Event details and registration →",
        )

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

        custom_link_text = event.get("link_text")
        link_text = event_detail_link(
            event,
            custom_link_text or "Read full recap →",
            custom_link_text or "Event details and presentations",
        )

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
    archived = [e for e in events if e.get("status") in {"archived", "recent"}]

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

    # Generate compact homepage partial
    home_lines = [
        f"// Events: homepage selection from {len(events)} configured events",
        "",
    ]
    home_lines.extend(generate_home_cards(events))

    home_content = "\n".join(home_lines)
    home_path = output_dir / "news-home.adoc"
    home_path.write_text(home_content, encoding="utf-8")
    print(f"  Saved partial: {home_path}")
    results["home"] = home_content

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
            archived_count = len([
                e
                for e in events
                if e.get("status") in {"archived", "recent"}
                and get_event_year(e) == year
            ])
            index_lines.append(f"* <<{year},{year}>> ({archived_count} events)")

        index_content = "\n".join(index_lines)
        index_path = output_dir / "news-archive-index.adoc"
        index_path.write_text(index_content, encoding="utf-8")
        print(f"  Saved partial: {index_path}")
        results["archive-index"] = index_content

    return results


def load_config_with_fallback(config_path: Path | None = None) -> dict:
    """Load configuration with fallback to unified config.

    Tries in order:
    1. Specified config path (if provided)
    2. Unified exama.yaml (if available and has events or references news.yaml)
    3. Legacy news.yaml

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Configuration dict with 'events' key
    """
    # If explicit path provided, use it directly
    if config_path and config_path.exists():
        return load_config(config_path)

    # Try unified config
    if HAS_UNIFIED_CONFIG and DEFAULT_UNIFIED_CONFIG.exists():
        try:
            exama_config = load_exama_config(DEFAULT_UNIFIED_CONFIG)
            # Use get_news_events which handles external file loading
            events = exama_config.get_news_events()
            if events:
                # Convert to legacy format
                return {"events": [e.model_dump() for e in events]}
            # If no events from unified config, fall through to legacy
        except Exception as e:
            print(f"Warning: Could not load unified config: {e}")

    # Fall back to legacy config
    return load_config(DEFAULT_CONFIG)


def main():
    """Main entry point for news generation."""
    parser = argparse.ArgumentParser(
        description="Generate Exa-MA news and events from YAML configuration"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help=f"Path to config file (default: exama.yaml or news.yaml)",
    )
    parser.add_argument(
        "--partials-dir",
        type=Path,
        help="Output directory for Antora partial files",
    )

    args = parser.parse_args()

    config = load_config_with_fallback(args.config)
    events = config.get("events", [])

    config_source = args.config or DEFAULT_UNIFIED_CONFIG if DEFAULT_UNIFIED_CONFIG.exists() else DEFAULT_CONFIG
    print(f"Loaded {len(events)} events from {config_source}")

    output_dir = args.partials_dir or resolve_partials_dir(args.config)
    output_partials(config, output_dir)


if __name__ == "__main__":
    main()
