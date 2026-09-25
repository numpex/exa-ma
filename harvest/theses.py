"""Match doctoral researchers to theses.fr and render reusable, offline metadata.

API documentation: https://theses.fr/api/v1/recherche/openapi.yaml
Only an exact normalized author name AND a known supervisor can match automatically.
Name variants and additional supervisors require documented entries in theses.yaml.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

from .team import PositionType, fetch_recruited_with_config

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "theses.yaml"
DEFAULT_PARTIALS = ROOT / "docs/modules/ROOT/partials"
SEARCH_URL = "https://theses.fr/api/v1/theses/recherche/"


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def full_name(person: dict) -> str:
    return f"{person.get('prenom') or ''} {person.get('nom') or ''}".strip()


def search_theses(name: str) -> list[dict]:
    # An AND query tolerates the API's surname-first index; quoted full names do not.
    tokens = normalize_name(name).split()
    if not tokens:
        raise ValueError("A non-empty author name is required")
    query = "auteursNP:(" + " AND ".join(tokens) + ")"
    url = SEARCH_URL + "?" + urlencode({"q": query, "nombre": 100, "debut": 0})
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
    rows, total = data["theses"], data["totalHits"]
    if not isinstance(rows, list) or not isinstance(total, int) or total != len(rows):
        raise ValueError(f"Incomplete theses.fr response for {name}; refusing partial results")
    return rows


def select_thesis(person, candidates: list[dict], override: dict) -> tuple[dict | None, str]:
    """Reject homonyms, ambiguous results, and incompatible doctoral dates."""
    names = {normalize_name(person.full_name)}
    names.update(normalize_name(n) for n in override.get("author_names", []))
    advisors = {normalize_name(n) for n in person.advisors}
    advisors.update(normalize_name(n) for n in override.get("additional_supervisors", []))
    matches = {}
    for thesis in candidates:
        if not any(normalize_name(full_name(a)) in names for a in thesis["auteurs"]):
            continue
        if not any(normalize_name(full_name(a)) in advisors for a in thesis["directeurs"]):
            continue
        enrolled = thesis.get("datePremiereInscriptionDoctorat")
        defended = thesis.get("dateSoutenance")
        if person.start_date:
            if enrolled and abs((datetime.strptime(enrolled, "%d/%m/%Y") - person.start_date).days) > 366:
                continue
            if defended and datetime.strptime(defended, "%d/%m/%Y") < person.start_date:
                continue
        identifier = thesis["id"]
        if not re.fullmatch(r"[A-Za-z0-9]+", identifier) or not thesis.get("titrePrincipal"):
            raise ValueError("Invalid thesis identifier or missing title")
        matches[identifier] = thesis
    if len(matches) == 1:
        return next(iter(matches.values())), "matched"
    return None, "ambiguous" if matches else "not_verified"


def refresh_snapshot(collection, config: dict, previous: dict | None = None, search=search_theses) -> dict:
    """Build a complete snapshot in memory; failed requests never overwrite prior data."""
    today = date.today().isoformat()
    previous_people = (previous or {}).get("people", {})
    people = {}
    extras = set(config.get("agenda_people", []))
    # Filter before deduplication: the sheet can have earlier non-PhD rows for a person.
    roster = {p.slug: p for p in collection.personnel
              if p.position == PositionType.PHD and (p.funded_by_exama or p.slug in extras)
              and (p.start_date is None or p.start_date.date() <= date.today())}
    for slug, person in sorted(roster.items()):
        override = config.get("people", {}).get(slug, {})
        if override and not override.get("evidence"):
            raise ValueError(f"Document identity exceptions for {slug} with an evidence URL")
        candidates = search(person.full_name)
        thesis, status = select_thesis(person, candidates, override)
        record = {
            "name": person.full_name,
            "work_packages": person.work_packages,
            "funded_by_exama": person.funded_by_exama,
            "checked_on": today,
            "match_status": status,
        }
        if thesis:
            record["thesis"] = {
                "id": thesis["id"],
                "url": f"https://theses.fr/{thesis['id']}",
                "title": thesis["titrePrincipal"],
                "title_en": thesis.get("titreEN") or None,
                "authors": [full_name(a) for a in thesis["auteurs"]],
                "supervisors": [full_name(a) for a in thesis["directeurs"]],
                "institution": thesis.get("etabSoutenanceN"),
                "status": thesis.get("status"),
                "enrolled_on": thesis.get("datePremiereInscriptionDoctorat"),
                "defended_on": thesis.get("dateSoutenance"),
                "verified_on": today,
            }
        elif previous_people.get(slug, {}).get("thesis"):
            # Keep a previously verified title visible, but explicitly flag it as cached.
            record["thesis"] = previous_people[slug]["thesis"]
            record["match_status"] = "retained_previous"
        if override:
            record["identity_evidence"] = override["evidence"]
        people[slug] = record
    if not people:
        raise ValueError("No doctoral researchers found; refusing to replace the snapshot")
    # Preserve historical/agenda records if a person leaves the live roster.
    for slug, old in previous_people.items():
        if slug not in people:
            people[slug] = {**old, "in_current_roster": False}
    return {"source": SEARCH_URL, "checked_on": today, "people": people}


def escape_asciidoc(text: str) -> str:
    """Escape metadata as literal text, including table and link delimiters."""
    replacements = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "|": "&#124;",
                    "[": "&#91;", "]": "&#93;", "{": "&#123;", "}": "&#125;",
                    "*": "&#42;", "_": "&#95;", "`": "&#96;", "+": "&#43;",
                    "\\": "&#92;"}
    return "".join(replacements.get(c, c) for c in " ".join(text.split()))


def thesis_link(record: dict) -> str:
    thesis = record.get("thesis")
    if not thesis:
        return "Title not yet verified on theses.fr"
    link = f"{thesis['url']}[{escape_asciidoc(thesis['title'])}]"
    if record["match_status"] == "retained_previous":
        link += f" (last verified {thesis['verified_on']})"
    return link


def render_partials(snapshot: dict) -> dict[str, str]:
    attributes = ["// Generated by exa-ma-harvest theses; do not edit."]
    directory = [
        "// Generated by exa-ma-harvest theses; do not edit.", "",
        "Registered thesis titles are reproduced in their original language and linked to theses.fr.",
        "A missing match does not mean that the person is not enrolled in a PhD.", "",
        f"Last lookup: {snapshot['checked_on']}.", "",
        '[.striped,cols="2,1,5,2",options="header"]', "|===",
        "|Doctoral researcher |Work package |Thesis title |Doctoral institution", "",
    ]
    for slug, person in sorted(snapshot["people"].items(),
                               key=lambda item: (item[1]["work_packages"], item[1]["name"])):
        attributes.append(f":thesis-{slug}: {thesis_link(person)}")
        if not person["funded_by_exama"] or person.get("in_current_roster") is False:
            continue
        institution = (person.get("thesis") or {}).get("institution") or "—"
        directory.extend([
            f"|{escape_asciidoc(person['name'])}",
            f"|{', '.join(person['work_packages'])}",
            f"|{thesis_link(person)}",
            f"|{escape_asciidoc(institution)}", "",
        ])
    directory.extend(["|===", ""])
    return {"attributes.adoc": "\n".join(attributes) + "\n",
            "directory.adoc": "\n".join(directory)}


def harvest_theses(*, refresh=False, config_path=DEFAULT_CONFIG,
                   partials_dir=DEFAULT_PARTIALS, team_config=None) -> dict:
    output = Path(partials_dir) / "theses"
    snapshot_path = output / "data.json"
    previous = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else None
    if refresh:
        config = yaml.safe_load(Path(config_path).read_text()) or {}
        collection = fetch_recruited_with_config(
            config_path=team_config, funded_only=False, active_only=False)
        snapshot = refresh_snapshot(collection, config, previous)
    elif previous:
        snapshot = previous
    else:
        raise FileNotFoundError("No thesis snapshot: run exa-ma-harvest theses --refresh first")
    rendered = render_partials(snapshot)
    output.mkdir(parents=True, exist_ok=True)
    if refresh:
        temporary = snapshot_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(snapshot_path)
    for name, content in rendered.items():
        (output / name).write_text(content)
    matched = sum(bool(p.get("thesis")) for p in snapshot["people"].values())
    print(f"Theses: {matched}/{len(snapshot['people'])} verified titles; output: {output}")
    return snapshot
