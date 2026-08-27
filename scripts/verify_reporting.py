#!/usr/bin/env python3
"""Grade Quoin's report command over the static reporting corpus."""

from __future__ import annotations

import json
import os
import pathlib
import shlex
import subprocess
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bounds import CorpusError, controls_by_case, discover, load_declaration

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUOIN = os.environ.get("QUOIN", "")
EXPECT_KEYS = {"exit_code", "stdout", "stderr_contains", "byte_identical"}


def run_case(case: dict, failures: list[str]) -> None:
    name = f"{case['id']} ({case['issue_ref']})"
    expectation = yaml.safe_load((ROOT / case["expect"]).read_text()) or {}
    unknown = sorted(set(expectation) - EXPECT_KEYS)
    if unknown:
        failures.append(f"{name}: unhandled expectation keys {unknown}")
        return

    tokens = shlex.split(case["reproduce"])
    if not tokens or tokens[0] != "quoin":
        failures.append(f"{name}: reproduce must invoke `quoin report`")
        return
    tokens[0] = QUOIN
    first = subprocess.run(tokens, cwd=ROOT, capture_output=True, text=True)
    second = subprocess.run(tokens, cwd=ROOT, capture_output=True, text=True)

    wanted_exit = expectation.get("exit_code", 0)
    if first.returncode != wanted_exit:
        failures.append(
            f"{name}: exit expected {wanted_exit}, got {first.returncode}: "
            f"{first.stderr.strip()[:300]}"
        )

    if expectation.get("byte_identical") and (
        first.stdout.encode() != second.stdout.encode()
        or first.stderr.encode() != second.stderr.encode()
    ):
        failures.append(f"{name}: repeated render was not byte-identical")

    if "stdout" in expectation:
        try:
            actual = json.loads(first.stdout)
        except json.JSONDecodeError as error:
            failures.append(f"{name}: stdout is not JSON: {error}")
        else:
            if actual != expectation["stdout"]:
                failures.append(
                    f"{name}: JSON differs\n"
                    f"    expected {json.dumps(expectation['stdout'], sort_keys=True)}\n"
                    f"    got      {json.dumps(actual, sort_keys=True)}"
                )

    for fragment in expectation.get("stderr_contains") or []:
        if fragment not in first.stderr:
            failures.append(f"{name}: stderr lacks {fragment!r}")


def main() -> int:
    if not QUOIN:
        print("verify-reporting: set QUOIN to the Quoin executable", file=sys.stderr)
        return 1
    try:
        cases = [case for case in discover() if case.get("mode") == "reporting"]
    except CorpusError as error:
        print(f"corpus: {error}", file=sys.stderr)
        return 1
    if not cases:
        print("verify-reporting: no reporting cases discovered", file=sys.stderr)
        return 1

    failures: list[str] = []
    contract = (load_declaration().get("reporting_contract") or {})
    required = set(contract.get("required_cases") or [])
    refusal = set(contract.get("refusal_cases") or [])
    failure_cases = {
        case.get("case") or case["id"]
        for case in cases
        if case.get("kind") == "failure"
    }
    missing = sorted(required - failure_cases - {
        case["id"] for case in cases if case.get("kind") == "regression"
    })
    if missing:
        failures.append(f"required reporting cases have no fixture: {missing}")

    controls = controls_by_case(cases)
    for case_id in sorted(refusal):
        subject = next(
            (case for case in cases if case["id"] == case_id), None
        )
        if subject is None:
            continue
        partners = controls.get((subject["id"], subject.get("language")), [])
        if not partners:
            failures.append(
                f"{case_id}: refusal case has no comparable-runs control"
            )
            continue
        for control in partners:
            expected = yaml.safe_load((ROOT / control["expect"]).read_text()) or {}
            comparisons = (expected.get("stdout") or {}).get("comparisons") or []
            if not comparisons or any(
                row.get("status") != "comparable" or row.get("reasons")
                for row in comparisons
            ):
                failures.append(
                    f"{control['id']}: refusal control does not require a "
                    "reason-free comparable delta"
                )

    for case in cases:
        run_case(case, failures)
    print(f"reporting cases run: {len(cases)}/{len(cases)}")
    for failure in failures:
        print("  MISMATCH", failure)
    print(f"reporting mismatches: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
