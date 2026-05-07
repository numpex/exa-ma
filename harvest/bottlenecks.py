"""Utilities for Exa-MA bottleneck tags."""

from __future__ import annotations

import re
from typing import Any


BOTTLENECKS: dict[str, dict[str, str]] = {
    "B1": {
        "title": "Energy efficiency",
        "role": "text-warning",
        "short": "Develop energy-efficient technologies to meet the exascale power envelope.",
    },
    "B2": {
        "title": "Interconnect technology",
        "role": "text-info",
        "short": "Improve intra-node and inter-node data movement in energy efficiency and performance.",
    },
    "B3": {
        "title": "Memory technology",
        "role": "text-info",
        "short": "Integrate new memory technologies for capacity, bandwidth, resiliency, and energy efficiency.",
    },
    "B4": {
        "title": "Scalable system software",
        "role": "text-primary",
        "short": "Increase scalability, power sensitivity, and resiliency of operating systems, runtimes, and monitoring.",
    },
    "B5": {
        "title": "Programming systems",
        "role": "text-primary",
        "short": "Develop programming paradigms for fine-grained concurrency, locality, and resilience.",
    },
    "B6": {
        "title": "Data management",
        "role": "text-info",
        "short": "Handle massive data volumes, including analysis, compression, and fault-tolerant I/O.",
    },
    "B7": {
        "title": "Exascale algorithms",
        "role": "text-primary",
        "short": "Redesign algorithms to reduce communication, avoid or hide synchronization, and exploit accelerators.",
    },
    "B8": {
        "title": "Discovery, design, and decision algorithms",
        "role": "text-success",
        "short": "Move beyond single heroic simulations toward ensembles for UQ, optimization, and decision workflows.",
    },
    "B9": {
        "title": "Resilience, robustness and accuracy",
        "role": "text-warning",
        "short": "Ensure computations are correct, reproducible, and verifiable despite software or hardware errors.",
    },
    "B10": {
        "title": "Scientific productivity",
        "role": "text-success",
        "short": "Provide tools to develop, run, prepare, collect, and analyze exascale scientific workflows productively.",
    },
    "B11": {
        "title": "Reproducibility and replicability",
        "role": "text-danger",
        "short": "Provide the data, codes, and practices needed to re-obtain and validate computational results.",
    },
    "B12": {
        "title": "Pre/post processing",
        "role": "text-info",
        "short": "Scale visualization, in situ processing, and preparation/analysis steps around simulations.",
    },
    "B13": {
        "title": "Uncertainty integration",
        "role": "text-purple",
        "short": "Integrate uncertainties directly into the core calculation rather than treating them after the fact.",
    },
}

_BOTTLENECK_RE = re.compile(r"\bB(?:1[0-3]|[1-9])\b", re.IGNORECASE)


def normalize_bottleneck_ids(values: Any) -> list[str]:
    """Extract stable bottleneck IDs from free-form sheet/YAML values."""
    if not values:
        return []

    if isinstance(values, str):
        candidates = [values]
    elif isinstance(values, list):
        candidates = [str(value) for value in values if value]
    else:
        candidates = [str(values)]

    ids: list[str] = []
    for candidate in candidates:
        for match in _BOTTLENECK_RE.findall(candidate):
            bid = match.upper()
            if bid in BOTTLENECKS and bid not in ids:
                ids.append(bid)
    return ids


def bottleneck_badges(values: Any) -> str:
    """Render bottleneck IDs as compact AsciiDoc badge text."""
    ids = normalize_bottleneck_ids(values)
    if not ids:
        return ""
    return " ".join(
        f"`{bid}` {BOTTLENECKS[bid]['title']}"
        for bid in ids
    )


def linked_bottleneck_badges(
    values: Any,
    target: str = "ROOT:bottlenecks.adoc",
) -> str:
    """Render bottleneck IDs as links to their definition page anchors."""
    ids = normalize_bottleneck_ids(values)
    if not ids:
        return ""
    return " ".join(
        f"xref:{target}#{bid.lower()}[`{bid}` {BOTTLENECKS[bid]['title']}]"
        for bid in ids
    )
