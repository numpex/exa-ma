"""
Harvest Exa-MA deliverable releases from GitHub repositories.

This module queries the GitHub API to retrieve releases for Exa-MA deliverables,
using configuration from deliverables.yaml.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Try to import yaml, fall back to basic parsing if not available
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# GitHub API endpoint
GITHUB_API_URL = "https://api.github.com"

# Default config path (relative to this module)
DEFAULT_CONFIG = Path(__file__).parent.parent / "deliverables.yaml"


def parse_basic_yaml(content: str) -> dict:
    """Basic YAML parser for simple structures (fallback when PyYAML unavailable)."""
    result: dict[str, Any] = {"settings": {}, "deliverables": []}
    current_deliverable: dict[str, Any] | None = None
    current_list: str | None = None

    for line in content.split("\n"):
        # Skip comments and empty lines
        if line.strip().startswith("#") or not line.strip():
            continue

        # Count indentation
        indent = len(line) - len(line.lstrip())
        line = line.strip()

        # Parse key-value pairs
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if key == "deliverables":
                continue
            elif key == "settings":
                continue
            elif line.startswith("- id:"):
                if current_deliverable:
                    result["deliverables"].append(current_deliverable)
                current_deliverable = {"id": value.strip('"')}
                current_list = None
            elif current_deliverable is not None:
                if key in ("workpackages", "featured_versions"):
                    current_list = key
                    current_deliverable[key] = []
                elif value:
                    # Remove quotes
                    value = value.strip('"').strip("'")
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    current_deliverable[key] = value
            elif indent == 2 and key in ("max_releases", "include_prereleases", "latest_only"):
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                result["settings"][key] = value
        elif line.startswith("- ") and current_list and current_deliverable:
            value = line[2:].strip().strip('"').strip("'")
            current_deliverable[current_list].append(value)

    if current_deliverable:
        result["deliverables"].append(current_deliverable)

    return result


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        if HAS_YAML:
            return yaml.safe_load(f)
        else:
            # Basic YAML parsing fallback (limited support)
            print("Warning: PyYAML not installed, using basic parsing", file=sys.stderr)
            return parse_basic_yaml(f.read())


def fetch_releases(repo: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch releases from a GitHub repository."""
    url = f"{GITHUB_API_URL}/repos/{repo}/releases?per_page={limit}"

    try:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Exa-MA-Deliverables-Harvester/1.0",
            },
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP Error {e.code} for {repo}: {e.reason}", file=sys.stderr)
        return []
    except URLError as e:
        print(f"URL Error for {repo}: {e.reason}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"JSON decode error for {repo}: {e}", file=sys.stderr)
        return []


def extract_pdf_assets(assets: list[dict]) -> list[dict[str, str]]:
    """Extract PDF assets from release assets."""
    pdfs = []
    for asset in assets:
        name = asset.get("name", "")
        if name.lower().endswith(".pdf"):
            pdfs.append(
                {
                    "name": name,
                    "url": asset.get("browser_download_url", ""),
                    "size": asset.get("size", 0),
                }
            )
    return pdfs


def format_release(
    release: dict, deliverable: dict, is_latest: bool = False, is_featured: bool = False
) -> dict[str, Any]:
    """Format a release record for output."""
    # Parse release date
    published_at = release.get("published_at", "")
    if published_at:
        try:
            date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            date_str = date.strftime("%Y-%m-%d")
        except ValueError:
            date_str = published_at[:10]
    else:
        date_str = "N/A"

    return {
        "deliverable_id": deliverable["id"],
        "title": deliverable["title"],
        "description": deliverable["description"],
        "workpackages": deliverable.get("workpackages", []),
        "repo": deliverable["repo"],
        "version": release.get("tag_name", ""),
        "name": release.get("name", ""),
        "date": date_str,
        "html_url": release.get("html_url", ""),
        "body": release.get("body", ""),
        "prerelease": release.get("prerelease", False),
        "draft": release.get("draft", False),
        "is_latest": is_latest,
        "is_featured": is_featured,
        "pdfs": extract_pdf_assets(release.get("assets", [])),
    }


def fetch_all_deliverables(
    config: dict, latest_only: bool = False, verbose: bool = True
) -> list[dict[str, Any]]:
    """Fetch releases for all configured deliverables."""
    settings = config.get("settings", {})
    include_prereleases = settings.get("include_prereleases", False)
    max_releases = settings.get("max_releases", 5)

    if latest_only or settings.get("latest_only", False):
        max_releases = 1

    all_releases = []

    for deliverable in config.get("deliverables", []):
        repo = deliverable["repo"]
        featured_versions = set(deliverable.get("featured_versions", []))

        if verbose:
            print(f"Fetching releases for {repo}...")

        releases = fetch_releases(repo, limit=20)  # Fetch more to find featured

        selected_releases = []
        is_first = True

        for release in releases:
            # Skip drafts
            if release.get("draft", False):
                continue
            # Skip prereleases unless requested
            if not include_prereleases and release.get("prerelease", False):
                continue

            version = release.get("tag_name", "")
            is_featured = version in featured_versions
            is_latest = is_first

            # Include if: within max_releases limit, or is featured
            if len(selected_releases) < max_releases or is_featured:
                formatted = format_release(release, deliverable, is_latest, is_featured)

                # Avoid duplicates (featured might already be in top N)
                if not any(r["version"] == version for r in selected_releases):
                    selected_releases.append(formatted)

            is_first = False

        # Sort by date (latest first), keeping featured releases
        selected_releases.sort(key=lambda x: x["date"], reverse=True)
        all_releases.extend(selected_releases)

    return all_releases


def output_json(
    releases: list[dict], config: dict, output_file: str | Path | None = None
) -> str:
    """Output releases as JSON."""
    result = {
        "metadata": {
            "source": "GitHub Releases",
            "project": "Exa-MA Deliverables",
            "harvested_at": datetime.now().isoformat(),
            "total_count": len(releases),
        },
        "config": config.get("settings", {}),
        "releases": releases,
    }

    content = json.dumps(result, indent=2, ensure_ascii=False)

    if output_file:
        Path(output_file).write_text(content, encoding="utf-8")
        print(f"\nSaved to {output_file}")
    else:
        print(content)

    return content


def output_asciidoc(
    releases: list[dict], config: dict, output_file: str | Path | None = None
) -> str:
    """Output releases as AsciiDoc table grouped by deliverable."""
    # Group by deliverable ID
    by_deliverable: dict[str, dict] = {}
    for release in releases:
        did = release["deliverable_id"]
        if did not in by_deliverable:
            by_deliverable[did] = {
                "info": {
                    "title": release["title"],
                    "description": release["description"],
                    "workpackages": release["workpackages"],
                    "repo": release["repo"],
                },
                "releases": [],
            }
        by_deliverable[did]["releases"].append(release)

    lines = []

    # Generate table for each deliverable
    for deliverable in config.get("deliverables", []):
        did = deliverable["id"]
        if did not in by_deliverable:
            continue

        data = by_deliverable[did]
        info = data["info"]
        rels = data["releases"]

        lines.append(f"=== {did}: {info['title']}")
        lines.append("")
        lines.append(f"_{info['description']}_")
        lines.append("")
        lines.append(f"*Work Packages*: {', '.join(info['workpackages'])}")
        lines.append("")
        lines.append(
            f"*Repository*: https://github.com/{info['repo']}[icon:code-branch[] {info['repo']}]"
        )
        lines.append("")

        # Releases table
        lines.append('[.striped,cols="1,2,1,2",options="header"]')
        lines.append("|===")
        lines.append("|Version |Release |Date |Downloads")
        lines.append("")

        for rel in rels:
            version = rel["version"]
            name = rel["name"] or version
            date = rel["date"]
            html_url = rel["html_url"]

            # Add badges for latest/featured
            badges = []
            if rel.get("is_latest"):
                badges.append("icon:star[role=text-warning,title=Latest]")
            if rel.get("is_featured") and not rel.get("is_latest"):
                badges.append("icon:bookmark[role=text-info,title=ANR Submission]")
            badge_str = " ".join(badges)
            if badge_str:
                badge_str = " " + badge_str

            # Build download links
            downloads = []
            downloads.append(f"link:{html_url}[icon:tag[title=Release]]")
            for pdf in rel["pdfs"]:
                downloads.append(f"link:{pdf['url']}[icon:file-pdf[title=PDF,role=text-danger]]")

            # Escape pipe characters
            name = name.replace("|", "\\|")

            lines.append(f"|*{version}*{badge_str}")
            lines.append(f"|{name}")
            lines.append(f"|{date}")
            lines.append(f"|{' '.join(downloads)}")
            lines.append("")

        lines.append("|===")
        lines.append("")

    content = "\n".join(lines)

    if output_file:
        Path(output_file).write_text(content, encoding="utf-8")
        print(f"\nSaved to {output_file}")
    else:
        print(content)

    return content


def output_partials(
    releases: list[dict], config: dict, output_dir: str | Path
) -> dict[str, str]:
    """Output releases as individual partial files per deliverable.

    Each partial contains just the table rows for that deliverable,
    suitable for inclusion in Antora pages.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group by deliverable ID
    by_deliverable: dict[str, dict] = {}
    for release in releases:
        did = release["deliverable_id"]
        if did not in by_deliverable:
            by_deliverable[did] = {
                "info": {
                    "title": release["title"],
                    "description": release["description"],
                    "workpackages": release["workpackages"],
                    "repo": release["repo"],
                },
                "releases": [],
            }
        by_deliverable[did]["releases"].append(release)

    results = {}

    for deliverable in config.get("deliverables", []):
        did = deliverable["id"]
        if did not in by_deliverable:
            continue

        data = by_deliverable[did]
        rels = data["releases"]

        lines = [
            f"// Deliverable: {did}",
            "",
            '[.striped,cols="1,2,1,2",options="header"]',
            "|===",
            "|Version |Release |Date |Downloads",
            "",
        ]

        for rel in rels:
            version = rel["version"]
            name = rel["name"] or version
            date = rel["date"]
            html_url = rel["html_url"]

            badges = []
            if rel.get("is_latest"):
                badges.append("icon:star[role=text-warning,title=Latest]")
            if rel.get("is_featured") and not rel.get("is_latest"):
                badges.append("icon:bookmark[role=text-info,title=ANR Submission]")
            badge_str = " ".join(badges)
            if badge_str:
                badge_str = " " + badge_str

            downloads = []
            downloads.append(f"link:{html_url}[icon:tag[title=Release]]")
            for pdf in rel["pdfs"]:
                downloads.append(f"link:{pdf['url']}[icon:file-pdf[title=PDF,role=text-danger]]")

            name = name.replace("|", "\\|")

            lines.append(f"|*{version}*{badge_str}")
            lines.append(f"|{name}")
            lines.append(f"|{date}")
            lines.append(f"|{' '.join(downloads)}")
            lines.append("")

        lines.append("|===")

        content = "\n".join(lines)

        # Use sanitized deliverable ID for filename (D7.1 -> releases-d7-1.adoc)
        filename = f"releases-{did.lower().replace('.', '-')}.adoc"
        output_path = output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        print(f"  Saved partial: {output_path}")
        results[did] = content

    return results


def main():
    """Main entry point for GitHub releases harvesting."""
    parser = argparse.ArgumentParser(
        description="Harvest Exa-MA deliverable releases from GitHub"
    )
    parser.add_argument(
        "-o", "--output", help="Output file path (prints to stdout if not specified)"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "asciidoc"],
        default="asciidoc",
        help="Output format (default: asciidoc)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to config YAML file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Show only the latest release per deliverable",
    )
    parser.add_argument(
        "--partials-dir",
        type=Path,
        help="Output directory for Antora partial files (one per deliverable)",
    )

    args = parser.parse_args()

    config = load_config(args.config)
    releases = fetch_all_deliverables(config, latest_only=args.latest_only)

    if not releases:
        print("No releases found.")
        return

    print(f"\nTotal releases retrieved: {len(releases)}")

    if args.partials_dir:
        output_partials(releases, config, args.partials_dir)
    elif args.format == "json":
        output_json(releases, config, args.output)
    else:
        output_asciidoc(releases, config, args.output)


if __name__ == "__main__":
    main()
