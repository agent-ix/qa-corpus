#!/usr/bin/env python3
"""Check that the governed collection is derived and plan-complete."""

from __future__ import annotations

import pathlib
import sys

from export_measurements import build_collection

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    collection = build_collection(
        ROOT,
        timestamp="2026-08-27T00:00:00.000Z",
        source_revision="selftest-source",
    )
    observations = collection["observations"]
    gap = [row for row in observations if row["metric"] == "bounds.gap_count"]
    recall = [row for row in observations if row["metric"] == "detection.recall"]
    problems: list[str] = []
    if len(gap) != 1 or gap[0]["value"] != 0:
        problems.append("the derived gap observation is not exactly zero")
    if not recall:
        problems.append("no runner recall observations were exported")
    if {row["dimensions"]["runner"] for row in recall} != {"quire-rs", "quoin"}:
        problems.append("the collection does not retain both runner boundaries")
    for row in recall:
        population = row["population"]
        expected = round(population["matched"] / population["examined"], 6)
        if row["value"] != expected:
            problems.append(f"{row['dimensions']}: recall was not derived from counts")
    if problems:
        print("measurement self-test: FAIL", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(
        "measurement self-test: 2/2 plans produced; "
        f"{len(recall)} partitioned recall observations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
