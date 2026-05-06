"""Generate Exa-MA highlight partials from YAML metadata."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path(__file__).parent.parent / "highlights.yaml"
DEFAULT_UNIFIED_CONFIG = Path(__file__).parent.parent / "exama.yaml"
DEFAULT_PARTIALS_DIR = Path("docs/modules/ROOT/partials")


def load_config(config_path: Path) -> dict[str, Any]:
    """Load highlights configuration from YAML."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config_with_fallback(config_path: Path | None = None) -> dict[str, Any]:
    """Load highlights config from explicit path, exama.yaml, or highlights.yaml."""
    if config_path:
        return load_config(config_path)

    if DEFAULT_UNIFIED_CONFIG.exists():
        unified = load_config(DEFAULT_UNIFIED_CONFIG)
        source = unified.get("sources", {}).get("highlights", {})
        highlights_file = source.get("file")
        if highlights_file:
            return load_config(DEFAULT_UNIFIED_CONFIG.parent / highlights_file)

    return load_config(DEFAULT_CONFIG)


def resolve_partials_dir(config_path: Path | None = None) -> Path:
    """Resolve the default Antora partials directory."""
    unified_config = config_path or DEFAULT_UNIFIED_CONFIG
    if unified_config.exists():
        config = load_config(unified_config)
        partials_dir = config.get("output", {}).get("partials_dir")
        if partials_dir:
            return Path(partials_dir)
    return DEFAULT_PARTIALS_DIR


def generate_highlight_cards(highlights: list[dict[str, Any]]) -> list[str]:
    """Generate highlight cards."""
    if not highlights:
        return ["_No highlights listed._"]

    lines = ["[.grid.grid-2.gap-2]", "===="]
    for item in highlights:
        icon = item.get("icon", "star")
        role = item.get("role", "text-primary")
        title = item.get("title", "Untitled Highlight")
        page = item.get("page", "")
        summary = item.get("summary", "").strip()

        lines.extend(
            [
                "[.text-center]",
                "____",
                f"icon:{icon}[size=3x,role={role}]",
                "",
            ]
        )
        if page:
            lines.append(f"*xref:{page}[{title}]*")
        else:
            lines.append(f"*{title}*")
        lines.extend(["", summary, "____", ""])

    lines.append("====")
    return lines


def highlights_for_year(config: dict[str, Any], year: int) -> list[dict[str, Any]]:
    """Return highlights for a given year."""
    return [
        item
        for item in config.get("highlights", [])
        if int(item.get("year", 0)) == year
    ]


def output_partials(config: dict[str, Any], output_dir: Path) -> dict[str, str]:
    """Generate current and yearly highlight partials."""
    output_dir.mkdir(parents=True, exist_ok=True)
    highlights = config.get("highlights", [])
    current_year = int(config.get("current_year") or max(item["year"] for item in highlights))
    years = sorted({int(item["year"]) for item in highlights}, reverse=True)
    results: dict[str, str] = {}

    current = highlights_for_year(config, current_year)
    current_content = "\n".join(generate_highlight_cards(current))
    current_path = output_dir / "highlights-current.adoc"
    current_path.write_text(current_content, encoding="utf-8")
    print(f"  Saved partial: {current_path}")
    results["current"] = current_content

    for year in years:
        year_items = highlights_for_year(config, year)
        year_content = "\n".join(generate_highlight_cards(year_items))
        year_path = output_dir / f"highlights-{year}.adoc"
        year_path.write_text(year_content, encoding="utf-8")
        print(f"  Saved partial: {year_path}")
        results[str(year)] = year_content

    return results


def main() -> None:
    """Main entry point for highlight generation."""
    parser = argparse.ArgumentParser(
        description="Generate Exa-MA highlight partials from YAML metadata"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to config file (default: exama.yaml or highlights.yaml)",
    )
    parser.add_argument(
        "--partials-dir",
        type=Path,
        help=(
            "Output directory for Antora partial files "
            "(default: output.partials_dir from exama.yaml, or docs/modules/ROOT/partials)"
        ),
    )

    args = parser.parse_args()
    config = load_config_with_fallback(args.config)
    print(f"Loaded {len(config.get('highlights', []))} highlights")
    output_partials(config, args.partials_dir or resolve_partials_dir(args.config))


if __name__ == "__main__":
    main()
