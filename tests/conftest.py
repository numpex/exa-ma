"""Pytest fixtures for Exa-MA harvest tests."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml


@pytest.fixture
def sample_exama_config() -> dict:
    """Sample exama.yaml configuration."""
    return {
        "project": {
            "name": "Exa-MA",
            "anr_id": "ANR-22-EXNU-0002",
        },
        "sources": {
            "publications": {
                "type": "hal",
                "query": "anrProjectReference_s:ANR-22-EXNU-0002",
                "domains": ["math", "info"],
                "years": [2024, 2025],
            },
            "deliverables": {
                "type": "github",
                "settings": {
                    "max_releases": 5,
                    "include_prereleases": False,
                },
                "items": [
                    {
                        "id": "D7.1",
                        "repo": "numpex/exa-ma-d7.1",
                        "title": "Test Deliverable",
                        "description": "Test description",
                        "workpackages": ["WP7"],
                    }
                ],
            },
            "software": {
                "type": "google_sheets",
                "sheet_id": "test-sheet-id",
                "sheets": {
                    "frameworks": "Frameworks",
                    "packaging": "Packaging",
                    "applications": "Applications",
                },
            },
            "team": {
                "type": "google_sheets",
                "sheet_id": "test-team-sheet-id",
                "sheet_name": "All Exa-MA",
                "filter": {
                    "funded_only": True,
                    "active_only": False,
                },
            },
            "news": {
                "type": "yaml",
                "file": "news.yaml",
            },
        },
        "output": {
            "partials_dir": "docs/modules/ROOT/partials",
            "software_pages_dir": "docs/modules/software/pages",
        },
    }


@pytest.fixture
def sample_news_config() -> dict:
    """Sample news.yaml configuration."""
    return {
        "events": [
            {
                "id": "test-event",
                "type": "assembly",
                "status": "upcoming",
                "title": "Test Event",
                "date": "2025-06-01",
                "location": "Test Location",
                "icon": "users",
                "description": "Test event description",
            },
            {
                "id": "past-event",
                "type": "conference",
                "status": "archived",
                "title": "Past Event",
                "date": "2024-01-15",
                "location": "Past Location",
                "icon": "chalkboard-teacher",
                "description": "Past event description",
            },
        ]
    }


@pytest.fixture
def temp_config_dir(sample_exama_config, sample_news_config):
    """Create a temporary directory with config files."""
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write exama.yaml
        exama_path = tmpdir / "exama.yaml"
        with open(exama_path, "w") as f:
            yaml.dump(sample_exama_config, f)

        # Write news.yaml
        news_path = tmpdir / "news.yaml"
        with open(news_path, "w") as f:
            yaml.dump(sample_news_config, f)

        yield tmpdir


@pytest.fixture
def sample_hal_response() -> dict:
    """Sample HAL API response."""
    return {
        "response": {
            "numFound": 2,
            "docs": [
                {
                    "docid": 12345,
                    "halId_s": "hal-12345",
                    "version_i": 1,
                    "uri_s": "https://hal.science/hal-12345v1",
                    "title_s": ["Test Publication Title"],
                    "authFullName_s": ["Author One", "Author Two"],
                    "producedDate_s": "2024-06-15",
                    "publicationDateY_i": 2024,
                    "docType_s": "ART",
                    "docTypeLabel_s": "Journal article",
                    "journalTitle_s": "Test Journal",
                    "doiId_s": "10.1234/test.doi",
                },
                {
                    "docid": 12346,
                    "halId_s": "hal-12346",
                    "version_i": 1,
                    "uri_s": "https://hal.science/hal-12346v1",
                    "title_s": ["Another Publication"],
                    "authFullName_s": ["Author Three"],
                    "producedDate_s": "2024-05-10",
                    "publicationDateY_i": 2024,
                    "docType_s": "COMM",
                    "docTypeLabel_s": "Conference paper",
                    "conferenceTitle_s": "Test Conference 2024",
                },
            ],
        }
    }


@pytest.fixture
def sample_github_releases() -> list[dict]:
    """Sample GitHub releases API response."""
    return [
        {
            "tag_name": "v1.0.0",
            "name": "Release v1.0.0",
            "published_at": "2024-06-01T12:00:00Z",
            "html_url": "https://github.com/test/repo/releases/v1.0.0",
            "body": "Initial release",
            "prerelease": False,
            "draft": False,
            "assets": [
                {
                    "name": "test-v1.0.0.pdf",
                    "browser_download_url": "https://github.com/test/repo/releases/download/v1.0.0/test-v1.0.0.pdf",
                }
            ],
        },
        {
            "tag_name": "v0.9.0",
            "name": "Beta Release",
            "published_at": "2024-05-01T12:00:00Z",
            "html_url": "https://github.com/test/repo/releases/v0.9.0",
            "body": "Beta release",
            "prerelease": True,
            "draft": False,
            "assets": [],
        },
    ]
