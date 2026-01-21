# Exa-MA Tools

CLI tools for the Exa-MA project, including harvesting publications and deliverable releases.

Package name: `exa-ma-tools`

## Installation

```bash
# With uv (recommended)
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# With pip
pip install -e .
```

## Usage

### Harvest HAL Publications

```bash
# Output AsciiDoc to stdout
exa-ma-harvest-hal

# Save to file
exa-ma-harvest-hal -o publications.adoc

# JSON format
exa-ma-harvest-hal -f json -o publications.json

# Filter by years
exa-ma-harvest-hal -y 2024,2025
```

HAL output now includes both the raw HAL document type (`type` / `hal_doc_type`) and a normalized, user-friendly publication type:
- `publication_type` (e.g. `preprint`, `journal-article`, `conference-paper`, `report`)
- `publication_type_label` (e.g. "Preprint / unpublished", "Article in journal", "Conference paper")

### Harvest GitHub Releases

```bash
# Output AsciiDoc to stdout
exa-ma-harvest-releases

# Save to file
exa-ma-harvest-releases -o deliverables.adoc

# Show only latest releases
exa-ma-harvest-releases --latest-only

# Custom config file
exa-ma-harvest-releases -c custom-deliverables.yaml
```

### Run All Harvesting

```bash
# Run all harvesting operations
exa-ma-harvest-all all --output-dir ./output

# Just HAL
exa-ma-harvest-all hal -o publications.adoc

# Just releases
exa-ma-harvest-all releases -o deliverables.adoc
```

## Configuration

Edit `deliverables.yaml` to configure which deliverable repositories to harvest:

```yaml
settings:
  max_releases: 5
  include_prereleases: false

deliverables:
  - id: "D7.1"
    repo: "numpex/exa-ma-d7.1"
    title: "Research, Software Development & Benchmarking"
    featured_versions:
      - "v2.0.0"
      - "v1.1.1"
```

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run linting
ruff check .

# Run type checking
mypy .
```
