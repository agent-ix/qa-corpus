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
EXPECT_KEYS = {
    "exit_code",
    "stdout",
    "stderr_contains",
    "byte_identical",
    "ratio_consistent",
}


def check_ratio_consistency(
    case: dict, expectation: dict, tokens: list[str], failures: list[str]
) -> None:
    """Check opted-in ratio records against their own counted population."""
    rule = expectation.get("ratio_consistent")
    if rule is None:
        return
    name = f"{case['id']} ({case['issue_ref']})"
    if not isinstance(rule, dict) or not isinstance(rule.get("decimals"), int):
        failures.append(f"{name}: ratio_consistent requires integer `decimals`")
        return
    try:
        repo = tokens[tokens.index("--repo") + 1]
    except (ValueError, IndexError):
        failures.append(f"{name}: ratio_consistent requires a `--repo` input")
        return

    checked = 0
    measurements = ROOT / repo / "spec/evidence/measurements"
    for path in sorted(measurements.glob("*.json")):
        record = json.loads(path.read_text())
        for observation in record.get("observations") or []:
            population = observation.get("population") or {}
            if (
                observation.get("state") != "measured"
                or observation.get("shape") != "ratio"
            ):
                continue
            examined = population.get("examined")
            matched = population.get("matched")
            if (
                not isinstance(examined, (int, float))
                or examined <= 0
                or not isinstance(matched, (int, float))
            ):
                failures.append(
                    f"{name}: {path.name} {observation.get('metric')} has no "
                    "positive examined/matched population"
                )
                continue
            scale = {"fraction": 1, "percent": 100}.get(observation.get("unit"))
            if scale is None:
                failures.append(
                    f"{name}: {path.name} {observation.get('metric')} uses "
                    f"unsupported ratio unit {observation.get('unit')!r}"
                )
                continue
            expected = round(matched / examined * scale, rule["decimals"])
            if observation.get("value") != expected:
                failures.append(
                    f"{name}: {path.name} {observation.get('metric')} value "
                    f"{observation.get('value')} disagrees with "
                    f"{matched}/{examined} = {expected}"
                )
            checked += 1
    if checked == 0:
        failures.append(f"{name}: ratio_consistent checked no ratio observations")


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
    check_ratio_consistency(case, expectation, tokens, failures)
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
    contract = load_declaration().get("reporting_contract") or {}
    required = set(contract.get("required_cases") or [])
    refusal = set(contract.get("refusal_cases") or [])
    failure_cases = {
        case.get("case") or case["id"]
        for case in cases
        if case.get("kind") == "failure"
    }
    missing = sorted(
        required
        - failure_cases
        - {case["id"] for case in cases if case.get("kind") == "regression"}
    )
    if missing:
        failures.append(f"required reporting cases have no fixture: {missing}")

    controls = controls_by_case(cases)
    for case_id in sorted(refusal):
        subject = next((case for case in cases if case["id"] == case_id), None)
        if subject is None:
            continue
        partners = controls.get((subject["id"], subject.get("language")), [])
        if not partners:
            failures.append(f"{case_id}: refusal case has no comparable-runs control")
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
