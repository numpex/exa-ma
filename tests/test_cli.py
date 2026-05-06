"""Tests for the combined harvest CLI."""

import argparse
from pathlib import Path

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
