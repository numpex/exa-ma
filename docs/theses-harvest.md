# Doctoral thesis metadata

The recruited-personnel page and the 2027 assembly agenda share metadata from the
[theses.fr search API](https://theses.fr/api/v1/recherche/openapi.yaml).
The team Google Sheet remains authoritative for names, positions, funding and WPs;
theses.fr supplies the registered thesis title and doctoral institution.
Only PhD rows whose start date has been reached are searched. `theses.yaml` can include additional agenda speakers
already present in the sheet without listing them as Exa-MA-funded personnel.

## Update

```sh
# Refresh the roster, query theses.fr, and regenerate both page includes.
exa-ma-harvest theses --refresh

# Regenerate offline from the checked-in snapshot.
exa-ma-harvest theses
```

`exa-ma-harvest all` also refreshes theses. The existing CI workflow runs that
command and tracks updates under `docs/modules/ROOT/partials/`.
No extra API key or dependency is required. These commands do not modify Google Sheets.

Outputs under `docs/modules/ROOT/partials/theses/`:

- `data.json`: minimal public metadata, match outcomes and verification dates.
- `directory.adoc`: PhD thesis table included by `team-recruited.adoc`.
- `attributes.adoc`: reusable `{thesis-person-slug}` links used in the programme.

Edit the configuration or generator, not generated includes. A plain Antora build
uses the checked-in includes and needs no live access to theses.fr.

## Identity checks and missing records

Automatic acceptance requires exactly one record with an exact normalized author
name and at least one matching supervisor. Case, accents and punctuation are
normalized; partial names and research-topic similarity are not sufficient.
When available, enrolment dates must be within one year of the recorded recruitment
start; a defence before that start is rejected. Missing matches remain explicitly
unverified, including when a new PhD has not yet been registered on theses.fr.

Document known name variants or an additional supervisor in `theses.yaml`, with
evidence URLs. Such entries still require both author and supervisor checks; they
do not bypass matching or supply invented titles. Review the generated diff.

Network failures, invalid responses and incomplete result sets abort the refresh
before changing any output. A previously verified record is retained and labelled
with its last verification date if a later search cannot verify it. Historical
records remain available to agenda attributes if someone leaves the current roster,
but disappear from the current thesis table. The normal personnel directory and
its overview statistics are managed separately by the existing team generator.

Thesis titles are reproduced as registered, including source spelling. They provide
research context on the agenda and are explicitly **not confirmed talk titles**.
Postdoctoral and engineering presentations retain their own descriptions.

## Validation

```sh
python -m pytest tests/test_theses.py tests/test_cli.py -q
npm run antora
```
