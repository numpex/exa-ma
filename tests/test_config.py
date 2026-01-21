"""Tests for unified configuration loading."""

from pathlib import Path

import pytest

from harvest.config import (
    ExaMAConfig,
    load_config,
    PublicationsConfig,
    DeliverablesConfig,
    SoftwareConfig,
    TeamConfig,
    NewsConfig,
    merge_with_legacy_deliverables,
)


class TestExaMAConfig:
    """Tests for ExaMAConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExaMAConfig()

        assert config.project.name == "Exa-MA"
        assert config.project.anr_id == "ANR-22-EXNU-0002"

    def test_from_dict(self, sample_exama_config):
        """Test loading config from dictionary."""
        config = ExaMAConfig.from_dict(sample_exama_config)

        assert config.project.name == "Exa-MA"
        assert config.sources.publications.domains == ["math", "info"]
        assert config.sources.publications.years == [2024, 2025]

    def test_from_yaml(self, temp_config_dir):
        """Test loading config from YAML file."""
        config_path = temp_config_dir / "exama.yaml"
        config = ExaMAConfig.from_yaml(config_path)

        assert config.project.name == "Exa-MA"
        assert config._config_path == config_path

    def test_from_yaml_not_found(self, tmp_path):
        """Test error when YAML file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ExaMAConfig.from_yaml(tmp_path / "nonexistent.yaml")

    def test_get_publications_config(self, sample_exama_config):
        """Test getting publications configuration."""
        config = ExaMAConfig.from_dict(sample_exama_config)
        pub_config = config.get_publications_config()

        assert isinstance(pub_config, PublicationsConfig)
        assert pub_config.type == "hal"
        assert "math" in pub_config.domains

    def test_get_deliverables_config(self, sample_exama_config):
        """Test getting deliverables configuration."""
        config = ExaMAConfig.from_dict(sample_exama_config)
        del_config = config.get_deliverables_config()

        assert isinstance(del_config, DeliverablesConfig)
        assert len(del_config.items) == 1
        assert del_config.items[0].id == "D7.1"

    def test_get_software_config(self, sample_exama_config):
        """Test getting software configuration."""
        config = ExaMAConfig.from_dict(sample_exama_config)
        soft_config = config.get_software_config()

        assert isinstance(soft_config, SoftwareConfig)
        assert soft_config.sheet_id == "test-sheet-id"

    def test_get_team_config(self, sample_exama_config):
        """Test getting team configuration."""
        config = ExaMAConfig.from_dict(sample_exama_config)
        team_config = config.get_team_config()

        assert isinstance(team_config, TeamConfig)
        assert team_config.sheet_id == "test-team-sheet-id"
        assert team_config.filter.funded_only is True

    def test_get_news_config(self, sample_exama_config):
        """Test getting news configuration."""
        config = ExaMAConfig.from_dict(sample_exama_config)
        news_config = config.get_news_config()

        assert isinstance(news_config, NewsConfig)
        assert news_config.file == "news.yaml"

    def test_get_news_events_from_file(self, temp_config_dir):
        """Test loading news events from external file."""
        config = ExaMAConfig.from_yaml(temp_config_dir / "exama.yaml")
        events = config.get_news_events()

        assert len(events) == 2
        assert events[0].id == "test-event"
        assert events[1].id == "past-event"


class TestDeliverablesConfig:
    """Tests for DeliverablesConfig class."""

    def test_to_legacy_format(self, sample_exama_config):
        """Test conversion to legacy format."""
        config = ExaMAConfig.from_dict(sample_exama_config)
        del_config = config.get_deliverables_config()
        legacy = del_config.to_legacy_format()

        assert "settings" in legacy
        assert "deliverables" in legacy
        assert len(legacy["deliverables"]) == 1
        assert legacy["deliverables"][0]["id"] == "D7.1"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_from_path(self, temp_config_dir):
        """Test loading config from explicit path."""
        config = load_config(temp_config_dir / "exama.yaml")
        assert config.project.name == "Exa-MA"

    def test_load_default(self):
        """Test loading with no path returns defaults."""
        # This should return defaults if no config file is found
        config = load_config()
        assert config.project.name == "Exa-MA"


class TestNewsConfig:
    """Tests for NewsConfig class."""

    def test_load_events_from_file(self, temp_config_dir, sample_news_config):
        """Test loading events from external file."""
        from harvest.config import NewsConfig

        news_config = NewsConfig(file="news.yaml")
        events = news_config.load_events_from_file(temp_config_dir)

        assert len(events) == 2
        assert events[0].title == "Test Event"

    def test_load_events_file_not_found(self, tmp_path):
        """Test graceful handling when events file doesn't exist."""
        from harvest.config import NewsConfig

        news_config = NewsConfig(file="nonexistent.yaml", events=[])
        events = news_config.load_events_from_file(tmp_path)

        assert events == []

    def test_inline_events(self):
        """Test inline events without file reference."""
        from harvest.config import NewsConfig, NewsEvent

        inline_event = NewsEvent(
            id="inline-1",
            type="workshop",
            status="upcoming",
            title="Inline Event",
            date="2025-07-01",
        )

        news_config = NewsConfig(events=[inline_event])

        assert len(news_config.events) == 1
        assert news_config.events[0].title == "Inline Event"
