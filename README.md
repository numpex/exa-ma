# Exa-MA Documentation

[![Website](https://img.shields.io/website?url=https%3A%2F%2Fexama.numpex.org&label=docs)](https://exama.numpex.org)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![GitHub last commit](https://img.shields.io/github/last-commit/numpex/exama)](https://github.com/numpex/exama/commits/main)
[![Antora](https://img.shields.io/badge/docs-Antora-blue)](https://antora.org)

Documentation site for the **Exa-MA** (Methods and Algorithms for Exascale Computing) project, part of the [PEPR NumPEx](https://numpex.org) initiative.

## Overview

Exa-MA develops advanced numerical methods and software for exascale computing across seven scientific work packages:

- **WP1** - Discretization (meshing, adaptivity, high-order schemes)
- **WP2** - Model Reduction & Scientific ML (ROMs, PINNs, neural operators)
- **WP3** - Solvers (domain decomposition, preconditioners, multiphysics)
- **WP4** - Inverse Problems & Data Assimilation
- **WP5** - Optimization (Bayesian, shape/topology)
- **WP6** - Uncertainty Quantification
- **WP7** - Showroom & Benchmarking (CI/CD, co-design)

The documentation is built using [Antora](https://antora.org/) with the [Feel++ Antora UI](https://github.com/feelpp/antora-ui) card catalog system.

## Building the Documentation

### Prerequisites

- Node.js (v16 or later)
- npm

### Quick Start

```bash
# Install dependencies
npm install

# Build the documentation
npm run antora

# Serve locally
npm start
```

### Available Scripts

- `npm run antora` - Build the documentation site
- `npm run clean-cache` - Clear the Antora cache (UI bundle, content cache)
- `npm run validate` - Validate cross-references
- `npm start` - Serve the built site locally

## Troubleshooting

### Cards Not Showing in Catalog Pages

If the card catalog system is not displaying cards on pages like the home page or work packages page, the issue is likely a **stale UI bundle cache**.

**Symptoms:**
- Pages have `:page-layout: manuals` but render with default layout
- Build warnings: `Page layout specified by page not found: manuals`
- Body class shows `article` instead of `article docs-manuals-catalog docs-cards-layout`

**Solution:**
```bash
# Clear the UI cache
npm run clean-cache

# Rebuild
npm run antora
```

**Technical Details:**
The card catalog system requires:
- `layouts/manuals.hbs` layout
- `helpers/get-page-cards.js` and `helpers/get-page-cards-multi.js` helpers
- Proper page attributes (`:page-layout: manuals`, `:page-tags:`, `:parent-catalogs:`)

The latest Antora UI includes these components, but cached versions from before September 2025 may be missing them.

### Cache Management

Antora caches the UI bundle and content in the `cache/` directory:
- `cache/ui/` - UI bundle cache
- `cache/content/` - Content cache

To force a fresh build:
```bash
rm -rf cache/
npm run antora
```

Or use the clean-cache script:
```bash
npm run clean-cache
```

## Project Structure

```
exama/
├── docs/
│   ├── antora.yml           # Component descriptor
│   ├── modules/
│   │   ├── ROOT/            # Main documentation module
│   │   │   ├── pages/
│   │   │   │   ├── index.adoc        # Home page
│   │   │   │   ├── team.adoc         # Team members
│   │   │   │   ├── workgroups.adoc   # Working groups
│   │   │   │   ├── workpackages.adoc # Work packages catalog
│   │   │   │   ├── results.adoc      # Research highlights
│   │   │   │   ├── wp1/ to wp7/      # Work package pages
│   │   │   │   └── highlights/       # Highlight articles
│   │   │   ├── images/               # Module images
│   │   │   └── nav.adoc              # Navigation
│   │   └── software/        # Software catalog module
│   │       ├── pages/
│   │       │   ├── index.adoc        # Software overview
│   │       │   └── *.adoc            # Individual software pages
│   │       └── nav.adoc
│   └── antora/              # Supplemental UI files
├── site.yml                 # Antora playbook
├── package.json             # Node.js dependencies
└── public/                  # Built site (generated)
```

## Configuration

### UI Bundle

The site uses the Feel++ Antora UI from:
```yaml
ui:
  bundle:
    url: https://github.com/feelpp/antora-ui/releases/latest/download/ui-bundle.zip
    snapshot: true
```

The `snapshot: true` setting allows the cache to be updated, but you may need to manually clear it for major UI updates.

## Contributing

Documentation is written in AsciiDoc format in the `docs/modules/` directory.

### Adding Software Pages

Software pages in `docs/modules/software/pages/` are automatically displayed as cards on the software index. Add these attributes:

```asciidoc
= Software Name
:page-tags: software
:page-illustration: fa-solid fa-icon-name
:description: Brief description of the software.
```

### Adding Research Highlights

Highlight articles in `docs/modules/ROOT/pages/highlights/` appear automatically on the results page:

```asciidoc
= Highlight Title
:page-tags: highlight
:page-illustration: fa-solid fa-icon-name
:description: Brief description of the research highlight.
```

### Card Catalog System

The site uses an automatic card catalog system. To create a catalog page:

**Catalog page** (displays cards):
```asciidoc
= Catalog Page
:page-layout: manuals
:page-cards-tag: software
:page-cards-within-module: true
```

**Child page** (appears as card):
```asciidoc
= Page Title
:page-tags: software
:page-illustration: fa-solid fa-cube
:description: Page description for card.
```

## Harvest Tools

The `harvest/` package provides tools to fetch and generate documentation from various sources. All sources can be configured via a unified `exama.yaml` file.

### Installation

```bash
# Install the package in development mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Configuration

All data sources are configured in `exama.yaml`:

```yaml
project:
  name: "Exa-MA"
  anr_id: "ANR-22-EXNU-0002"

sources:
  publications:
    type: hal
    query: "anrProjectReference_s:ANR-22-EXNU-0002"
    domains: [math, info, stat, phys]
    years: [2023, 2024, 2025, 2026]

  deliverables:
    type: github
    items:
      - id: "D7.1"
        repo: "numpex/exa-ma-d7.1"
        title: "Research, Software Development & Benchmarking"

  software:
    type: google_sheets
    sheet_id: "19v57jpek52nQV2V0tBBON5ivGCz7Bqf3Gw-fHroVHkA"

  team:
    type: google_sheets
    sheet_id: "1-QuexB1IiP2O1ebNhp1OrQb6hOx8BXA5"
    sheet_name: "All Exa-MA"

  news:
    type: yaml
    file: "news.yaml"  # External file for easy maintenance
```

### Commands

```bash
# Harvest all sources at once (recommended)
exa-ma-harvest all --output-dir docs/modules/ROOT/partials/

# Individual subcommands
exa-ma-harvest hal -o publications.adoc
exa-ma-harvest releases -o deliverables.adoc
exa-ma-harvest team --output recruited.adoc
exa-ma-harvest news --partials-dir docs/modules/ROOT/partials/
exa-ma-harvest-software generate -o docs/modules/software/pages
```

### Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=harvest tests/
```

### Data Sources

| Source | Type | Description |
|--------|------|-------------|
| Publications | HAL API | Scientific publications from HAL archive |
| Deliverables | GitHub | Release information from deliverable repositories |
| Software | Google Sheets | Framework and application metadata |
| Team | Google Sheets | Recruited personnel (PhD, postdoc, engineers) |
| News | YAML | Events and announcements |

## Deployment

The site is automatically deployed to GitHub Pages on push to the main branch via GitHub Actions.

## Links

- **Live Site**: https://exama.numpex.org
- **NumPEx Portal**: https://numpex.org
- **GitHub Repository**: https://github.com/numpex/exama

## License

AGPL-3.0
