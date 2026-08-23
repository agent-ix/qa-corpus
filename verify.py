#!/usr/bin/env python3
"""Run every case by its OWN documented invocation and diff against expect.yaml.

Checks EVERY key `expect.yaml` declares. The first version of this script
checked six of nine and reported 10/10 green while
`cases/detection/catch-all-headline` did not reproduce — its `diagnostic_paths`
and `diagnostic_message_contains` still carried pre-port paths. A verifier that
skips a field is a verifier that certifies it.

Usage:  python3 verify.py            # from the corpus root
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent
QUIRE = "quire"

# Every key `expect.yaml` may carry. A key here with no handler below is a
# silently-unasserted expectation, so the set is closed and checked.
KNOWN = {
    "backed", "total", "diagnostic_reasons", "absent_diagnostic_reasons",
    "diagnostic_paths", "diagnostic_message_contains", "binding_census",
    "metrics", "no_symbol_rows",
}


def is_hollow(metric: dict) -> bool:
    """quire-rs `Metric::is_hollow`, restated because `--json` does not carry it.

    A ratio measured over a non-empty population that matched nothing is
    hollow — the shape that reports a confident 0% over a corpus the binder
    could not read. Counts are never hollow: for a count, `matched` and the
    value are the same fact.
    """
    return (metric.get("shape") == "ratio"
            and (metric.get("population") or 0) > 0
            and (metric.get("examined") or 0) > 0
            and (metric.get("matched") or 0) == 0)


def check(case: pathlib.Path, failures: list[str]) -> bool:
    meta = yaml.safe_load((case / "case.yaml").read_text())
    expect = yaml.safe_load((case / "expect.yaml").read_text()) or {}
    name = meta["id"]

    unknown = set(expect) - KNOWN
    if unknown:
        failures.append(f"{name}: expect.yaml declares unhandled key(s) {sorted(unknown)}")

    argv = meta["reproduce"].replace("quire ", f"{QUIRE} ", 1).split()
    done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    if done.returncode != 0 or not done.stdout.strip():
        failures.append(f"{name}: invocation failed: {done.stderr.strip()[:200]}")
        return False
    got = json.loads(done.stdout)

    for key in ("backed", "total"):
        if key in expect and expect[key] != got["totals"][key]:
            failures.append(f"{name}: {key} expected {expect[key]}, got {got['totals'][key]}")

    diagnostics = got.get("diagnostics", [])
    have = {d["reason"] for d in diagnostics}
    for reason in expect.get("diagnostic_reasons") or []:
        if reason not in have:
            failures.append(f"{name}: `{reason}` did not fire; got {sorted(have)}")
    for reason in expect.get("absent_diagnostic_reasons") or []:
        if reason in have:
            failures.append(f"{name}: `{reason}` fired on input that must stay silent")

    # L2: the finding names the right place.
    for reason, want in (expect.get("diagnostic_paths") or {}).items():
        actual = next((d.get("path") for d in diagnostics if d["reason"] == reason), None)
        if actual != want:
            failures.append(f"{name}: {reason} path expected {want!r}, got {actual!r}")

    # L3: the message names the thing to change.
    for reason, fragment in (expect.get("diagnostic_message_contains") or {}).items():
        message = next((d["message"] for d in diagnostics if d["reason"] == reason), None)
        if message is None or fragment not in message:
            failures.append(f"{name}: {reason} message lacks {fragment!r}; got {message!r}")

    for want, census in zip(expect.get("binding_census") or [], got.get("binding_census") or []):
        for key in ("language", "candidates", "bound"):
            if key in want and want[key] != census.get(key):
                failures.append(
                    f"{name}: binding_census.{key} expected {want[key]}, got {census.get(key)}")
        if "unbound_example" in want:
            example = census.get("unbound_example")
            actual = f"{example['path']}:{example['line']}" if example else None
            if want["unbound_example"] != actual:
                failures.append(
                    f"{name}: unbound_example expected {want['unbound_example']}, got {actual}")

    for want in expect.get("metrics") or []:
        metric = next((m for m in got.get("metrics", []) if m["name"] == want["name"]), None)
        if metric is None:
            failures.append(f"{name}: metric `{want['name']}` absent")
            continue
        for key in ("state", "value", "population", "examined", "matched"):
            if key in want and want[key] != metric.get(key):
                failures.append(
                    f"{name}: {want['name']}.{key} expected {want[key]}, got {metric.get(key)}")
        if "hollow" in want and want["hollow"] != is_hollow(metric):
            failures.append(
                f"{name}: {want['name']}.hollow expected {want['hollow']}, got {is_hollow(metric)}")

    if "no_symbol_rows" in expect:
        # ABSENT and EMPTY are the same claim for this key: the engine omits it
        # when nothing is exempt (FR-050-AC-7 byte-identity), so a strict
        # `null != []` reading would fail every clean corpus.
        actual = got.get("no_symbol_rows", [])
        if len(actual) != len(expect["no_symbol_rows"] or []):
            failures.append(
                f"{name}: no_symbol_rows expected {len(expect['no_symbol_rows'] or [])}, "
                f"got {len(actual)}")
    return True


def main() -> int:
    failures: list[str] = []
    cases = sorted(ROOT.glob("cases/*/*/case.yaml"))
    ran = sum(check(p.parent, failures) for p in cases)

    # Structural conformance to FR-065, over the corpus as a whole.
    ids = {yaml.safe_load(p.read_text())["id"] for p in cases}
    for p in cases:
        meta = yaml.safe_load(p.read_text())
        if meta["kind"] == "control" and meta.get("control_for") not in ids:
            failures.append(
                f"{meta['id']}: control_for names {meta.get('control_for')!r}, which is no case")

    print(f"cases run: {ran}/{len(cases)}")
    for failure in failures:
        print("  MISMATCH", failure)
    print(f"mismatches: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
