"""Tests for training catalog generation."""

from pathlib import Path

from harvest.training import (
    DEFAULT_PARTIALS_DIR,
    format_date_range,
    generate_training_catalog,
    load_config_with_fallback,
    output_partials,
    resolve_partials_dir,
)


def test_format_date_range_for_same_month_range():
    item = {"date": "2026-06-08", "end_date": "2026-06-12"}

    assert format_date_range(item) == "Jun 08-12, 2026"


def test_generate_training_catalog_includes_title_and_topics():
    trainings = [
        {
            "title": "MAJSC 2026: ML & Autodiff in JAX",
            "date": "2026-06-08",
            "topics": ["JAX fundamentals"],
            "resources": [{"title": "Notes", "url": "https://notes.example.org"}],
            "url": "https://example.org",
        }
    ]

    content = "\n".join(generate_training_catalog(trainings))

    assert "MAJSC 2026" in content
    assert "JAX fundamentals" in content
    assert "https://notes.example.org[Notes]" in content
    assert "https://example.org[Training details]" in content


def test_output_partials_writes_training_catalog(tmp_path):
    config = {"trainings": [{"title": "Training", "date": "2026-01-01"}]}

    output_partials(config, tmp_path)

    output = tmp_path / "training-catalog.adoc"
    assert output.exists()
    assert "// Trainings: 1" in output.read_text(encoding="utf-8")


def test_load_config_with_fallback_uses_unified_training_file(tmp_path, monkeypatch):
    exama = tmp_path / "exama.yaml"
    training = tmp_path / "training.yaml"
    exama.write_text(
        "sources:\n  training:\n    type: yaml\n    file: training.yaml\n",
        encoding="utf-8",
    )
    training.write_text(
        "trainings:\n  - id: t1\n    title: Test Training\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("harvest.training.DEFAULT_UNIFIED_CONFIG", exama)
    monkeypatch.setattr("harvest.training.DEFAULT_CONFIG", Path("missing.yaml"))

    config = load_config_with_fallback()

    assert config["trainings"][0]["title"] == "Test Training"


def test_resolve_partials_dir_uses_unified_output_config(tmp_path):
    exama = tmp_path / "exama.yaml"
    exama.write_text(
        "output:\n  partials_dir: custom/partials\n",
        encoding="utf-8",
    )

    assert resolve_partials_dir(exama) == Path("custom/partials")


def test_resolve_partials_dir_falls_back_to_antora_partials(tmp_path):
    assert resolve_partials_dir(tmp_path / "missing.yaml") == DEFAULT_PARTIALS_DIR
