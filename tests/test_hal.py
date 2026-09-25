"""Tests for HAL publications harvesting."""

import pytest

from harvest.hal import (
    format_publication,
    infer_publication_type,
    select_best_versions,
    build_query_params,
    DEFAULT_QUERY,
    DEFAULT_DOMAINS,
    DEFAULT_YEARS,
    output_asciidoc,
)


class TestInferPublicationType:
    """Tests for publication type inference."""

    def test_journal_article(self):
        """Test journal article type detection."""
        result = infer_publication_type(
            "ART",
            doc_type_label="Journal article",
            journal_title="Test Journal",
        )

        assert result["publication_type"] == "journal-article"
        assert result["publication_type_label"] == "Article in journal"

    def test_conference_paper(self):
        """Test conference paper type detection."""
        result = infer_publication_type(
            "COMM",
            doc_type_label="Conference paper",
            conference_title="Test Conference",
        )

        assert result["publication_type"] == "conference-paper"
        assert result["publication_type_label"] == "Conference paper"

    def test_thesis(self):
        """Test thesis type detection."""
        result = infer_publication_type("THESE", doc_type_label="PhD thesis")

        assert result["publication_type"] == "thesis"

    def test_preprint_with_doi_becomes_article(self):
        """Test that preprints with DOI are classified as articles."""
        result = infer_publication_type(
            "UNDEFINED",
            doi="10.1234/test.doi",
        )

        assert result["publication_type"] == "journal-article"

    def test_preprint_with_conference_becomes_paper(self):
        """Test that preprints with conference become conference papers."""
        result = infer_publication_type(
            "UNDEFINED",
            conference_title="Some Conference",
        )

        assert result["publication_type"] == "conference-paper"


class TestSelectBestVersions:
    """Tests for version selection logic."""

    def test_single_publication(self):
        """Test with single publication."""
        pubs = [
            {
                "halId_s": "hal-12345",
                "version_i": 1,
                "docType_s": "ART",
                "producedDate_s": "2024-01-01",
            }
        ]

        result = select_best_versions(pubs)

        assert len(result) == 1
        assert result[0]["halId_s"] == "hal-12345"

    def test_multiple_versions_same_id(self):
        """Test that best version is selected for same HAL id."""
        pubs = [
            {
                "halId_s": "hal-12345",
                "version_i": 1,
                "docType_s": "UNDEFINED",
                "producedDate_s": "2024-01-01",
            },
            {
                "halId_s": "hal-12345",
                "version_i": 2,
                "docType_s": "ART",
                "journalTitle_s": "Test Journal",
                "producedDate_s": "2024-06-01",
            },
        ]

        result = select_best_versions(pubs)

        assert len(result) == 1
        assert result[0]["version_i"] == 2
        assert result[0]["_hal_versions_found_i"] == 2

    def test_different_publications_kept(self):
        """Test that different publications are all kept."""
        pubs = [
            {
                "halId_s": "hal-12345",
                "version_i": 1,
                "docType_s": "ART",
                "producedDate_s": "2024-01-01",
            },
            {
                "halId_s": "hal-67890",
                "version_i": 1,
                "docType_s": "COMM",
                "producedDate_s": "2024-02-01",
            },
        ]

        result = select_best_versions(pubs)

        assert len(result) == 2


class TestFormatPublication:
    """Tests for publication formatting."""

    def test_format_basic_publication(self, sample_hal_response):
        """Test formatting a basic publication."""
        doc = sample_hal_response["response"]["docs"][0]
        formatted = format_publication(doc)

        assert formatted["hal_id"] == "hal-12345"
        assert formatted["title"] == "Test Publication Title"
        assert formatted["authors"] == ["Author One", "Author Two"]
        assert formatted["year"] == 2024
        assert formatted["publication_type"] == "journal-article"

    def test_format_conference_paper(self, sample_hal_response):
        """Test formatting a conference paper."""
        doc = sample_hal_response["response"]["docs"][1]
        formatted = format_publication(doc)

        assert formatted["hal_id"] == "hal-12346"
        assert formatted["conference"] == "Test Conference 2024"
        assert formatted["publication_type"] == "conference-paper"


class TestBuildQueryParams:
    """Tests for query parameter building."""

    def test_default_params(self):
        """Test default query parameters."""
        params = build_query_params()

        assert params["q"] == DEFAULT_QUERY
        assert "fq" in params
        assert len(params["fq"]) == 2  # domain and year filters

    def test_custom_years(self):
        """Test custom year filtering."""
        params = build_query_params(years=[2024, 2025])

        year_filter = [fq for fq in params["fq"] if "publicationDateY_i" in fq][0]
        assert "2024" in year_filter
        assert "2025" in year_filter

    def test_custom_domains(self):
        """Test custom domain filtering."""
        params = build_query_params(domains=["math", "phys"])

        domain_filter = [fq for fq in params["fq"] if "level0_domain_s" in fq][0]
        assert "math" in domain_filter
        assert "phys" in domain_filter

    def test_pagination(self):
        """Test pagination parameters."""
        params = build_query_params(start=100, rows=50)

        assert params["start"] == "100"
        assert params["rows"] == "50"

    def test_explicit_empty_filters_harvest_all_project_records(self):
        params = build_query_params(years=[], domains=[])
        assert params["fq"] == []
        assert params["q"] == DEFAULT_QUERY


def test_publication_table_links_multiple_wps_in_one_row():
    record = {
        "halId_s": "hal-12345",
        "uri_s": "https://hal.science/hal-12345",
        "title_s": ["A publication"],
        "authFullName_s": ["Jane Doe"],
        "docType_s": "ART",
        "publicationDateY_i": 2025,
        "producedDate_s": "2025-01-01",
    }
    content = output_asciidoc(
        [record], partial=True, wp_assignments={"hal-12345": ["WP2", "WP6"]}
    )
    assert "|Title |Authors |Type |WPs |Links" in content
    assert "|xref:workpackages/wp2.adoc[WP2], xref:workpackages/wp6.adoc[WP6]" in content
    assert content.count("|*A publication*") == 1

    without_wp = output_asciidoc([record], partial=True, wp_assignments={"hal-12345": []})
    assert "|xref:workpackages/" not in without_wp
    assert without_wp.count("|*A publication*") == 1

    preview = output_asciidoc(
        [record], partial=True, wp_assignments={"hal-12345": ["WP2"]},
        proposed_wp_assignments={"hal-12345": ["WP2", "WP6"]},
    )
    assert "== Proposed WP distribution" in preview
    assert "|xref:workpackages/wp2.adoc[WP2] |1 |0" in preview
    assert "|xref:workpackages/wp6.adoc[WP6] |0 |1" in preview
    assert "xref:workpackages/wp2.adoc[WP2], xref:workpackages/wp6.adoc[WP6] (proposed)" in preview
    assert preview.count("|*A publication*") == 1
