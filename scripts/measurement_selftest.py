#!/usr/bin/env python3
"""Check that the governed collection is derived and plan-complete."""

from __future__ import annotations

import pathlib
import sys
import json
import tempfile

from export_measurements import ExportError, build_collection, load_verification_stack

ROOT = pathlib.Path(__file__).resolve().parent.parent


def attestation(revision: str) -> dict:
    return {
        "schemaVersion": "verification-stack-attestation-v1",
        "lockDigest": "sha256:" + "1" * 64,
        "executableDigest": "sha256:" + "2" * 64,
        "sources": {
            "qa-corpus": {
                "revision": revision,
                "sourceState": "clean",
                "remote": "https://github.com/agent-ix/qa-corpus",
            }
        },
        "capabilities": ["fixture.capability"],
        "artifacts": {"fixture": "sha256:" + "3" * 64},
        "toolchains": {"node": "22.15.0", "rust": "1.94.1", "python": "3.10.12"},
    }


def main() -> int:
    source_revision = "a" * 40
    stack = attestation(source_revision)
    collection = build_collection(
        ROOT,
        timestamp="2026-08-27T00:00:00.000Z",
        source_revision=source_revision,
        verification_stack=stack,
    )
    observations = collection["observations"]
    gap = [row for row in observations if row["metric"] == "bounds.gap_count"]
    recall = [row for row in observations if row["metric"] == "detection.recall"]
    problems: list[str] = []
    if (
        collection.get("schemaVersion") != 2
        or collection.get("verificationStack") != stack
    ):
        problems.append(
            "the collection is not bound to its schema-v2 verification stack"
        )
    if collection.get("toolVersion") != f"git:{source_revision}":
        problems.append("the exporter toolVersion is not its exact source revision")
    if len(gap) != 1 or gap[0]["value"] != 0:
        problems.append("the derived gap observation is not exactly zero")
    if not recall:
        problems.append("no runner recall observations were exported")
    if {row["dimensions"]["runner"] for row in recall} != {"quire-rs", "quoin"}:
        problems.append("the collection does not retain both runner boundaries")
    observation_keys = [
        (row["metric"], json.dumps(row.get("dimensions", {}), sort_keys=True))
        for row in observations
    ]
    if len(observation_keys) != len(set(observation_keys)):
        problems.append("the collection contains duplicate metric dimensions")
    quoin_recall = [row for row in recall if row["dimensions"]["runner"] == "quoin"]
    if not quoin_recall or any(
        not row["dimensions"].get("family") for row in quoin_recall
    ):
        problems.append("Quoin recall observations lost their family partition")
    quire_recall = [row for row in recall if row["dimensions"]["runner"] == "quire-rs"]
    if any("family" in row["dimensions"] for row in quire_recall):
        problems.append("Quire recall observations invented a family partition")
    for row in recall:
        population = row["population"]
        if population["examined"] == 0:
            if row["state"] != "not_computed" or row["value"] is not None:
                problems.append(
                    f"{row['dimensions']}: zero population is not explicitly uncomputed"
                )
            if population["matched"] != 0 or not population["identity"].get(
                "exclusions"
            ):
                problems.append(
                    f"{row['dimensions']}: zero population lost its exclusions"
                )
        else:
            expected = round(population["matched"] / population["examined"], 6)
            if row["state"] != "measured" or row["value"] != expected:
                problems.append(
                    f"{row['dimensions']}: recall was not derived from counts"
                )
    with tempfile.TemporaryDirectory(prefix="qa-attestation-selftest-") as temp:
        path = pathlib.Path(temp) / "attestation.json"
        path.write_text(json.dumps(stack))
        loaded = load_verification_stack(
            path,
            source_revision=source_revision,
            source_remote="git@github.com:agent-ix/qa-corpus.git",
        )
        if loaded != stack:
            problems.append("the exact verification stack did not round-trip")
        mutations = [
            ("schema", {**stack, "schemaVersion": "moving-v2"}),
            ("digest", {**stack, "lockDigest": "sha256:short"}),
            (
                "executable digest",
                {**stack, "executableDigest": "sha256:short"},
            ),
            ("revision", attestation("b" * 40)),
            (
                "source state",
                {
                    **stack,
                    "sources": {
                        "qa-corpus": {
                            **stack["sources"]["qa-corpus"],
                            "sourceState": "dirty",
                        }
                    },
                },
            ),
            ("capability order", {**stack, "capabilities": ["z", "a"]}),
            (
                "capability duplication",
                {**stack, "capabilities": ["fixture", "fixture"]},
            ),
            ("artifact", {**stack, "artifacts": {"fixture": "moving"}}),
            ("toolchains", {**stack, "toolchains": {}}),
        ]
        for name, mutation in mutations:
            path.write_text(json.dumps(mutation))
            try:
                load_verification_stack(
                    path,
                    source_revision=source_revision,
                    source_remote="https://github.com/agent-ix/qa-corpus",
                )
            except ExportError:
                continue
            problems.append(f"the {name} attestation mutation did not fail closed")
        path.write_text(json.dumps(stack))
        try:
            load_verification_stack(
                path,
                source_revision=source_revision,
                source_remote="https://github.com/other/qa-corpus",
            )
        except ExportError:
            pass
        else:
            problems.append("the source remote mutation did not fail closed")
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
