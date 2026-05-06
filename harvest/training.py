"""Generate Exa-MA training partials from YAML configuration."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path(__file__).parent.parent / "training.yaml"
DEFAULT_UNIFIED_CONFIG = Path(__file__).parent.parent / "exama.yaml"
DEFAULT_PARTIALS_DIR = Path("docs/modules/ROOT/partials")


def load_config(config_path: Path) -> dict[str, Any]:
    """Load training configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config_with_fallback(config_path: Path | None = None) -> dict[str, Any]:
    """Load training config from explicit path, exama.yaml, or training.yaml."""
    if config_path:
        return load_config(config_path)

    if DEFAULT_UNIFIED_CONFIG.exists():
        unified = load_config(DEFAULT_UNIFIED_CONFIG)
        training_source = unified.get("sources", {}).get("training", {})
        training_file = training_source.get("file")
        if training_file:
            return load_config(DEFAULT_UNIFIED_CONFIG.parent / training_file)

    return load_config(DEFAULT_CONFIG)


def resolve_partials_dir(config_path: Path | None = None) -> Path:
    """Resolve the default Antora partials directory."""
    unified_config = config_path or DEFAULT_UNIFIED_CONFIG
    if unified_config.exists():
        unified = load_config(unified_config)
        partials_dir = unified.get("output", {}).get("partials_dir")
        if partials_dir:
            return Path(partials_dir)
    return DEFAULT_PARTIALS_DIR


def format_date_range(item: dict[str, Any]) -> str:
    """Format a training date or date range for display."""
    start = item.get("date", "")
    end = item.get("end_date", "")

    if not start:
        return "TBD"

    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        if not end:
            return start_dt.strftime("%b %d, %Y")

        end_dt = datetime.strptime(end, "%Y-%m-%d")
        if start_dt.month == end_dt.month and start_dt.year == end_dt.year:
            return f"{start_dt.strftime('%b %d')}-{end_dt.strftime('%d, %Y')}"
        return f"{start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d, %Y')}"
    except ValueError:
        return start


def generate_training_catalog(trainings: list[dict[str, Any]]) -> list[str]:
    """Generate the training catalog partial."""
    if not trainings:
        return ["_No training sessions listed._"]

    upcoming = [item for item in trainings if item.get("status") == "upcoming"]
    archived = [item for item in trainings if item.get("status") == "archived"]
    other = [
        item
        for item in trainings
        if item.get("status") not in {"upcoming", "archived", "material"}
    ]
    materials = [item for item in trainings if item.get("status") == "material"]

    lines: list[str] = []

    if upcoming:
        lines.extend(["[discrete]", "== Upcoming Training", ""])
        lines.extend(generate_training_cards(upcoming, show_status=False))
        lines.append("")

    if archived:
        lines.extend(["[discrete]", "== Training Archive", ""])
        lines.extend(generate_training_cards(archived, show_status=False))
        lines.append("")

    if materials:
        lines.extend(["[discrete]", "== Training Materials", ""])
        lines.extend(generate_training_cards(materials, show_status=False))
        lines.append("")

    if other:
        lines.extend(["[discrete]", "== Other Training", ""])
        lines.extend(generate_training_cards(other, show_status=True))

    return lines


def generate_training_cards(
    trainings: list[dict[str, Any]],
    show_status: bool = True,
) -> list[str]:
    """Generate training cards."""
    trainings = sorted(trainings, key=lambda item: item.get("date", ""), reverse=True)
    lines = ["[.grid.grid-2.gap-2.items-start]", "--"]

    for item in trainings:
        icon = item.get("icon", "graduation-cap")
        title = item.get("title", "Untitled Training")
        status = item.get("status", "planned").title()
        date_str = format_date_range(item)
        location = item.get("location", "")
        description = item.get("description", "").strip().replace("\n", " ")
        organizers = item.get("organizers", [])
        topics = item.get("topics", [])
        resources = item.get("resources", [])
        url = item.get("url")

        lines.append("[.card]")
        lines.append("====")
        lines.append(f"icon:{icon}[size=2x,role=text-success] *{title}*")
        lines.append("")
        if item.get("date") or location or show_status:
            if item.get("date") and location:
                metadata = f"*{date_str}* | {location}"
            elif item.get("date"):
                metadata = f"*{date_str}*"
            else:
                metadata = location
            if show_status:
                metadata = f"{metadata} | {status}" if metadata else status
            lines.append(metadata)
            lines.append("")
        if description:
            lines.append(description)
            lines.append("")
        if organizers:
            lines.append(f"*Organizers:* {', '.join(organizers)}")
            lines.append("")
        if topics:
            lines.append(f"*Topics:* {'; '.join(topics)}")
            lines.append("")
        if resources:
            resource_links = []
            for resource in resources:
                label = resource.get("title", "Resource")
                resource_url = resource.get("url", "")
                if resource_url:
                    resource_links.append(f"{resource_url}[{label}]")
                else:
                    resource_links.append(label)
            lines.append("*Resources:* +")
            for idx, link in enumerate(resource_links):
                suffix = " +" if idx < len(resource_links) - 1 else ""
                lines.append(f"{link}{suffix}")
            lines.append("")
        if url:
            lines.append(f"{url}[Training details]")
        lines.append("====")
        lines.append("")

    lines.append("--")
    return lines


def output_partials(config: dict[str, Any], output_dir: Path) -> dict[str, str]:
    """Generate training partial files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    trainings = config.get("trainings", [])

    lines = [f"// Trainings: {len(trainings)}", ""]
    lines.extend(generate_training_catalog(trainings))

    content = "\n".join(lines)
    output_path = output_dir / "training-catalog.adoc"
    output_path.write_text(content, encoding="utf-8")
    print(f"  Saved partial: {output_path}")

    return {"catalog": content}


def main() -> None:
    """Main entry point for training generation."""
    parser = argparse.ArgumentParser(
        description="Generate Exa-MA training pages from YAML configuration"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to config file (default: exama.yaml or training.yaml)",
    )
    parser.add_argument(
        "--partials-dir",
        type=Path,
        help="Output directory for Antora partial files",
    )

    args = parser.parse_args()

    config = load_config_with_fallback(args.config)
    trainings = config.get("trainings", [])
    print(f"Loaded {len(trainings)} training sessions")

    output_dir = args.partials_dir or resolve_partials_dir(args.config)
    output_partials(config, output_dir)


if __name__ == "__main__":
    main()
