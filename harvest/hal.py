"""
Harvest Exa-MA publications from HAL (Hyper Articles en Ligne) archive.

This module queries the HAL API to retrieve publications related to the Exa-MA project,
filtering by scientific domains and publication years.

Supports configuration from:
- Command line arguments (highest priority)
- Unified exama.yaml config file
- Default values (fallback)
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Import is conditional to avoid circular imports and allow standalone usage
try:
    from .config import ExaMAConfig, load_config as load_exama_config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

# HAL API endpoint
HAL_API_URL = "https://api.archives-ouvertes.fr/search/"

# Default search parameters matching the Exa-MA deliverables query
# ANR-22-EXNU-0002 is the official ANR project identifier for Exa-MA
# Using anrProjectReference_s field for precise matching (not general text search)
DEFAULT_ANR_PROJECT = "ANR-22-EXNU-0002"
DEFAULT_QUERY = f"anrProjectReference_s:{DEFAULT_ANR_PROJECT}"
DEFAULT_DOMAINS = ["math", "info", "stat", "phys"]
DEFAULT_YEARS = [2023, 2024, 2025]
DEFAULT_ROWS = 100  # Max results per request

# Fields to retrieve from HAL
FIELDS = [
    "docid",
    "halId_s",
    "version_i",
    "uri_s",
    "doiId_s",
    "title_s",
    "authFullName_s",
    "producedDate_s",
    "publicationDateY_i",
    "docType_s",
    "docTypeLabel_s",
    "journalTitle_s",
    "conferenceTitle_s",
    "abstract_s",
    "keyword_s",
    "domain_s",
    "openAccess_bool",
    "citationFull_s",
    "fileMain_s",
]


# HAL document type codes to normalized publication types.
#
# Notes:
# - HAL uses short codes like ART/COMM/REPORT/etc.
# - This mapping intentionally stays coarse and user-facing.
HAL_DOC_TYPE_TO_PUBLICATION_TYPE: dict[str, tuple[str, str]] = {
    # Peer-reviewed / scholarly
    "ART": ("journal-article", "Article in journal"),
    "COMM": ("conference-paper", "Conference paper"),
    "COUV": ("book-chapter", "Book chapter"),
    "OUV": ("book", "Book"),
    # Grey literature / theses
    "REPORT": ("report", "Report"),
    "THESE": ("thesis", "Thesis"),
    "HDR": ("thesis", "HDR"),
    # Other scholarly outputs
    "POSTER": ("poster", "Poster"),
    "PATENT": ("patent", "Patent"),
    "SOFTWARE": ("software", "Software"),
    "DATA": ("dataset", "Dataset"),
    # Catch-alls
    "UNDEFINED": ("preprint", "Preprint / unpublished"),
    "OTHER": ("other", "Other"),
}


def _first_str(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value) if value is not None else ""


def infer_publication_type(
    doc_type_code: str,
    *,
    doc_type_label: str = "",
    journal_title: str = "",
    conference_title: str = "",
    doi: str = "",
) -> dict[str, str]:
    """Infer a normalized publication type from HAL fields.

    Returns a small dict with:
      - publication_type: a stable, machine-friendly key
      - publication_type_label: user-friendly English label
      - hal_doc_type: raw HAL docType code
      - hal_doc_type_label: raw HAL label if available
    """

    code = (doc_type_code or "").strip()
    label = (doc_type_label or "").strip()

    if code in HAL_DOC_TYPE_TO_PUBLICATION_TYPE:
        normalized, normalized_label = HAL_DOC_TYPE_TO_PUBLICATION_TYPE[code]

        # HAL sometimes keeps docType as UNDEFINED/OTHER across versions, while
        # later versions gain journal/DOI metadata after validation/review.
        # In that case, infer a more specific "published" type.
        if normalized in {"preprint", "other"}:
            if journal_title or doi:
                normalized, normalized_label = ("journal-article", "Article in journal")
            elif conference_title:
                normalized, normalized_label = ("conference-paper", "Conference paper")

        return {
            "publication_type": normalized,
            "publication_type_label": normalized_label,
            "hal_doc_type": code,
            "hal_doc_type_label": label,
        }

    # Heuristic fallback when docType is missing/unknown.
    if journal_title or doi:
        normalized, normalized_label = ("journal-article", "Article in journal")
    elif conference_title:
        normalized, normalized_label = ("conference-paper", "Conference paper")
    else:
        normalized, normalized_label = ("other", "Other")

    return {
        "publication_type": normalized,
        "publication_type_label": normalized_label,
        "hal_doc_type": code,
        "hal_doc_type_label": label,
    }


def _score_publication_version(pub: dict[str, Any]) -> tuple[int, int, str]:
    """Score HAL record for selecting best version for the same HAL id.

    Higher is better.
    Primary goal: prefer records that look 'published' (journal/DOI metadata)
    over earlier preprint versions, then pick the highest version number.
    """

    doc_type_code = _first_str(pub.get("docType_s", "")).strip()
    journal_title = _first_str(pub.get("journalTitle_s", "")).strip()
    conference_title = _first_str(pub.get("conferenceTitle_s", "")).strip()
    doi = _first_str(pub.get("doiId_s", "")).strip()

    score = 0
    if doc_type_code == "ART" or journal_title or doi:
        score += 30
    if doi:
        score += 10
    if doc_type_code == "COMM" or conference_title:
        score += 20
    if doc_type_code in {"COUV", "OUV", "REPORT", "THESE", "HDR"}:
        score += 15

    version = pub.get("version_i")
    try:
        version_i = int(version) if version is not None else 0
    except (TypeError, ValueError):
        version_i = 0

    produced_date = _first_str(pub.get("producedDate_s", ""))
    return (score, version_i, produced_date)


def select_best_versions(publications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate publications by HAL id, selecting the best available version."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for pub in publications:
        key = (
            _first_str(pub.get("halId_s", "")).strip()
            or _first_str(pub.get("uri_s", "")).strip()
            or str(pub.get("docid", "")).strip()
        )
        grouped.setdefault(key, []).append(pub)

    selected: list[dict[str, Any]] = []
    for _, pubs in grouped.items():
        best = max(pubs, key=_score_publication_version)
        best_copy = dict(best)
        best_copy["_hal_versions_found_i"] = len(pubs)
        selected.append(best_copy)

    selected.sort(key=lambda x: _first_str(x.get("producedDate_s", "")), reverse=True)
    return selected


def build_query_params(
    query: str = DEFAULT_QUERY,
    domains: list[str] | None = None,
    years: list[int] | None = None,
    rows: int = DEFAULT_ROWS,
    start: int = 0,
) -> dict[str, Any]:
    """Build HAL API query parameters."""
    if domains is None:
        domains = DEFAULT_DOMAINS
    if years is None:
        years = DEFAULT_YEARS

    # Build domain filter: level0_domain_s:(math OR info OR stat OR phys)
    domain_filter = " OR ".join(domains)

    # Build year filter: publicationDateY_i:(2024 OR 2025)
    year_filter = " OR ".join(str(y) for y in years)

    params = {
        "q": query,
        "fq": [
            f"level0_domain_s:({domain_filter})",
            f"publicationDateY_i:({year_filter})",
        ],
        "fl": ",".join(FIELDS),
        "rows": str(rows),
        "start": str(start),
        "sort": "producedDate_s desc",
        "wt": "json",
    }

    return params


def fetch_publications(
    query: str = DEFAULT_QUERY,
    domains: list[str] | None = None,
    years: list[int] | None = None,
    verbose: bool = True,
) -> list[dict[str, Any]]:
    """Fetch all publications matching the query from HAL API."""
    all_publications = []
    start = 0
    total = None

    if verbose:
        print(f"Searching HAL for: {query}")
        print(f"Domains: {domains or DEFAULT_DOMAINS}")
        print(f"Years: {years or DEFAULT_YEARS}")
        print()

    while True:
        params = build_query_params(
            query=query,
            domains=domains,
            years=years,
            start=start,
        )

        # Build URL with multiple fq parameters
        base_params = {k: v for k, v in params.items() if k != "fq"}
        url = HAL_API_URL + "?" + urlencode(base_params)
        for fq in params["fq"]:
            url += "&fq=" + fq.replace(" ", "+")

        try:
            request = Request(url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
            sys.exit(1)
        except URLError as e:
            print(f"URL Error: {e.reason}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}", file=sys.stderr)
            sys.exit(1)

        response_data = data.get("response", {})
        if total is None:
            total = response_data.get("numFound", 0)
            if verbose:
                print(f"Found {total} publications")

        docs = response_data.get("docs", [])
        if not docs:
            break

        all_publications.extend(docs)
        start += len(docs)

        if verbose:
            print(f"  Fetched {len(all_publications)}/{total} publications...")

        if start >= total:
            break

    return select_best_versions(all_publications)


def format_publication(pub: dict[str, Any]) -> dict[str, Any]:
    """Format a publication record for output."""
    # Handle fields that may be lists or single values
    title = _first_str(pub.get("title_s", ""))
    authors = pub.get("authFullName_s", [])
    if isinstance(authors, str):
        authors = [authors]

    doc_type_code = _first_str(pub.get("docType_s", ""))
    doc_type_label = _first_str(pub.get("docTypeLabel_s", ""))
    journal_title = _first_str(pub.get("journalTitle_s", ""))
    conference_title = _first_str(pub.get("conferenceTitle_s", ""))
    doi = _first_str(pub.get("doiId_s", ""))
    type_info = infer_publication_type(
        doc_type_code,
        doc_type_label=doc_type_label,
        journal_title=journal_title,
        conference_title=conference_title,
        doi=doi,
    )

    return {
        **type_info,
        "hal_id": pub.get("halId_s", ""),
        "hal_version": pub.get("version_i", ""),
        "hal_versions_found": pub.get("_hal_versions_found_i", ""),
        "url": pub.get("uri_s", ""),
        "title": title,
        "authors": authors,
        "date": pub.get("producedDate_s", ""),
        "year": pub.get("publicationDateY_i", ""),
        # Backward-compatible raw HAL code (kept for existing consumers)
        "type": doc_type_code,
        "journal": journal_title,
        "conference": conference_title,
        "doi": doi,
        "abstract": (
            pub.get("abstract_s", [""])[0]
            if isinstance(pub.get("abstract_s"), list)
            else pub.get("abstract_s", "")
        ),
        "keywords": pub.get("keyword_s", []),
        "domains": pub.get("domain_s", []),
        "open_access": pub.get("openAccess_bool", False),
        "citation": pub.get("citationFull_s", ""),
        "pdf_url": pub.get("fileMain_s", ""),
    }


def output_json(publications: list[dict], output_file: str | Path | None = None) -> str:
    """Output publications as JSON."""
    formatted = [format_publication(p) for p in publications]
    result = {
        "metadata": {
            "source": "HAL - Hyper Articles en Ligne",
            "project": "Exa-MA (ANR-22-EXNU-0002)",
            "anr_project_id": DEFAULT_ANR_PROJECT,
            "query": DEFAULT_QUERY,
            "harvested_at": datetime.now().isoformat(),
            "total_count": len(formatted),
        },
        "publications": formatted,
    }

    content = json.dumps(result, indent=2, ensure_ascii=False)

    if output_file:
        Path(output_file).write_text(content, encoding="utf-8")
        print(f"\nSaved to {output_file}")
    else:
        print(content)

    return content


def output_csv(publications: list[dict], output_file: str | Path | None = None) -> str:
    """Output publications as CSV."""
    formatted = [format_publication(p) for p in publications]

    fieldnames = [
        "hal_id",
        "hal_version",
        "hal_versions_found",
        "title",
        "authors",
        "year",
        "type",
        "publication_type",
        "publication_type_label",
        "journal",
        "conference",
        "doi",
        "url",
        "pdf_url",
        "open_access",
    ]

    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for pub in formatted:
        row = {
            **pub,
            "authors": "; ".join(pub["authors"]),
        }
        writer.writerow(row)

    content = output.getvalue()

    if output_file:
        Path(output_file).write_text(content, encoding="utf-8")
        print(f"\nSaved to {output_file}")
    else:
        print(content)

    return content


def _compute_statistics(publications: list[dict]) -> dict:
    """Compute publication statistics."""
    from collections import Counter
    
    stats = {
        "total": len(publications),
        "by_type": Counter(),
        "by_year": {},
        "with_doi": 0,
        "with_pdf": 0,
        "open_access": 0,
        "by_domain": Counter(),
    }
    
    for pub in publications:
        # Type statistics
        pub_type = pub.get("publication_type_label", "Unknown")
        stats["by_type"][pub_type] += 1
        
        # DOI and PDF
        if pub.get("doi"):
            stats["with_doi"] += 1
        if pub.get("pdf_url"):
            stats["with_pdf"] += 1
        if pub.get("open_access"):
            stats["open_access"] += 1
            
        # Domain statistics
        domains = pub.get("domains", [])
        if isinstance(domains, list):
            for domain in domains:
                stats["by_domain"][domain] += 1
        
        # Per-year statistics
        year = pub.get("year", "Unknown")
        if year not in stats["by_year"]:
            stats["by_year"][year] = {
                "count": 0,
                "by_type": Counter(),
            }
        stats["by_year"][year]["count"] += 1
        stats["by_year"][year]["by_type"][pub_type] += 1
    
    return stats


def _format_statistics_asciidoc(stats: dict) -> list[str]:
    """Format statistics as AsciiDoc."""
    lines = []
    
    # Map publication types to Font Awesome icons
    type_icons = {
        "Article in journal": "newspaper",
        "Preprint / unpublished": "file-alt",
        "Conference paper": "users",
        "Poster": "image",
        "Report": "file-text",
        "Thesis": "graduation-cap",
        "PhD": "graduation-cap",
        "HDR": "user-graduate",
        "Book": "book",
        "Book chapter": "book-open",
        "Software": "code",
        "Dataset": "database",
        "Patent": "certificate",
    }
    
    # Global statistics section
    lines.extend([
        "== icon:chart-pie[] Overview",
        "",
        f"icon:list-ol[] Total publications: *{stats['total']}*",
        "",
    ])
    
    # Publication type distribution
    if stats["by_type"]:
        lines.extend([
            "[.grid.grid-2.gap-2]",
            "====",
        ])
        
        for pub_type, count in stats["by_type"].most_common():
            pct = (count / stats["total"] * 100) if stats["total"] > 0 else 0
            icon = type_icons.get(pub_type, "file")
            lines.extend([
                "____",
                f"icon:{icon}[size=2x,role=text-primary] *{count}* {pub_type}",
                "",
                f"_{pct:.1f}% of total_",
                "____",
                "",
            ])
        
        lines.extend([
            "====",
            "",
        ])
    
    # Access statistics
    lines.extend([
        "=== icon:unlock[] Access & Availability",
        "",
        f"* icon:fingerprint[] Publications with DOI: *{stats['with_doi']}* ({stats['with_doi']/stats['total']*100:.1f}%)",
        f"* icon:file-pdf[] Publications with PDF: *{stats['with_pdf']}* ({stats['with_pdf']/stats['total']*100:.1f}%)",
        f"* icon:lock-open[] Open Access: *{stats['open_access']}* ({stats['open_access']/stats['total']*100:.1f}%)",
        "",
    ])
    
    # Domain distribution
    if stats["by_domain"]:
        lines.extend([
            "=== icon:flask[] By Scientific Domain",
            "",
        ])
        for domain, count in stats["by_domain"].most_common(5):
            lines.append(f"* icon:atom[] {domain}: *{count}*")
        lines.append("")
    
    return lines


def output_asciidoc(
    publications: list[dict], output_file: str | Path | None = None, partial: bool = False
) -> str:
    """Output publications as AsciiDoc with tables grouped by year.

    Args:
        publications: List of publication records from HAL
        output_file: Optional file path to write output
        partial: If True, output only the tables (for Antora partials)
    """
    formatted = [format_publication(p) for p in publications]

    # Sort by date (newest first) then group by year
    formatted.sort(key=lambda x: x.get("date", ""), reverse=True)

    by_year: dict[int | str, list] = {}
    for pub in formatted:
        year = pub.get("year", "Unknown")
        by_year.setdefault(year, []).append(pub)

    # Compute statistics
    stats = _compute_statistics(formatted)

    lines = []

    if not partial:
        lines.extend([
            "= Exa-MA Publications",
            ":page-layout: default",
            f":generated: {datetime.now().strftime('%Y-%m-%d')}",
            ":icons: font",
            "",
            "[.lead]",
            f"Publications acknowledging the Exa-MA project (ANR-22-EXNU-0002). "
            f"Total: *{len(formatted)}* publications.",
            "",
        ])
        # Add statistics for full page
        lines.extend(_format_statistics_asciidoc(stats))
    else:
        # Add statistics comment for partials
        lines.append(f"// Total publications: {len(formatted)}")
        lines.append("")
        # Include statistics in partials too
        lines.extend(_format_statistics_asciidoc(stats))

    for year in sorted(by_year.keys(), reverse=True):
        pubs = by_year[year]
        year_stats = stats["by_year"].get(year, {})
        
        lines.append(f"== {year}")
        lines.append("")
        lines.append(f"_{len(pubs)} publication{'s' if len(pubs) > 1 else ''}_")
        lines.append("")
        
        # Per-year type breakdown
        if year_stats.get("by_type"):
            type_summary = ", ".join(
                f"{count} {pub_type}" 
                for pub_type, count in year_stats["by_type"].most_common()
            )
            lines.append(f"_{type_summary}_")
            lines.append("")
        
        lines.append('[.striped.publications,cols="4,2,2,1",options="header"]')
        lines.append("|===")
        lines.append("|Title |Authors |Type |Links")
        lines.append("")

        for pub in pubs:
            # Format authors (max 3, then "et al.")
            authors = pub["authors"][:3]
            author_str = ", ".join(authors)
            if len(pub["authors"]) > 3:
                author_str += " et al."

            # Escape pipe characters in title
            title = pub["title"].replace("|", "\\|")

            # Prefer normalized label; fall back to HAL code.
            pub_type = (
                pub.get("publication_type_label")
                or pub.get("hal_doc_type_label")
                or pub.get("type")
                or ""
            )
            pub_type = str(pub_type).replace("|", "\\|")

            # Build links
            links = []
            links.append(f"link:{pub['url']}[icon:external-link-alt[title=HAL]]")
            if pub["pdf_url"]:
                links.append(f"link:{pub['pdf_url']}[icon:file-pdf[title=PDF]]")

            lines.append(f"|*{title}*")
            lines.append(f"|{author_str}")
            lines.append(f"|{pub_type}")
            lines.append(f"|{' '.join(links)}")
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


def output_bibtex(publications: list[dict], output_file: str | Path | None = None) -> str:
    """Output publications as BibTeX."""
    formatted = [format_publication(p) for p in publications]
    entries = []

    for pub in formatted:
        hal_id = pub["hal_id"].replace("-", "_")
        entry_type = {
            "ART": "article",
            "COMM": "inproceedings",
            "THESE": "phdthesis",
            "REPORT": "techreport",
            "POSTER": "misc",
            "COUV": "incollection",
            "OUV": "book",
            "UNDEFINED": "misc",
        }.get(pub["type"], "misc")

        authors = " and ".join(pub["authors"])
        title = pub["title"].replace("{", "\\{").replace("}", "\\}")

        entry = [f"@{entry_type}{{{hal_id},"]
        entry.append(f"  author = {{{authors}}},")
        entry.append(f"  title = {{{{{title}}}}},")
        entry.append(f'  year = {{{pub["year"]}}},')

        if pub["journal"]:
            entry.append(f'  journal = {{{pub["journal"]}}},')
        if pub["conference"]:
            entry.append(f'  booktitle = {{{pub["conference"]}}},')

        entry.append(f'  url = {{{pub["url"]}}},')
        entry.append(f'  hal_id = {{{pub["hal_id"]}}},')
        entry.append("}")

        entries.append("\n".join(entry))

    content = "\n\n".join(entries)

    if output_file:
        Path(output_file).write_text(content, encoding="utf-8")
        print(f"\nSaved to {output_file}")
    else:
        print(content)

    return content


def main():
    """Main entry point for HAL harvesting."""
    parser = argparse.ArgumentParser(description="Harvest Exa-MA publications from HAL archive")
    parser.add_argument("-o", "--output", help="Output file path (prints to stdout if not specified)")
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "csv", "asciidoc", "bibtex"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to exama.yaml config file (uses defaults if not specified)",
    )
    parser.add_argument(
        "-q",
        "--query",
        help=f"Search query (default: {DEFAULT_QUERY})",
    )
    parser.add_argument(
        "-y",
        "--years",
        help="Comma-separated years to filter (default: 2023,2024,2025)",
    )
    parser.add_argument(
        "-d",
        "--domains",
        help="Comma-separated domains (default: math,info,stat,phys)",
    )
    parser.add_argument(
        "--partials-dir",
        type=Path,
        help="Output directory for Antora partial file (publications-hal.adoc)",
    )

    args = parser.parse_args()

    # Load configuration from unified config file if available
    query = DEFAULT_QUERY
    years = DEFAULT_YEARS
    domains = DEFAULT_DOMAINS

    if HAS_CONFIG and args.config:
        try:
            config = load_exama_config(args.config)
            pub_config = config.get_publications_config()
            query = pub_config.query
            years = pub_config.years
            domains = pub_config.domains
            print(f"Loaded configuration from: {args.config}")
        except FileNotFoundError:
            print(f"Config file not found: {args.config}, using defaults", file=sys.stderr)
        except Exception as e:
            print(f"Error loading config: {e}, using defaults", file=sys.stderr)
    elif HAS_CONFIG:
        # Try to auto-discover config file
        try:
            config = load_exama_config()
            pub_config = config.get_publications_config()
            query = pub_config.query
            years = pub_config.years
            domains = pub_config.domains
        except FileNotFoundError:
            pass  # Use defaults

    # CLI args override config
    if args.query:
        query = args.query
    if args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    if args.domains:
        domains = [d.strip() for d in args.domains.split(",")]

    publications = fetch_publications(
        query=query,
        domains=domains,
        years=years,
    )

    if not publications:
        print("No publications found.")
        return

    print(f"\nTotal publications retrieved: {len(publications)}")

    if args.partials_dir:
        args.partials_dir.mkdir(parents=True, exist_ok=True)
        output_file = args.partials_dir / "publications-hal.adoc"
        output_asciidoc(publications, output_file, partial=True)
    elif args.format == "asciidoc":
        output_asciidoc(publications, args.output, partial=False)
    else:
        output_funcs = {
            "json": output_json,
            "csv": output_csv,
            "bibtex": output_bibtex,
        }
        output_funcs[args.format](publications, args.output)


if __name__ == "__main__":
    main()
