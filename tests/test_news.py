"""Tests for news and event generation."""

from pathlib import Path

from harvest.news import DEFAULT_PARTIALS_DIR, resolve_partials_dir
from harvest.news import event_detail_link, generate_archive_by_year, generate_home_cards, output_partials


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


def test_generate_home_cards_prefers_upcoming_events():
    events = [
        {
            "status": "recent",
            "type": "announcement",
            "title": "Recent Event",
            "date": "2026-01-10",
            "description": "Recent update",
        },
        {
            "status": "upcoming",
            "type": "training",
            "title": "Upcoming Event",
            "date": "2026-06-01",
            "description": "Upcoming training",
            "url": "https://example.org/training",
        },
    ]

    content = "\n".join(generate_home_cards(events, limit=1))

    assert "Upcoming Event" in content
    assert "https://example.org/training[Upcoming Event]" in content
    assert "Recent Event" not in content


def test_event_detail_link_skips_missing_page_xref():
    event = {
        "page": "news/2099/missing.adoc",
        "url": "https://example.org/archive",
    }

    assert event_detail_link(event, "Read full recap →", "External details") == (
        "https://example.org/archive[External details]"
    )


def test_event_detail_link_returns_empty_without_existing_target():
    event = {"page": "news/2099/missing.adoc"}

    assert event_detail_link(event, "Read full recap →", "External details") == ""


def test_output_partials_writes_homepage_news(tmp_path):
    config = {
        "events": [
            {
                "status": "recent",
                "type": "announcement",
                "title": "Recent Event",
                "date": "2026-01-10",
                "description": "Recent update",
            }
        ]
    }

    output_partials(config, tmp_path)

    assert (tmp_path / "news-home.adoc").exists()
    assert "Recent Event" in (tmp_path / "news-home.adoc").read_text(encoding="utf-8")


def test_resolve_partials_dir_uses_unified_output_config(tmp_path):
    exama = tmp_path / "exama.yaml"
    exama.write_text(
        "output:\n  partials_dir: custom/partials\n",
        encoding="utf-8",
    )

    assert resolve_partials_dir(exama) == Path("custom/partials")


def test_resolve_partials_dir_falls_back_to_antora_partials(tmp_path):
    assert resolve_partials_dir(tmp_path / "missing.yaml") == DEFAULT_PARTIALS_DIR
