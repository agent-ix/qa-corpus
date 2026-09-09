#!/usr/bin/env python3
"""Validate the retained eight-consumer assurance-chain baseline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
BASELINE = ROOT / "compatibility" / "assurance-chain-baseline.json"
DRIVER_PATH = "scripts/assurance_chain.py"
REQUIRED = {
    "agent-ix/quire-analyze",
    "agent-ix/quire-contract-codegen",
    "agent-ix/quire-contract-ir",
    "agent-ix/quire-contract-runtime",
    "agent-ix/tl-mltl",
    "agent-ix/tl-parse",
    "agent-ix/tl-rewrite",
    "agent-ix/tl-syntax",
}
FR019_STATES = {
    "pass",
    "fail",
    "unavailable",
    "not-computed",
    "malformed",
    "stale",
    "tampered",
    "incomplete",
}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def fail(message: str) -> None:
    raise ValueError(message)


def validate_count(value: Any, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or set(value) != {"matched", "total"}:
        fail(f"{label} is not an exact matched/total count")
    matched = value["matched"]
    total = value["total"]
    if not isinstance(matched, int) or not isinstance(total, int) or total <= 0:
        fail(f"{label} is not a non-vacuous integer count")
    if matched < 0 or matched > total:
        fail(f"{label} has an impossible matched count")


def validate_document(document: Any) -> None:
    if not isinstance(document, dict):
        fail("baseline root is not an object")
    if document.get("schema_version") != "qa-corpus.assurance-chain-baseline/v1":
        fail("unknown assurance-chain baseline schema_version")
    if document.get("issue_ref") != "agent-ix/qa-corpus#20":
        fail("baseline does not name its owning issue")
    if document.get("driver_path") != DRIVER_PATH:
        fail("baseline driver path changed")
    if set(document.get("required_consumers", [])) != REQUIRED:
        fail("required consumer set is incomplete or invented")
    if set(document.get("required_comparison_states", [])) != FR019_STATES:
        fail("FR-019 comparison state set is incomplete or invented")
    if not str(document.get("semantic_gap", "")).strip():
        fail("the partial/incomplete semantic gap is not recorded")

    consumers = document.get("consumers")
    if not isinstance(consumers, list):
        fail("consumers is not an array")
    identities = [entry.get("repository") for entry in consumers if isinstance(entry, dict)]
    if len(identities) != len(set(identities)):
        fail("duplicate consumer repository")
    if set(identities) != REQUIRED:
        fail("consumer observations are incomplete or invented")

    reported_states: set[str] = set()
    for entry in consumers:
        repository = entry["repository"]
        if not HEX40.fullmatch(str(entry.get("revision", ""))):
            fail(f"{repository} has no exact revision")
        for field in ("driver_sha256", "observation_source_sha256"):
            if not HEX64.fullmatch(str(entry.get(field, ""))):
                fail(f"{repository} has an invalid {field}")
        source = entry.get("observation_source")
        if not isinstance(source, str) or source.startswith("/") or ".." in Path(source).parts:
            fail(f"{repository} has an unsafe observation source path")
        observation = entry.get("observation")
        if not isinstance(observation, dict) or observation.get("all_matched") is not True:
            fail(f"{repository} has no retained matched observation")
        for field in ("scenarios", "controls", "adapter_probes"):
            validate_count(observation.get(field), f"{repository}.{field}")
        states = observation.get("states_reported")
        if not isinstance(states, list) or any(not isinstance(item, str) for item in states):
            fail(f"{repository} states_reported is invalid")
        count = observation.get("states_reported_count")
        if count is not None and (not isinstance(count, int) or count <= 0):
            fail(f"{repository} states_reported_count is invalid")
        if states and count != len(states):
            fail(f"{repository} state count disagrees with its enumeration")
        counts = [observation.get(name) for name in ("scenarios", "controls", "adapter_probes")]
        if not any(item is not None for item in counts) and not states:
            fail(f"{repository} observation is vacuous")
        limitations = observation.get("limitations")
        witnesses = observation.get("witnesses")
        if not isinstance(limitations, list) or not all(str(item).strip() for item in limitations):
            fail(f"{repository} does not state its observation limits")
        if not isinstance(witnesses, list) or not witnesses or not all(str(item).strip() for item in witnesses):
            fail(f"{repository} has no retained observation witness")
        reported_states.update(states)

    legacy_required = FR019_STATES - {"incomplete"}
    if not legacy_required.issubset(reported_states):
        fail(f"enumerated legacy state coverage is incomplete: {sorted(legacy_required - reported_states)}")


def git_bytes(repo: Path, revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def validate_sources(document: dict[str, Any], source_root: Path) -> None:
    for entry in document["consumers"]:
        repository = entry["repository"]
        repo = source_root / repository.split("/", 1)[1]
        if not (repo / ".git").exists():
            fail(f"source checkout is missing: {repository}")
        revision = entry["revision"]
        published = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", revision, "origin/main"]
        )
        if published.returncode != 0:
            fail(f"recorded revision is not published on origin/main: {repository}@{revision}")
        driver = git_bytes(repo, revision, DRIVER_PATH)
        if hashlib.sha256(driver).hexdigest() != entry["driver_sha256"]:
            fail(f"driver digest mismatch: {repository}@{revision}")
        source = git_bytes(repo, revision, entry["observation_source"])
        if hashlib.sha256(source).hexdigest() != entry["observation_source_sha256"]:
            fail(f"observation-source digest mismatch: {repository}@{revision}")
        text = source.decode("utf-8")
        for witness in entry["observation"]["witnesses"]:
            if witness not in text:
                fail(f"observation witness missing: {repository}: {witness}")


def self_test(document: dict[str, Any]) -> None:
    mutations: list[tuple[str, Any]] = []

    missing = copy.deepcopy(document)
    missing["consumers"].pop()
    mutations.append(("missing consumer", missing))

    duplicate = copy.deepcopy(document)
    duplicate["consumers"].append(copy.deepcopy(duplicate["consumers"][0]))
    mutations.append(("duplicate consumer", duplicate))

    digest = copy.deepcopy(document)
    digest["consumers"][0]["driver_sha256"] = "0" * 63
    mutations.append(("invalid digest", digest))

    vacuous = copy.deepcopy(document)
    target = vacuous["consumers"][-1]["observation"]
    target["states_reported"] = []
    target["states_reported_count"] = None
    mutations.append(("vacuous observation", vacuous))

    gap = copy.deepcopy(document)
    gap["semantic_gap"] = ""
    mutations.append(("missing semantic gap", gap))

    for name, mutation in mutations:
        try:
            validate_document(mutation)
        except ValueError:
            continue
        fail(f"self-test mutation passed: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    validate_document(document)
    if arguments.source_root is not None:
        validate_sources(document, arguments.source_root)
    if arguments.self_test:
        self_test(document)
    print("assurance-chain baseline validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
