"""Tests for highlight metadata generation."""

from pathlib import Path

from harvest.highlights import (
    DEFAULT_PARTIALS_DIR,
    generate_highlight_cards,
    highlights_for_year,
    output_partials,
    resolve_partials_dir,
)


def test_generate_highlight_cards_links_to_detail_page():
    highlights = [
        {
            "title": "HPDDM in PETSc 3.25",
            "summary": "Robust preconditioners for PETSc workflows",
            "page": "highlights/hpddm-petsc-3-25.adoc",
            "icon": "network-wired",
            "role": "text-success",
        }
    ]

    content = "\n".join(generate_highlight_cards(highlights))

    assert "xref:highlights/hpddm-petsc-3-25.adoc[HPDDM in PETSc 3.25]" in content
    assert "Robust preconditioners" in content


def test_highlights_for_year_filters_by_year():
    config = {
        "highlights": [
            {"title": "A", "year": 2026},
            {"title": "B", "year": 2025},
        ]
    }

    assert [item["title"] for item in highlights_for_year(config, 2026)] == ["A"]


def test_output_partials_writes_current_and_year_files(tmp_path):
    config = {
        "current_year": 2026,
        "highlights": [
            {"title": "A", "year": 2026},
            {"title": "B", "year": 2025},
        ],
    }

    output_partials(config, tmp_path)

    assert (tmp_path / "highlights-current.adoc").exists()
    assert (tmp_path / "highlights-2026.adoc").exists()
    assert (tmp_path / "highlights-2025.adoc").exists()


def test_resolve_partials_dir_uses_unified_output_config(tmp_path):
    exama = tmp_path / "exama.yaml"
    exama.write_text(
        "output:\n  partials_dir: custom/partials\n",
        encoding="utf-8",
    )

    assert resolve_partials_dir(exama) == Path("custom/partials")


def test_resolve_partials_dir_falls_back_to_antora_partials(tmp_path):
    assert resolve_partials_dir(tmp_path / "missing.yaml") == DEFAULT_PARTIALS_DIR
