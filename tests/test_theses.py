"""Offline regression checks for identity matching and safe thesis refreshes."""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from harvest import theses
from harvest.team import PositionType, RecruitedCollection, RecruitedPerson


@pytest.fixture
def person():
    return RecruitedPerson(first_name="Antoine", surname="Simon", position=PositionType.PHD,
                           advisors=["Marc Massot"], start_date=datetime(2024, 11, 12),
                           work_packages=["WP1"])


@pytest.fixture
def candidate():
    return {"id": "s408792", "titrePrincipal": "Couplage temporel adaptatif",
            "auteurs": [{"prenom": "Antoine", "nom": "Simon"}],
            "directeurs": [{"prenom": "Marc", "nom": "Massot"}],
            "datePremiereInscriptionDoctorat": "12/11/2024", "status": "enCours",
            "etabSoutenanceN": "Institut polytechnique de Paris"}


def test_disambiguates_homonyms_with_supervisor(person, candidate):
    unrelated = {**candidate, "id": "2024OTHER", "directeurs": [{"prenom": "Other", "nom": "Advisor"}]}
    assert theses.select_thesis(person, [unrelated, candidate], {}) == (candidate, "matched")
    assert theses.select_thesis(person, [unrelated], {}) == (None, "not_verified")


def test_rejects_ambiguous_matches(person, candidate):
    other = {**candidate, "id": "s999999"}
    assert theses.select_thesis(person, [candidate, other], {}) == (None, "ambiguous")


def test_name_normalization_is_not_fuzzy():
    assert theses.normalize_name("Hélène HÉNON") == theses.normalize_name("Helene Henon")
    assert theses.normalize_name("Prud’homme") == theses.normalize_name("Prud'homme")


def test_partial_name_needs_documented_alias(person, candidate):
    variant = {**candidate, "auteurs": [{"prenom": "Antoine", "nom": "Simon Dupont"}]}
    assert theses.select_thesis(person, [variant], {})[0] is None
    assert theses.select_thesis(person, [variant], {"author_names": ["Antoine Simon Dupont"]})[0] == variant


@pytest.mark.parametrize("changes", [
    {"datePremiereInscriptionDoctorat": "01/01/2005"},
    {"dateSoutenance": "01/01/2020"},
])
def test_rejects_incompatible_dates(person, candidate, changes):
    assert theses.select_thesis(person, [{**candidate, **changes}], {})[0] is None


def test_refresh_deduplicates_phd_rows_before_search_and_skips_nonphd(person, candidate):
    engineer = person.model_copy(update={"position": PositionType.RESEARCH_ENGINEER})
    collection = RecruitedCollection(personnel=[engineer, person, person])
    search = Mock(return_value=[candidate])
    snapshot = theses.refresh_snapshot(collection, {}, search=search)
    search.assert_called_once_with("Antoine Simon")
    assert list(snapshot["people"]) == ["antoine-simon"]
    assert "email" not in json.dumps(snapshot)


def test_future_doctoral_recruitment_is_not_a_current_phd(person, candidate):
    future = person.model_copy(update={"first_name": "Future", "start_date": datetime(2099, 1, 1)})
    snapshot = theses.refresh_snapshot(RecruitedCollection(personnel=[person, future]), {},
                                       search=lambda _: [candidate])
    assert future.slug not in snapshot["people"]


def test_unfunded_agenda_person_not_added_to_funded_directory(person, candidate):
    person.funded_by_exama = False
    snapshot = theses.refresh_snapshot(RecruitedCollection(personnel=[person]),
        {"agenda_people": [person.slug]}, search=lambda _: [candidate])
    rendered = theses.render_partials(snapshot)
    assert ":thesis-antoine-simon:" in rendered["attributes.adoc"]
    assert "Antoine Simon" not in rendered["directory.adoc"]


def test_unmatched_and_previous_records_are_explicit(person, candidate):
    collection = RecruitedCollection(personnel=[person])
    first = theses.refresh_snapshot(collection, {}, search=lambda _: [])
    assert "Title not yet verified" in theses.render_partials(first)["directory.adoc"]
    verified = theses.refresh_snapshot(collection, {}, search=lambda _: [candidate])
    again = theses.refresh_snapshot(collection, {}, verified, search=lambda _: [])
    assert again["people"][person.slug]["match_status"] == "retained_previous"
    assert "last verified" in theses.render_partials(again)["directory.adoc"]


def test_rejects_undocumented_override(person):
    with pytest.raises(ValueError, match="evidence"):
        theses.refresh_snapshot(RecruitedCollection(personnel=[person]),
            {"people": {person.slug: {"author_names": ["Different Name"]}}}, search=lambda _: [])


def test_failed_refresh_preserves_all_outputs(tmp_path, monkeypatch, person, candidate):
    collection = RecruitedCollection(personnel=[person])
    snapshot = theses.refresh_snapshot(collection, {}, search=lambda _: [candidate])
    output = tmp_path / "theses"
    output.mkdir()
    (output / "data.json").write_text(json.dumps(snapshot))
    config = tmp_path / "config.yaml"
    config.write_text("{}")
    theses.harvest_theses(partials_dir=tmp_path)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    monkeypatch.setattr(theses, "fetch_recruited_with_config", Mock(side_effect=TimeoutError("offline")))
    with pytest.raises(TimeoutError):
        theses.harvest_theses(refresh=True, partials_dir=tmp_path, config_path=config)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_incomplete_api_response_is_rejected(monkeypatch):
    import io
    monkeypatch.setattr(theses, "urlopen", lambda *a, **kw: io.StringIO('{"totalHits": 2, "theses": []}'))
    with pytest.raises(ValueError, match="Incomplete"):
        theses.search_theses("Antoine Simon")


def test_metadata_escapes_asciidoc_markup():
    assert theses.escape_asciidoc("A | B [x] {include} *bold*\nnext") == (
        "A &#124; B &#91;x&#93; &#123;include&#125; &#42;bold&#42; next")


def test_historical_records_keep_agenda_attribute(person, candidate):
    collection = RecruitedCollection(personnel=[person])
    previous = theses.refresh_snapshot(collection, {}, search=lambda _: [candidate])
    other = person.model_copy(update={"first_name": "Someone"})
    snapshot = theses.refresh_snapshot(RecruitedCollection(personnel=[other]), {}, previous,
                                       search=lambda _: [])
    rendered = theses.render_partials(snapshot)
    assert ":thesis-antoine-simon:" in rendered["attributes.adoc"]
    assert "Antoine Simon" not in rendered["directory.adoc"]
