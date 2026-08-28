#!/usr/bin/env python3
"""Reject unexplained byte-copy drift in self-contained corpus fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "config/duplicate-census.json"


def census() -> dict:
    by_digest: dict[str, list[str]] = defaultdict(list)
    for path in sorted((ROOT / "cases").rglob("*")):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            by_digest[digest].append(str(path.relative_to(ROOT)))
    groups = []
    for digest, paths in sorted(by_digest.items()):
        if len(paths) < 2:
            continue
        groups.append(
            {
                "sha256": digest,
                "classification": "intentional-self-contained-fixture",
                "invariant": (
                    "Each case remains independently runnable; byte-identical support files "
                    "must change together unless the case's declared defect requires divergence."
                ),
                "paths": paths,
            }
        )
    return {
        "schemaVersion": "qa-duplicate-census-v1",
        "scope": "cases/** regular files",
        "groups": groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    actual = census()
    if args.update:
        BASELINE.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
        print(f"duplicate census: wrote {len(actual['groups'])} classified groups")
        return 0
    try:
        expected = json.loads(BASELINE.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"duplicate census: baseline unreadable: {error}", file=sys.stderr)
        return 1
    if actual != expected:
        expected_by = {group["sha256"]: group for group in expected.get("groups", [])}
        actual_by = {group["sha256"]: group for group in actual["groups"]}
        print("duplicate census: unexplained fixture-copy drift", file=sys.stderr)
        for digest in sorted(expected_by.keys() - actual_by.keys()):
            print(f"- disappeared group {digest}: {expected_by[digest]['paths']}", file=sys.stderr)
        for digest in sorted(actual_by.keys() - expected_by.keys()):
            print(f"- new group {digest}: {actual_by[digest]['paths']}", file=sys.stderr)
        for digest in sorted(expected_by.keys() & actual_by.keys()):
            if expected_by[digest] != actual_by[digest]:
                print(f"- membership changed {digest}", file=sys.stderr)
        print(
            "Review the relationship, then run `python3 scripts/duplicate_census.py --update` "
            "and commit the code/census change together.",
            file=sys.stderr,
        )
        return 1
    print(
        f"duplicate census: {len(actual['groups'])} intentional groups; no unexplained drift"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
