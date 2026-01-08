"""
Harvest Exa-MA publications from HAL (Hyper Articles en Ligne) archive.

This module queries the HAL API to retrieve publications related to the Exa-MA project,
filtering by scientific domains and publication years.
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
    "uri_s",
    "title_s",
    "authFullName_s",
    "producedDate_s",
    "publicationDateY_i",
    "docType_s",
    "journalTitle_s",
    "conferenceTitle_s",
    "abstract_s",
    "keyword_s",
    "domain_s",
    "openAccess_bool",
    "citationFull_s",
    "fileMain_s",
]


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

    return all_publications


def format_publication(pub: dict[str, Any]) -> dict[str, Any]:
    """Format a publication record for output."""
    # Handle fields that may be lists or single values
    title = (
        pub.get("title_s", [""])[0]
        if isinstance(pub.get("title_s"), list)
        else pub.get("title_s", "")
    )
    authors = pub.get("authFullName_s", [])
    if isinstance(authors, str):
        authors = [authors]

    return {
        "hal_id": pub.get("halId_s", ""),
        "url": pub.get("uri_s", ""),
        "title": title,
        "authors": authors,
        "date": pub.get("producedDate_s", ""),
        "year": pub.get("publicationDateY_i", ""),
        "type": pub.get("docType_s", ""),
        "journal": pub.get("journalTitle_s", ""),
        "conference": pub.get("conferenceTitle_s", ""),
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
        "title",
        "authors",
        "year",
        "type",
        "journal",
        "conference",
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
    else:
        # Add generation comment for partials
        lines.append(f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"// Total publications: {len(formatted)}")
        lines.append("")

    for year in sorted(by_year.keys(), reverse=True):
        pubs = by_year[year]
        lines.append(f"== {year}")
        lines.append("")
        lines.append(f"_{len(pubs)} publication{'s' if len(pubs) > 1 else ''}_")
        lines.append("")
        lines.append('[.striped.publications,cols="4,2,1",options="header"]')
        lines.append("|===")
        lines.append("|Title |Authors |Links")
        lines.append("")

        for pub in pubs:
            # Format authors (max 3, then "et al.")
            authors = pub["authors"][:3]
            author_str = ", ".join(authors)
            if len(pub["authors"]) > 3:
                author_str += " et al."

            # Escape pipe characters in title
            title = pub["title"].replace("|", "\\|")

            # Build links
            links = []
            links.append(f"link:{pub['url']}[icon:external-link-alt[title=HAL]]")
            if pub["pdf_url"]:
                links.append(f"link:{pub['pdf_url']}[icon:file-pdf[title=PDF]]")

            lines.append(f"|*{title}*")
            lines.append(f"|{author_str}")
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
        "-q",
        "--query",
        default=DEFAULT_QUERY,
        help=f"Search query (default: {DEFAULT_QUERY})",
    )
    parser.add_argument(
        "-y",
        "--years",
        default="2023,2024,2025",
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
