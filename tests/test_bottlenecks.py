"""Tests for Exa-MA bottleneck tag utilities."""

from harvest.bottlenecks import (
    bottleneck_badges,
    linked_bottleneck_badges,
    normalize_bottleneck_ids,
)


def test_normalize_bottleneck_ids_extracts_sheet_values():
    values = [
        "B6 - Data Management",
        '"B9 - Resilience; Robustness; Accuracy"',
        "(B11) Reproducibility and Replicability of Computation",
    ]

    assert normalize_bottleneck_ids(values) == ["B6", "B9", "B11"]


def test_bottleneck_badges_renders_known_labels():
    badges = bottleneck_badges(["B7 - Exascale Algorithms", "B10"])

    assert "`B7` Exascale algorithms" in badges
    assert "`B10` Scientific productivity" in badges


def test_linked_bottleneck_badges_point_to_overview_anchor():
    badges = linked_bottleneck_badges(["B7"])

    assert (
        "xref:ROOT:bottlenecks.adoc#b7[`B7` Exascale algorithms]"
        in badges
    )
