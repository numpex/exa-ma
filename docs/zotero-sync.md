# Daily HAL → Zotero synchronization

`exa-ma-harvest zotero-sync` retrieves records for the configured Exa-MA ANR
identifier and files them in group **5582837**, under **Our Publications**.
`exa-ma-d7.1` separately retrieves Zotero's bibliography. This command is separate
from `exa-ma-harvest all`, so normal website builds never modify Zotero.

The Exa-MA publications page reads the current `Our Publications/WP1`–`WP7`
memberships from Zotero when `exa-ma-harvest all` generates its HAL partial.
It shows one row per HAL record with links to every confirmed WP; records without
a confirmed Zotero WP assignment have an empty WP cell. Keyword suggestions in
this tool's dry-run report do not appear on the site until the Zotero item is
actually placed in a WP collection. Site generation needs Zotero read access;
the CI workflow uses the `ZOTERO_API_KEY` secret.
The site workflow refreshes at **06:17 UTC**, after the 04:17 UTC Zotero sync.

## Run locally

```sh
# ZOTERO_API_KEY is read from the environment; never put its value in a file.
uv run --python 3.11 exa-ma-harvest zotero-sync --report /tmp/zotero-report.json
# After inspecting the report, write the planned changes:
uv run --python 3.11 exa-ma-harvest zotero-sync --apply --report /tmp/zotero-report.json
```

The default is a read-only dry run. `--apply` needs group write permission.
`--zotero-config` selects a different collection/rule configuration. The global
`--config exama.yaml` argument, placed before `zotero-sync`, selects the HAL query.
Ingestion deliberately applies no year/domain filters; those filters belong to
reporting and website views, not the project reference inventory.

## How WP classification works

Rules and exact collection IDs live in [`zotero.yaml`](../zotero.yaml).
The importer validates that WP1–WP7 are children of the configured parent, avoiding
the similarly named collections under External Publications.

1. Existing Zotero WP memberships are retained. Confirmed `assignments` in the
   configuration can add WPs and take precedence over inferred assignments.
2. Otherwise, specific phrases in the **title or HAL keywords** assign WPs.
   Examples: domain decomposition → WP3; inverse problems → WP4; shape optimization
   → WP5. Case, punctuation, hyphens and accents are normalized. Matching uses word
   boundaries, not arbitrary substrings. Inflection variants are explicit rules.
3. A title match contributes 3, a HAL-keyword match 4, and distinct abstract
   phrase matches contribute at most 2 per WP. Confirmed author history adds
   only 1 point. The assignment threshold is 3, so an author alone or with one
   abstract phrase cannot assign a WP. These are transparent rule weights,
   **not probabilities**.
4. Multiple WPs may match, placing one Zotero item in several collections.
   The report also suggests WPs for authors who already have at least two distinct
   Zotero publications in exactly one WP. This history can tip two abstract
   purpose phrases over the threshold, but never files a paper by itself. Names
   are ambiguous, and contributors can publish across several WPs. Confirm an
   uncertain author-based suggestion by adding the HAL ID to `assignments` after review.
   Generic words such as simulation, HPC and performance are deliberately insufficient.
5. References without a clear WP match go directly in `Our Publications`, with
   no WP collection or WP tag added. Abstract suggestions remain in the report
   only. Existing memberships are preserved if a WP is assigned later.

Gaussian processes (GPs) are a method, not a WP signal on their own. A GP paper
about Bayesian optimization points to WP5; a paper about uncertainty
quantification points to WP6. If both purposes are explicit, both WPs can be
assigned. An author who works in both WPs does not settle an otherwise unclear
paper's assignment.

Papers, posters, and theses are filed under `WPx/Articles`; HAL reports under
`WPx/Technical Notes`; software and datasets under their corresponding category.
Reports are not assumed to be project deliverables. Existing manual placements
within a WP are retained without adding another category there.

Keyword rules are conservative and should be reviewed on the first report. They
cannot establish scientific responsibility from metadata alone. Once an item has
a WP membership, changing rules does not automatically reclassify it; correct it
in Zotero or add a confirmed mapping. To remove a wrong membership, remove it in
Zotero and update any conflicting explicit mapping.

## Identity and preservation

The importer matches by HAL ID or normalized DOI, including DOI lines in Extra.
It reuses existing items and preserves their bibliographic metadata, citation
keys, tags, attachments and memberships. Only missing HAL provenance and collection
membership are added to existing items; later HAL metadata does not overwrite
editorial corrections. New items retain HAL document types and structured author
names where available. A DOI alone does not turn a preprint into a journal article.

Exact-title/citation-key candidates without matching identifiers, or multiple
identifier matches, are skipped and reported for review. Other records continue.
Resolve them in Zotero by correcting identifiers or merging actual duplicates.
HAL records are never removed from Zotero merely because they disappear from a query.

The JSON report lists every proposed change, destinations, classification evidence
and skipped duplicate candidates. Each conflict includes the incoming record and
candidate titles, authors, dates, document types, DOIs, HAL IDs, links, matching
criteria, and field differences. A `new:hal-...` candidate is a proposed import,
not an existing Zotero item; its creation remains planned even when another HAL
record is skipped as a possible duplicate. `conflict` means unresolved identity,
not an API failure or proof that two records must be merged.

Zotero pagination is checked against its library
version; writes use version preconditions and batches of at most 50. A concurrent
edit stops the run rather than overwriting it. A later run resumes by matching the
already imported records. Failed writes may leave earlier batches applied; the
report's `applied` flag is true only when all planned batches completed.

## Daily workflow

`.github/workflows/zotero.yml` runs at **04:17 UTC** and applies changes. Manual
dispatch defaults to dry-run; enable its `apply` input to write. It runs tests,
prevents overlapping jobs, and saves reports as artifacts for 30 days. It does not
commit website content or repository files.

Set the Actions secret **ZOTERO_API_KEY** to a key with write access to this group.
The D7.1 repository uses the same secret name, and needs only read access. Never
pass the key as a CLI argument. Workflows take effect once merged into each
repository's default branch. GitHub may delay scheduled jobs.

D7.1's retrieval job runs at **05:17 UTC**. The one-hour offset is not a strict
cross-repository dependency: it retrieves whatever complete snapshot Zotero has
at that time. No cross-repository token is needed. Its commits use `GITHUB_TOKEN`,
so they do not trigger a recursive build. Normal LaTeX builds use the committed
bibliography and do not contact Zotero.
