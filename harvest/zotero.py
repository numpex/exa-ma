"""Import HAL records into Zotero without replacing curated metadata.

Reads are public when the group permits it. Writes require ZOTERO_API_KEY.
The default is a dry run; only --apply writes to the shared library.
"""

import copy
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

from .config import load_config
from .hal import _first_str, fetch_publications

API = "https://api.zotero.org"
HAL_ID = re.compile(r"\b(?:hal|tel|inria|insu|in2p3|ird|pasteur|cea)-\d+", re.I)
TYPES = {
    "ART": "journalArticle",
    "COMM": "conferencePaper",
    "COUV": "bookSection",
    "OUV": "book",
    "THESE": "thesis",
    "HDR": "thesis",
    "REPORT": "report",
    "UNDEFINED": "preprint",
    "SOFTWARE": "computerProgram",
    "DATA": "dataset",
    "POSTER": "presentation",
    "PATENT": "patent",
}


class ZoteroClient:
    def __init__(self, group_id, api_key=None):
        self.prefix = f"/groups/{int(group_id)}"
        self.api_key = api_key
        self.version = None
        self.templates = {}
        self.not_before = 0.0

    def request(self, path, *, method="GET", payload=None, headers=None):
        request_headers = {"Zotero-API-Version": "3", "Accept": "application/json"}
        if self.api_key:
            request_headers["Zotero-API-Key"] = self.api_key
        request_headers.update(headers or {})
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            request_headers["Content-Type"] = "application/json"
        for attempt in range(4):
            time.sleep(max(0, self.not_before - time.monotonic()))
            try:
                with urlopen(
                    Request(API + path, data=body, headers=request_headers, method=method),
                    timeout=60,
                ) as response:
                    response_headers = response.headers
                    self.not_before = time.monotonic() + float(response_headers.get("Backoff", 0))
                    raw = response.read()
                    return (json.loads(raw) if raw else None), response_headers
            except HTTPError as error:
                # Never blindly retry a write: the next run re-reads the library.
                if method == "GET" and error.code in (429, 500, 502, 503, 504) and attempt < 3:
                    delay = max(float(error.headers.get("Retry-After", 0)), 2**attempt)
                    self.not_before = time.monotonic() + delay
                    continue
                raise RuntimeError(
                    f"Zotero {method} {path.split('?')[0]}: HTTP {error.code}"
                ) from error

    def list_all(self, resource):
        result = []
        total = None
        while total is None or len(result) < total:
            page, headers = self.request(
                self.prefix
                + "/"
                + resource
                + "?"
                + urlencode(
                    {
                        "limit": 100,
                        "start": len(result),
                    }
                )
            )
            version = headers["Last-Modified-Version"]
            if self.version is not None and version != self.version:
                raise RuntimeError("Zotero library changed during read; rerun synchronization")
            self.version = version
            page_total = int(headers["Total-Results"])
            if total is not None and total != page_total:
                raise RuntimeError("Zotero result count changed during pagination")
            total = page_total
            if not isinstance(page, list) or (not page and len(result) < total):
                raise RuntimeError("Incomplete Zotero response")
            result.extend(page)
        return result

    def template(self, item_type):
        if item_type not in self.templates:
            self.templates[item_type], _ = self.request(
                "/items/new?" + urlencode({"itemType": item_type})
            )
        return copy.deepcopy(self.templates[item_type])

    def write(self, resource, objects):
        if not self.api_key or self.version is None:
            raise RuntimeError("Writes require ZOTERO_API_KEY and a complete library snapshot")
        result, headers = self.request(
            self.prefix + "/" + resource,
            method="POST",
            payload=objects,
            headers={"If-Unmodified-Since-Version": self.version},
        )
        self.version = headers["Last-Modified-Version"]
        if result.get("failed"):
            raise RuntimeError("Zotero rejected objects: " + json.dumps(result["failed"]))
        successful = result.get("successful", {})
        if len(successful) + len(result.get("unchanged", {})) != len(objects):
            raise RuntimeError("Zotero returned an incomplete write result")
        return successful

    def require_write_access(self):
        permissions, _ = self.request("/keys/current")
        groups = permissions.get("access", {}).get("groups", {})
        group_id = self.prefix.rsplit("/", 1)[1]
        access = groups.get(group_id, groups.get("all", {}))
        if not access.get("write"):
            raise ValueError(f"ZOTERO_API_KEY has no write access to group {group_id}")


class Collections:
    def __init__(self, config, collections):
        self.config = config
        self.by_key = {c["key"]: c["data"] for c in collections}
        self.root = config["parent_collection"]
        if self.root not in self.by_key:
            raise ValueError("Configured Our Publications collection does not exist")
        self.wps = config["wp_collections"]
        if set(self.wps) != {f"WP{i}" for i in range(1, 8)}:
            raise ValueError("Configure exactly WP1 through WP7")
        for wp, key in self.wps.items():
            data = self.by_key.get(key, {})
            if data.get("parentCollection") != self.root or data.get("name") != wp:
                raise ValueError(f"{wp} does not match a child of Our Publications")
        self.pending = {}

    def workpackages(self, keys):
        result = set()
        for key in keys:
            seen = set()
            while key and key not in seen:
                seen.add(key)
                result.update(wp for wp, wp_key in self.wps.items() if wp_key == key)
                if key in self.pending:
                    key = self.pending[key]["parentCollection"]
                else:
                    key = self.by_key.get(key, {}).get("parentCollection")
        return result

    def child(self, parent, name):
        matches = [
            k
            for k, d in self.by_key.items()
            if d.get("parentCollection") == parent and d["name"] == name
        ]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous collection {name} under {parent}")
        if matches:
            return matches[0]
        token = f"new:{parent}/{name}"
        self.pending[token] = {"name": name, "parentCollection": parent}
        return token

    def label(self, key):
        data = self.pending.get(key, self.by_key.get(key, {}))
        parent = data.get("parentCollection")
        return (self.label(parent) + "/" if parent else "") + data.get("name", key)


def normalize_doi(value):
    return re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", _first_str(value).strip().lower()
    )


def normalized_title(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", _first_str(value)).casefold() if c.isalnum()
    )


def words(value):
    """Normalize punctuation/accents while retaining word boundaries."""
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    return " ".join(re.findall(r"[^\W_]+", value.casefold()))


def classify(pub, rules, author_evidence=None):
    """Specific topic phrases dominate; confirmed author history adds one point.

    Scores are rule weights, not probabilities. A single title (3) or keyword
    (4) match suffices; abstract matches are capped at 2 per WP. An author
    alone, or an author plus one abstract phrase, cannot assign a WP.
    """
    fields = {
        "title": words(_first_str(pub.get("title_s"))),
        "keywords": words(
            " ; ".join(pub.get("keyword_s", []))
            if isinstance(pub.get("keyword_s"), list)
            else pub.get("keyword_s", "")
        ),
        "abstract": words(_first_str(pub.get("abstract_s"))),
    }
    evidence = {}
    for wp, phrases in rules.items():
        matches = []
        score = 0
        for field, weight in (("title", 3), ("keywords", 4), ("abstract", 1)):
            found = [
                phrase
                for phrase in phrases
                if " " + words(phrase) + " " in " " + fields[field] + " "
            ]
            if found:
                matches.append({"field": field, "phrases": found})
                score += min(2, len(found)) if field == "abstract" else weight
        if author_evidence and wp in author_evidence:
            matches.append({"field": "author", "authors": author_evidence[wp]})
            score += 1
        if matches:
            evidence[wp] = {"score": score, "matches": matches}
    return sorted(wp for wp, info in evidence.items() if info["score"] >= 3), evidence


def author_suggestions(pub, items, tree):
    """Suggest WPs from authors with repeated, exclusive Zotero WP history.

    Author history is intentionally advisory: names are imperfect identifiers,
    and a contributor may publish in several work packages.
    """
    history = defaultdict(lambda: defaultdict(set))
    for item in items:
        data = item["data"]
        wps = tree.workpackages(data.get("collections", []))
        if not wps or data.get("itemType") in ("attachment", "note", "annotation"):
            continue
        for creator in data.get("creators", []):
            name = creator.get("name") or " ".join(
                part for part in (creator.get("firstName"), creator.get("lastName")) if part
            )
            if name:
                for wp in wps:
                    history[words(name)][wp].add(item["key"])

    evidence = defaultdict(list)
    authors = pub.get("authFullName_s", [])
    for name in [authors] if isinstance(authors, str) else authors:
        counts = history.get(words(name), {})
        if len(counts) == 1:
            wp, keys = next(iter(counts.items()))
            if len(keys) >= 2:
                evidence[wp].append({"author": name, "confirmed_items": len(keys)})
    return {
        wp: sorted(rows, key=lambda row: row["author"])
        for wp, rows in sorted(evidence.items())
    }


def hal_ids(data):
    return set(
        HAL_ID.findall(
            " ".join(str(data.get(k, "")) for k in ("url", "extra", "archiveLocation")).lower()
        )
    )


def confirmed_workpackages(publications, items, collections, config):
    """Map HAL IDs to WP memberships already present in Our Publications.

    An exact HAL ID takes precedence over DOI. Ambiguous matches get no label;
    title similarity alone does not establish a Zotero identity.
    """
    tree = Collections(config, collections)
    by_hal = defaultdict(set)
    by_doi = defaultdict(set)
    data_by_key = {}
    for item in items:
        data = item["data"]
        if data.get("itemType") in ("attachment", "note", "annotation"):
            continue
        key = item["key"]
        data_by_key[key] = data
        for hal_id in hal_ids(data):
            by_hal[hal_id].add(key)
        extra_doi = re.search(r"(?im)^DOI:\s*(\S+)", data.get("extra", ""))
        doi = normalize_doi(data.get("DOI") or (extra_doi.group(1) if extra_doi else ""))
        if doi:
            by_doi[doi].add(key)
    result = {}
    for pub in publications:
        hal_id = pub["halId_s"].lower()
        matches = by_hal[hal_id]
        if not matches:
            matches = by_doi[normalize_doi(pub.get("doiId_s", ""))]
        result[pub["halId_s"]] = (
            sorted(tree.workpackages(data_by_key[next(iter(matches))].get("collections", [])))
            if len(matches) == 1
            else []
        )
    return result


def fetch_confirmed_workpackages(publications, config_path=None):
    """Read Zotero's current WP collection memberships for site generation."""
    path = config_path or Path(__file__).parent.parent / "zotero.yaml"
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    client = ZoteroClient(config["group_id"], os.environ.get("ZOTERO_API_KEY"))
    collections = client.list_all("collections")
    items = client.list_all("items/top")
    return confirmed_workpackages(publications, items, collections, config)


def new_item(pub, client):
    code = _first_str(pub.get("docType_s"))
    item_type = TYPES.get(code, "document")
    data = client.template(item_type)
    full = pub.get("authFullName_s", [])
    if isinstance(full, str):
        full = [full]
    first, last = pub.get("authFirstName_s", []), pub.get("authLastName_s", [])
    if isinstance(first, str):
        first = [first]
    if isinstance(last, str):
        last = [last]
    # Do not guess how to split family names; retain HAL's structured names when complete.
    role = {"computerProgram": "programmer", "presentation": "presenter", "patent": "inventor"}.get(
        item_type, "author"
    )
    if full and len(first) == len(last) == len(full) and all(last):
        creators = [
            {"creatorType": role, "firstName": given, "lastName": family}
            for given, family in zip(first, last)
        ]
    else:
        creators = [{"creatorType": role, "name": name} for name in full]
    values = {
        "title": _first_str(pub.get("title_s")),
        "creators": creators,
        "abstractNote": _first_str(pub.get("abstract_s")),
        "date": _first_str(
            pub.get("publicationDate_s")
            or pub.get("producedDate_s")
            or pub.get("publicationDateY_i")
        ),
        "url": "https://hal.science/" + pub["halId_s"],
        "DOI": normalize_doi(pub.get("doiId_s", "")),
        "publicationTitle": _first_str(pub.get("journalTitle_s")),
        "conferenceName": _first_str(pub.get("conferenceTitle_s")),
        "proceedingsTitle": _first_str(pub.get("conferenceTitle_s")),
        "volume": _first_str(pub.get("volume_s")),
        "issue": _first_str(pub.get("issue_s")),
        "pages": _first_str(pub.get("page_s")),
        "publisher": _first_str(pub.get("publisher_s")),
        "language": _first_str(pub.get("language_s")),
    }
    for key, value in values.items():
        if key in data and value:
            data[key] = value
    data["extra"] = "Citation Key: " + pub["halId_s"].replace("-", "_")
    if values["DOI"] and "DOI" not in data:
        data["extra"] += "\nDOI: " + values["DOI"]
    data["tags"] = [{"tag": "source:HAL"}, {"tag": "project:Exa-MA"}]
    return data


def publication_summary(pub):
    """Human-readable HAL metadata for duplicate review, without guessing identity."""
    return {
        "title": _first_str(pub.get("title_s")),
        "authors": pub.get("authFullName_s", []),
        "date": _first_str(pub.get("publicationDate_s") or pub.get("publicationDateY_i")),
        "document_type": _first_str(pub.get("docType_s")),
        "doi": normalize_doi(pub.get("doiId_s", "")),
        "hal_ids": [pub["halId_s"]],
        "url": "https://hal.science/" + pub["halId_s"],
        "venue": _first_str(pub.get("journalTitle_s") or pub.get("conferenceTitle_s")),
    }


def conflict_details(pub, reason, keys, working, sources, tree, group_id):
    """Explain why each candidate was flagged and what the dry run would skip."""
    candidates = []
    incoming = publication_summary(pub)
    for key in sorted(set(keys)):
        data = working[key]
        if key.startswith("new:"):
            summary = publication_summary(sources[key.removeprefix("new:")])
            origin = "planned HAL import (not yet in Zotero)"
        else:
            extra_doi = re.search(r"(?im)^DOI:\s*(\S+)", data.get("extra", ""))
            summary = {
                "title": data.get("title", ""),
                "authors": [
                    c.get("name")
                    or " ".join(part for part in (c.get("firstName"), c.get("lastName")) if part)
                    for c in data.get("creators", [])
                ],
                "date": data.get("date", ""),
                "document_type": data.get("itemType", ""),
                "doi": normalize_doi(data.get("DOI") or (extra_doi.group(1) if extra_doi else "")),
                "hal_ids": sorted(hal_ids(data)),
                "url": data.get("url", ""),
                "venue": data.get("publicationTitle") or data.get("conferenceName", ""),
                "zotero_url": f"https://www.zotero.org/groups/{group_id}/items/{key}",
            }
            origin = "existing Zotero item"
        matched_on = []
        if normalized_title(incoming["title"]) == normalized_title(summary["title"]):
            matched_on.append("normalized title (case/punctuation ignored)")
        if incoming["doi"] and incoming["doi"] == summary["doi"]:
            matched_on.append("DOI")
        if pub["halId_s"] in summary["hal_ids"]:
            matched_on.append("HAL ID")
        if re.search(
            r"(?im)^Citation Key:\s*" + re.escape(pub["halId_s"].replace("-", "_")) + r"\s*$",
            data.get("extra", ""),
        ):
            matched_on.append("citation key")
        candidates.append(
            {
                "key": key,
                "origin": origin,
                **summary,
                "matched_on": matched_on,
                "collections": [tree.label(k) for k in data.get("collections", [])],
                "differences": {
                    field: {"incoming": incoming[field], "candidate": summary[field]}
                    for field in (
                        "title",
                        "authors",
                        "date",
                        "document_type",
                        "doi",
                        "hal_ids",
                        "venue",
                    )
                    if incoming[field] != summary[field]
                },
            }
        )
    return {
        "hal_id": pub["halId_s"],
        "reason": reason,
        "items": sorted(set(keys)),
        "incoming": incoming,
        "candidates": candidates,
        "effect": (
            "This incoming HAL record is skipped; candidate imports already planned remain planned."
        ),
        "review": (
            "Check whether these are the same work, different versions, or distinct outputs "
            "before merging or linking identifiers."
        ),
    }


def build_plan(publications, items, collections, config, client):
    tree = Collections(config, collections)
    assignments = config.get("assignments", {})
    rules = config.get("keyword_rules", {})
    if any(
        wp not in tree.wps
        or not isinstance(phrases, list)
        or any(not isinstance(p, str) or not words(p) for p in phrases)
        for wp, phrases in rules.items()
    ):
        raise ValueError("Invalid keyword rules")
    for hal_id, wps in assignments.items():
        if not isinstance(wps, list) or not wps or any(wp not in tree.wps for wp in wps):
            raise ValueError(f"Invalid WP assignments for {hal_id}")
    originals = {
        i["key"]: i["data"]
        for i in items
        if i["data"]["itemType"] not in ("attachment", "note", "annotation")
    }
    working = copy.deepcopy(originals)
    sources = {pub["halId_s"]: pub for pub in publications}
    conflicts = []
    classifications = []
    for pub in publications:
        hid = pub["halId_s"]
        doi = normalize_doi(pub.get("doiId_s", ""))
        matches = [
            key
            for key, data in working.items()
            if hid in hal_ids(data)
            or (doi and doi == normalize_doi(data.get("DOI", "")))
            or (
                doi
                and re.search(r"(?im)^DOI:\s*" + re.escape(doi) + r"\s*$", data.get("extra", ""))
            )
        ]
        if len(matches) > 1:
            conflicts.append(
                conflict_details(
                    pub,
                    "multiple identifier matches",
                    matches,
                    working,
                    sources,
                    tree,
                    config["group_id"],
                )
            )
            continue
        if not matches:
            title = normalized_title(pub.get("title_s"))
            possible = [
                k for k, d in working.items() if title and normalized_title(d.get("title")) == title
            ]
            citekey = hid.replace("-", "_")
            possible += [
                k
                for k, d in working.items()
                if re.search(
                    r"(?im)^Citation Key:\s*" + re.escape(citekey) + r"\s*$", d.get("extra", "")
                )
            ]
            if possible:
                conflicts.append(
                    conflict_details(
                        pub,
                        "title/citation-key match needs review",
                        possible,
                        working,
                        sources,
                        tree,
                        config["group_id"],
                    )
                )
                continue
            key = "new:" + hid
            working[key] = new_item(pub, client)
        else:
            key = matches[0]
        data = working[key]
        # Curated bibliographic fields and citation keys are never overwritten.
        if hid not in hal_ids(data):
            data["extra"] = (data.get("extra", "").rstrip() + "\nHAL ID: " + hid).lstrip()
        existing = list(data.get("collections", []))
        existing_wps = tree.workpackages(existing)
        author_evidence = author_suggestions(pub, items, tree)
        inferred, evidence = classify(pub, rules, author_evidence)
        if hid in assignments:
            wps = existing_wps | set(assignments[hid])
            basis = "manual mapping"
        elif existing_wps:
            wps = existing_wps
            basis = "existing Zotero membership"
        else:
            wps = set(inferred)
            if not wps:
                basis = "unassigned"
            elif any(
                not any(
                    match["field"] in ("title", "keywords")
                    for match in evidence[wp]["matches"]
                )
                for wp in wps
            ):
                basis = "weighted topic/author evidence"
            else:
                basis = "title/HAL keywords"
        classifications.append(
            {
                "hal_id": hid,
                "title": _first_str(pub.get("title_s")),
                "workpackages": sorted(wps),
                "basis": basis,
                "keyword_evidence": evidence,
                "author_suggestions": author_evidence,
            }
        )
        if wps:
            code = _first_str(pub.get("docType_s"))
            category = {
                "SOFTWARE": "Software",
                "DATA": "Datasets",
                "REPORT": "Technical Notes",
            }.get(code, "Articles")
            # Keep an existing WP placement; explicit assignments add a destination
            # only when that WP has not already been assigned manually.
            for wp in sorted(wps - tree.workpackages(existing)):
                existing.append(tree.child(tree.wps[wp], category))
        else:
            existing.append(tree.root)
        data["collections"] = sorted(set(existing))
    actions = []
    for key, data in working.items():
        if key not in originals:
            actions.append({"action": "create", "key": key, "data": data})
        elif data != originals[key]:
            # Batch POST supports PATCH semantics; send only fields this importer owns.
            patch = {"key": key, "version": data["version"]}
            patch.update(
                {
                    field: data[field]
                    for field in ("extra", "collections")
                    if data.get(field) != originals[key].get(field)
                }
            )
            actions.append({"action": "update", "key": key, "data": patch})
    report = {
        "hal_records": len(publications),
        "create": sum(a["action"] == "create" for a in actions),
        "update": sum(a["action"] == "update" for a in actions),
        "conflicts": conflicts,
        "classifications": classifications,
        "actions": [
            {
                "action": a["action"],
                "key": a["key"],
                "title": working[a["key"]].get("title", ""),
                "collections": [tree.label(k) for k in working[a["key"]].get("collections", [])],
            }
            for a in actions
        ],
    }
    return actions, tree, report


def apply_plan(client, actions, tree):
    # Only create missing collections actually used by a planned item.
    tokens = {
        key for a in actions for key in a["data"].get("collections", []) if key in tree.pending
    }
    resolved = {}
    for token in sorted(tokens):
        result = client.write("collections", [tree.pending[token]])
        resolved[token] = result["0"]["key"]
    for start in range(0, len(actions), 50):
        batch = []
        for action in actions[start : start + 50]:
            data = copy.deepcopy(action["data"])
            if "collections" in data:
                data["collections"] = [resolved.get(k, k) for k in data["collections"]]
            batch.append(data)
        client.write("items", batch)


def run(args):
    try:
        config = yaml.safe_load(args.zotero_config.read_text())
        key = os.environ.get("ZOTERO_API_KEY")
        if args.apply and not key:
            raise ValueError("Set ZOTERO_API_KEY before using --apply")
        query = load_config(args.config).get_publications_config().query
        publications = fetch_publications(query=query, years=[], domains=[], verbose=False)
        if not publications:
            raise ValueError("HAL returned no publications; refusing synchronization")
        client = ZoteroClient(config["group_id"], key)
        if args.apply:
            client.require_write_access()
        collections = client.list_all("collections")
        items = client.list_all("items/top")
        actions, tree, report = build_plan(publications, items, collections, config, client)
        report["applied"] = False
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(
            f"HAL: {report['hal_records']}; create: {report['create']}; "
            f"update: {report['update']}; conflicts: {len(report['conflicts'])}"
        )
        print(f"Report: {args.report}")
        if report["conflicts"]:
            print("Ambiguous duplicate candidates skipped; see report for items needing review")
        if args.apply:
            apply_plan(client, actions, tree)
            report["applied"] = True
            args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            print("Zotero synchronization complete")
        else:
            print("Dry run: Zotero was not changed (use --apply to synchronize)")
        return 0
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        print(f"Zotero synchronization failed: {error}", file=sys.stderr)
        return 1
