"""Behavioral tests for safe, repeatable HAL ingestion and WP classification."""

import copy
from unittest.mock import patch

import pytest

from harvest.zotero import (
    Collections,
    ZoteroClient,
    apply_plan,
    build_plan,
    classify,
    confirmed_workpackages,
    new_item,
)


@pytest.fixture
def config():
    return {
        "parent_collection": "ROOT",
        "group_id": 1,
        "wp_collections": {f"WP{i}": f"WPKEY{i}" for i in range(1, 8)},
        "assignments": {},
        "keyword_rules": {
            "WP3": ["domain decomposition", "mixed precision"],
            "WP6": ["uncertainty quantification"],
            "WP1": ["elements finis discontinus"],
        },
    }


@pytest.fixture
def collections(config):
    rows = [
        {"key": "ROOT", "data": {"name": "Our Publications", "parentCollection": False}},
    ]
    for wp, key in config["wp_collections"].items():
        rows.extend(
            [
                {"key": key, "data": {"name": wp, "parentCollection": "ROOT"}},
                {"key": key + "ART", "data": {"name": "Articles", "parentCollection": key}},
            ]
        )
    return rows


class FakeClient:
    def __init__(self):
        self.calls = []

    def template(self, item_type):
        return {
            "itemType": item_type,
            "title": "",
            "creators": [],
            "extra": "",
            "DOI": "",
            "date": "",
            "url": "",
            "tags": [],
            "collections": [],
        }

    def write(self, resource, objects):
        self.calls.append((resource, objects))
        return {str(i): {"key": f"CREATED{i}"} for i in range(len(objects))}


def publication(**updates):
    result = {
        "halId_s": "hal-12345678",
        "title_s": ["Mixed-precision domain decomposition"],
        "docType_s": "ART",
        "doiId_s": "10.1000/test",
        "publicationDateY_i": 2026,
        "authFullName_s": ["Jane Doe"],
        "authFirstName_s": ["Jane"],
        "authLastName_s": ["Doe"],
    }
    result.update(updates)
    return result


def existing(**updates):
    data = {
        "key": "ITEM",
        "version": 3,
        "itemType": "journalArticle",
        "title": "Curated title",
        "DOI": "https://doi.org/10.1000/test",
        "extra": "Citation Key: existing_key",
        "collections": ["WPKEY2ART"],
        "tags": [{"tag": "curated"}],
    }
    data.update(updates)
    return {"key": "ITEM", "data": data}


def test_multiple_wp_phrases_and_abstract_only_suggestions(config):
    pub = publication(keyword_s=["Uncertainty quantification"])
    wps, evidence = classify(pub, config["keyword_rules"])
    assert wps == ["WP3", "WP6"]
    assert evidence["WP6"]["matches"][0]["field"] == "keywords"
    pub = publication(
        title_s=["Generic HPC simulation"], abstract_s=["Mixed precision domain decomposition"]
    )
    assert classify(pub, config["keyword_rules"])[0] == []


def test_french_accents_and_word_boundaries(config):
    assert classify(publication(title_s=["Éléments finis discontinus"]), config["keyword_rules"])[
        0
    ] == ["WP1"]
    assert (
        classify(publication(title_s=["Notpreconditioning"]), {"WP3": ["preconditioning"]})[0] == []
    )


def test_fractal_decomposition_optimization_phrase_is_wp5():
    pub = publication(title_s=["A Comparative Study of Fractal-Based Decomposition Optimization"])
    assert classify(pub, {"WP5": ["fractal based decomposition optimization"]})[0] == ["WP5"]


def test_gaussian_processes_are_classified_by_purpose():
    rules = {
        "WP5": ["bayesian optimization"],
        "WP6": ["uncertainty quantification"],
    }
    assert classify(publication(title_s=["Gaussian processes"]), rules)[0] == []
    cases = (
        ("Gaussian processes for Bayesian optimization", ["WP5"]),
        ("Gaussian processes for uncertainty quantification", ["WP6"]),
        (
            "Bayesian optimization and uncertainty quantification with Gaussian processes",
            ["WP5", "WP6"],
        ),
    )
    for title, expected in cases:
        assert classify(publication(title_s=[title]), rules)[0] == expected


def test_author_history_has_weak_weight_and_needs_two_abstract_purpose_phrases():
    rules = {"WP5": ["bayesian optimization", "shape optimization"]}
    pub = publication(
        title_s=["Gaussian processes"],
        abstract_s=["Bayesian optimization and shape optimization"],
    )
    assert classify(pub, rules)[0] == []
    hint = {"WP5": [{"author": "Jane Doe", "confirmed_items": 2}]}
    wps, evidence = classify(pub, rules, hint)
    assert wps == ["WP5"]
    assert evidence["WP5"]["score"] == 3
    assert classify(publication(title_s=["Gaussian processes"]), rules, hint)[0] == []


def test_existing_assignment_and_metadata_win(config, collections):
    item = existing()
    untouched = copy.deepcopy(item)
    actions, _, report = build_plan([publication()], [item], collections, config, FakeClient())
    assert item == untouched
    assert actions[0]["data"] == {
        "key": "ITEM",
        "version": 3,
        "extra": "Citation Key: existing_key\nHAL ID: hal-12345678",
    }
    assert report["classifications"][0]["workpackages"] == ["WP2"]


def test_new_item_multi_wp_and_idempotence(config, collections):
    pub = publication(keyword_s=["uncertainty quantification"])
    actions, _, _ = build_plan([pub], [], collections, config, FakeClient())
    data = actions[0]["data"]
    assert data["collections"] == ["WPKEY3ART", "WPKEY6ART"]
    data.update(key="SAVED", version=1)
    again, _, _ = build_plan(
        [pub], [{"key": "SAVED", "data": data}], collections, config, FakeClient()
    )
    assert again == []


def test_manual_mapping_overrides_keywords_without_removing_existing_wps(config, collections):
    config["assignments"] = {"hal-12345678": ["WP5", "WP6"]}
    actions, _, report = build_plan(
        [publication()], [existing()], collections, config, FakeClient()
    )
    assert actions[0]["data"]["collections"] == ["WPKEY2ART", "WPKEY5ART", "WPKEY6ART"]
    assert report["classifications"][0]["basis"] == "manual mapping"


def test_unassigned_goes_to_parent_without_wp_labels(config, collections):
    pub = publication(title_s=["Unclear topic"], abstract_s=["Mixed precision"])
    actions, tree, report = build_plan([pub], [], collections, config, FakeClient())
    assert actions[0]["data"]["collections"] == ["ROOT"]
    assert actions[0]["data"]["tags"] == [{"tag": "source:HAL"}, {"tag": "project:Exa-MA"}]
    assert tree.pending == {}
    assert report["classifications"][0]["workpackages"] == []
    assert report["classifications"][0]["basis"] == "unassigned"
    assert "WP3" in report["classifications"][0]["keyword_evidence"]
    data = actions[0]["data"]
    data.update(key="SAVED", version=1)
    again, _, _ = build_plan(
        [pub], [{"key": "SAVED", "data": data}], collections, config, FakeClient()
    )
    assert again == []


def test_author_history_is_advisory_and_cross_wp_authors_are_excluded(config, collections):
    records = []
    for key, wp, author in (
        ("A", "WPKEY3ART", "Jane Doe"),
        ("B", "WPKEY3ART", "Jane Doe"),
        ("C", "WPKEY3ART", "Alex Multi"),
        ("D", "WPKEY4ART", "Alex Multi"),
    ):
        records.append(
            {
                "key": key,
                "data": {
                    "itemType": "journalArticle",
                    "title": key,
                    "collections": [wp],
                    "creators": [{"creatorType": "author", "name": author}],
                },
            }
        )
    pub = publication(
        title_s=["A topic without keyword evidence"],
        doiId_s="",
        authFullName_s=["Jane Doe", "Alex Multi"],
    )
    actions, _, report = build_plan([pub], records, collections, config, FakeClient())
    assert actions[0]["data"]["collections"] == ["ROOT"]
    row = report["classifications"][0]
    assert row["workpackages"] == []
    assert row["author_suggestions"] == {
        "WP3": [{"author": "Jane Doe", "confirmed_items": 2}]
    }


def test_later_classification_preserves_existing_memberships(config, collections):
    item = existing(collections=["ROOT", "EXTERNAL"])
    actions, _, _ = build_plan([publication()], [item], collections, config, FakeClient())
    assert actions[0]["data"]["collections"] == ["EXTERNAL", "ROOT", "WPKEY3ART"]


def test_ambiguous_duplicates_are_skipped(config, collections):
    first, second = existing(), existing(key="SECOND")
    second["key"] = "SECOND"
    actions, _, report = build_plan(
        [publication()], [first, second], collections, config, FakeClient()
    )
    assert not actions
    assert report["conflicts"][0]["reason"] == "multiple identifier matches"


def test_same_title_is_not_blindly_imported(config, collections):
    item = existing(DOI="", title="Mixed-precision domain decomposition")
    actions, _, report = build_plan([publication()], [item], collections, config, FakeClient())
    assert not actions
    assert report["conflicts"]
    detail = report["conflicts"][0]
    assert detail["incoming"]["doi"] == "10.1000/test"
    candidate = detail["candidates"][0]
    assert candidate["origin"] == "existing Zotero item"
    assert candidate["zotero_url"] == "https://www.zotero.org/groups/1/items/ITEM"
    assert candidate["matched_on"] == ["normalized title (case/punctuation ignored)"]
    assert candidate["differences"]["doi"] == {"incoming": "10.1000/test", "candidate": ""}


def test_conflict_with_planned_import_reports_both_publication_types(config, collections):
    report_pub = publication(doiId_s="", docType_s="REPORT")
    article_pub = publication(halId_s="hal-87654321", doiId_s="", docType_s="ART")
    actions, _, report = build_plan(
        [report_pub, article_pub], [], collections, config, FakeClient()
    )
    assert len(actions) == 1
    detail = report["conflicts"][0]
    assert detail["incoming"]["document_type"] == "ART"
    candidate = detail["candidates"][0]
    assert candidate["origin"] == "planned HAL import (not yet in Zotero)"
    assert candidate["document_type"] == "REPORT"
    assert candidate["url"] == "https://hal.science/hal-12345678"
    assert "zotero_url" not in candidate


def test_repeated_doi_in_hal_creates_one_item(config, collections):
    actions, _, _ = build_plan(
        [publication(), publication(halId_s="hal-87654321")], [], collections, config, FakeClient()
    )
    assert len(actions) == 1
    assert "hal-87654321" in actions[0]["data"]["extra"]


def test_doi_does_not_turn_a_preprint_into_a_journal_article():
    data = new_item(publication(docType_s="UNDEFINED"), FakeClient())
    assert data["itemType"] == "preprint"
    assert data["creators"] == [{"creatorType": "author", "firstName": "Jane", "lastName": "Doe"}]


def test_collections_resolved_and_writes_batched(config, collections):
    tree = Collections(config, collections)
    token = tree.child("WPKEY1", "Software")
    actions = [{"data": {"collections": [token]}} for _ in range(51)]
    client = FakeClient()
    apply_plan(client, actions, tree)
    assert [len(objects) for _, objects in client.calls] == [1, 50, 1]
    assert client.calls[1][1][0]["collections"] == ["CREATED0"]


def test_wrong_collection_tree_is_rejected(config, collections):
    collections[1]["data"]["parentCollection"] = "EXTERNAL"
    with pytest.raises(ValueError, match="Our Publications"):
        Collections(config, collections)


def test_partial_write_failure_is_reported():
    client = ZoteroClient(1, "not-a-real-key")
    client.version = "1"
    with patch.object(
        client,
        "request",
        return_value=({"failed": {"0": {"code": 400}}}, {"Last-Modified-Version": "2"}),
    ):
        with pytest.raises(RuntimeError, match="rejected"):
            client.write("items", [{}])


def test_library_changes_abort_pagination():
    client = ZoteroClient(1)
    responses = [
        ([{}], {"Total-Results": "2", "Last-Modified-Version": "1"}),
        ([{}], {"Total-Results": "2", "Last-Modified-Version": "2"}),
    ]
    with patch.object(client, "request", side_effect=responses):
        with pytest.raises(RuntimeError, match="changed"):
            client.list_all("items/top")


def test_read_only_key_is_rejected_before_writes():
    client = ZoteroClient(1, "not-a-real-key")
    permissions = {"access": {"groups": {"all": {"library": True, "write": False}}}}
    with patch.object(client, "request", return_value=(permissions, {})):
        with pytest.raises(ValueError, match="no write access"):
            client.require_write_access()


def test_site_uses_one_zotero_item_with_multiple_wp_memberships(config, collections):
    item = existing(collections=["WPKEY2ART", "WPKEY6ART"])
    labels = confirmed_workpackages([publication()], [item], collections, config)
    assert labels == {"hal-12345678": ["WP2", "WP6"]}


def test_site_omits_unassigned_and_ambiguous_wp_labels(config, collections):
    unassigned = existing(collections=["ROOT"])
    ambiguous = existing(key="SECOND", collections=["WPKEY5ART"])
    ambiguous["key"] = "SECOND"
    assert confirmed_workpackages([publication()], [unassigned], collections, config) == {
        "hal-12345678": []
    }
    assert confirmed_workpackages(
        [publication()], [unassigned, ambiguous], collections, config
    ) == {"hal-12345678": []}


def test_site_does_not_use_external_publications_wp_tree(config, collections):
    external = existing(collections=["EXTERNAL_WP3_ART"])
    assert confirmed_workpackages([publication()], [external], collections, config) == {
        "hal-12345678": []
    }
