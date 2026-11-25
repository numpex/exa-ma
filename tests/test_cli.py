"""Tests for the combined harvest CLI."""

import argparse
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import URLError

import pytest

from harvest import cli, hal, theses
from harvest.cli import DEFAULT_PARTIALS_DIR, resolve_all_output_dir
from harvest.config import ExaMAConfig


def test_resolve_all_output_dir_uses_explicit_output_dir():
    args = argparse.Namespace(output_dir="custom-output")

    assert resolve_all_output_dir(args) == Path("custom-output")


def test_resolve_all_output_dir_uses_configured_partials_dir_by_default():
    args = argparse.Namespace(output_dir=None)
    config = ExaMAConfig.from_dict(
        {"output": {"partials_dir": "site/modules/ROOT/partials"}}
    )

    assert resolve_all_output_dir(args, config) == Path("site/modules/ROOT/partials")


def test_resolve_all_output_dir_falls_back_to_antora_partials_dir():
    args = argparse.Namespace(output_dir=None)

    assert resolve_all_output_dir(args) == DEFAULT_PARTIALS_DIR


@pytest.mark.parametrize("saved_publications", [None, "Saved HAL publications\n"])
def test_harvest_all_continues_after_hal_timeout(tmp_path, monkeypatch, capsys, saved_publications):
    partial = tmp_path / "publications-hal.adoc"
    if saved_publications is not None:
        partial.write_text(saved_publications)

    first_page = io.BytesIO(b'{"response": {"numFound": 2, "docs": [{"halId_s": "hal-1"}]}}')
    fetch_hal_page = Mock(side_effect=[first_page, URLError(TimeoutError("timed out"))])
    monkeypatch.setattr(hal, "urlopen", fetch_hal_page)
    monkeypatch.setattr(cli, "fetch_all_deliverables", Mock(return_value=[{}]))
    monkeypatch.setattr(cli, "releases_asciidoc", Mock())
    personnel = SimpleNamespace(unique_personnel=lambda: [])
    monkeypatch.setattr(cli, "fetch_recruited_with_config", Mock(return_value=personnel))
    monkeypatch.setattr(theses, "harvest_theses", Mock())
    partners = SimpleNamespace(partners=[])
    monkeypatch.setattr(cli, "fetch_partners_with_config", Mock(return_value=partners))

    result = cli.harvest_all(argparse.Namespace(output_dir=tmp_path))

    assert fetch_hal_page.call_count == 2
    assert (tmp_path / "news-home.adoc").is_file()
    warnings = capsys.readouterr().err
    assert "timed out" in warnings
    if saved_publications is None:
        assert result == 1
        assert not partial.exists()
        assert "no saved partial" in warnings
    else:
        assert result == 0
        assert partial.read_text() == saved_publications
        assert f"Using saved partial {partial}" in warnings
