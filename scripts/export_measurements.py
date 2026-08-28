#!/usr/bin/env python3
"""Export the corpus-owned measurements as one Quoin collection.

Values come from the derived bounds report and the two runner-produced recall
baselines. This command does not accept observation values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNERS = ("quire-rs", "quoin")
CONFIG_FILES = (
    "config/metrics.json",
    "assurance/MP-201-gap-count.md",
    "assurance/MP-202-detection-recall.md",
)


class ExportError(RuntimeError):
    """The producer inputs cannot support a governed collection."""


def digest_bytes(parts: list[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return f"sha256:{digest.hexdigest()}"


def git_revision(root: pathlib.Path) -> str:
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0 or not done.stdout.strip():
        raise ExportError("the corpus source revision is unavailable")
    return done.stdout.strip()


def bounds_report(root: pathlib.Path) -> dict[str, Any]:
    done = subprocess.run(
        [sys.executable, "bounds.py", "--json", "--require-complete"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise ExportError(done.stderr.strip() or "bounds derivation failed")
    try:
        value = json.loads(done.stdout)
    except json.JSONDecodeError as error:
        raise ExportError(f"bounds output is not JSON: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("bounds"), dict):
        raise ExportError("bounds output has no bounds summary")
    return value


def baselines(root: pathlib.Path) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for runner in RUNNERS:
        path = root / "baselines" / f"{runner}.json"
        try:
            value = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise ExportError(f"{path}: unreadable runner baseline: {error}") from error
        if value.get("runner") != runner:
            raise ExportError(f"{path}: runner must be {runner!r}")
        if value.get("definition_version") != "detection-recall-v1":
            raise ExportError(f"{path}: unexpected detection-recall definition")
        if not isinstance(value.get("rows"), list) or not value["rows"]:
            raise ExportError(f"{path}: recall rows are empty")
        values[runner] = value
    return values


def detection_observations(values: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for runner in RUNNERS:
        for row in values[runner]["rows"]:
            reached = row.get("reached")
            population = row.get("population")
            if not isinstance(reached, int) or not isinstance(population, int):
                raise ExportError(f"{runner}: recall row lacks integer counts")
            if population < 0 or reached < 0 or reached > population:
                raise ExportError(
                    f"{runner}: invalid recall population {reached}/{population}"
                )
            dimensions = {
                key: str(row.get(key, ""))
                for key in ("runner", "mode", "language", "level")
            }
            dimensions["runner"] = runner
            exclusions = row.get("exclusions", [])
            if not isinstance(exclusions, list):
                raise ExportError(f"{runner}: recall exclusions are not a list")
            if population == 0 and (reached != 0 or not exclusions):
                raise ExportError(
                    f"{runner}: zero recall population must retain exclusions and zero reached"
                )
            observations.append(
                {
                    "metric": "detection.recall",
                    "planId": "MP-202",
                    "definitionVersion": "detection-recall-v1",
                    "state": "not_computed" if population == 0 else "measured",
                    "value": None if population == 0 else round(reached / population, 6),
                    "unit": "fraction of seeded failure cases",
                    "shape": "ratio",
                    "population": {
                        "examined": population,
                        "matched": reached,
                        "complete": True,
                        "identity": {
                            **dimensions,
                            "misses": row.get("misses", []),
                            "exclusions": exclusions,
                        },
                    },
                    "dimensions": dimensions,
                }
            )
    return observations


def build_collection(
    root: pathlib.Path,
    *,
    timestamp: str | None = None,
    source_revision: str | None = None,
) -> dict[str, Any]:
    bounds = bounds_report(root)
    values = baselines(root)
    summary = bounds["bounds"]
    gap_count = summary.get("gap_count")
    if not isinstance(gap_count, int):
        raise ExportError("derived bounds gap_count is not an integer")
    for runner, value in values.items():
        if value.get("gap_count") != gap_count:
            raise ExportError(
                f"{runner}: baseline gap_count {value.get('gap_count')} "
                f"disagrees with derived {gap_count}"
            )

    raw_evidence = {"bounds": bounds, "runnerBaselines": values}
    evidence_digest = digest_bytes(
        [json.dumps(raw_evidence, sort_keys=True).encode("utf-8")]
    )
    timestamp = timestamp or datetime.now(timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")
    compact_time = timestamp.replace("-", "").replace(":", "").replace(".", "")
    compact_time = compact_time.replace("T", "").replace("Z", "")
    observations = [
        {
            "metric": "bounds.gap_count",
            "planId": "MP-201",
            "definitionVersion": "bounds.gap-count-v1",
            "state": "measured",
            "value": gap_count,
            "unit": "mode-language cell",
            "shape": "count",
            "population": {
                "examined": summary.get("declared_cells"),
                "matched": gap_count,
                "complete": True,
                "identity": summary.get("matrix"),
            },
        },
        *detection_observations(values),
    ]
    config_digest = digest_bytes(
        [(root / relative).read_bytes() for relative in CONFIG_FILES]
    )
    corpus_revisions = sorted(
        str(value.get("corpus_revision", "")) for value in values.values()
    )
    return {
        "schemaVersion": 1,
        "collectionId": f"qa-corpus-{compact_time}-{evidence_digest[7:19]}",
        "subject": "controlled QA corpus",
        "scope": {
            "fixtures": len(bounds.get("cases", [])),
            "declaredCells": summary.get("declared_cells"),
            "runners": list(RUNNERS),
        },
        "toolIdentity": "qa-corpus measurement exporter",
        "toolVersion": "qa-corpus-measurement-v1",
        "configDigest": config_digest,
        "timestamp": timestamp,
        "sourceRevision": source_revision or git_revision(root),
        "corpusRevision": digest_bytes(
            [revision.encode("utf-8") for revision in corpus_revisions]
        )[7:],
        "environment": {
            "boundsProducer": "bounds.py --json --require-complete",
            "recallProducers": ",".join(RUNNERS),
        },
        "observations": observations,
        "rawEvidence": raw_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="write collection JSON here instead of stdout",
    )
    args = parser.parse_args()
    try:
        collection = build_collection(ROOT)
    except ExportError as error:
        print(f"measurement export: {error}", file=sys.stderr)
        return 1
    rendered = json.dumps(collection, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
