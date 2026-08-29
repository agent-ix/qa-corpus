#!/usr/bin/env python3
"""Validate the exact external-witness contract without running its producer."""

from __future__ import annotations

import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    manifest = json.loads((ROOT / "config/external-channel.json").read_text())
    problems: list[str] = []
    if manifest.get("schemaVersion") != "qa-external-channel-v1":
        problems.append("external channel schema version is not qa-external-channel-v1")
    producer = manifest.get("producer") or {}
    revision = producer.get("sourceRevision")
    if not isinstance(revision, str) or len(revision) != 40:
        problems.append("external producer sourceRevision is not a full SHA")
    if not producer.get("versionOutput"):
        problems.append("external producer versionOutput is empty")
    channels = manifest.get("channels") or {}
    for kind, channel in channels.items():
        command = channel.get("command") if isinstance(channel, dict) else None
        if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
            problems.append(f"{kind}: command is not a non-empty string array")
        elif "{repo}" not in command:
            problems.append(f"{kind}: command does not name the controlled repository")
        if not channel.get("owner"):
            problems.append(f"{kind}: non-Quire owner is not declared")

    cases = 0
    failures = 0
    controls = 0
    observed: set[str] = set()
    for expect_path in sorted((ROOT / "cases").glob("*/*/**/expect.yaml")):
        expect = yaml.safe_load(expect_path.read_text()) or {}
        if "external_observations" not in expect:
            continue
        cases += 1
        values = expect.get("external_observations") or []
        observed.update(str(value.get("kind")) for value in values if isinstance(value, dict))
        if values:
            failures += 1
        else:
            controls += 1
    if cases == 0 or failures == 0 or controls == 0:
        problems.append(f"external population is incomplete: {cases} cases, {failures} failures, {controls} controls")
    unknown = observed - set(channels)
    if unknown:
        problems.append(f"external observations have no producer channel: {sorted(unknown)}")
    unused = set(channels) - observed
    if unused:
        problems.append(f"external producer channels have no positive observation: {sorted(unused)}")
    if problems:
        for problem in problems:
            print(f"external channel: {problem}", file=sys.stderr)
        return 1
    print(
        f"external channel: {cases} cases ({failures} failures, {controls} controls), "
        f"{len(channels)} exact producer commands"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
