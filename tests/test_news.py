"""Tests for news and event generation."""

from pathlib import Path

from harvest.news import DEFAULT_PARTIALS_DIR, resolve_partials_dir
from harvest.news import generate_archive_by_year


def test_archive_includes_recent_and_archived_events():
    events = [
        {
            "id": "recent-event",
            "status": "recent",
            "type": "assembly",
            "title": "Recent Event",
            "date": "2026-01-10",
        },
        {
            "id": "archived-event",
            "status": "archived",
            "type": "workshop",
            "title": "Archived Event",
            "date": "2026-01-05",
        },
        {
            "id": "upcoming-event",
            "status": "upcoming",
            "type": "training",
            "title": "Upcoming Event",
            "date": "2026-06-01",
        },
    ]

    archive = generate_archive_by_year(events)
    content = "\n".join(archive[2026])

    assert "Recent Event" in content
    assert "Archived Event" in content
    assert "Upcoming Event" not in content


def test_resolve_partials_dir_uses_unified_output_config(tmp_path):
    exama = tmp_path / "exama.yaml"
    exama.write_text(
        "output:\n  partials_dir: custom/partials\n",
        encoding="utf-8",
    )

    assert resolve_partials_dir(exama) == Path("custom/partials")


def test_resolve_partials_dir_falls_back_to_antora_partials(tmp_path):
    assert resolve_partials_dir(tmp_path / "missing.yaml") == DEFAULT_PARTIALS_DIR
