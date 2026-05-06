"""Tests for news and event generation."""

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
