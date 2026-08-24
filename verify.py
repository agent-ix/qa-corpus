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
import os
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent

# NOT a PATH lookup. `quire` on PATH is whatever somebody installed — measured
# at 0.29.0 on this machine, which pins engine v0.42.0 and predates
# `binding_census` entirely, so half these fixtures grade against a payload that
# cannot carry what they assert. That is agent-ix/quire-rs#265's defect, one
# repository over, and this corpus is the thing that is supposed to catch it.
#
# Pass an explicit binary: `QUIRE=/path/to/quire make verify`.
QUIRE = os.environ.get("QUIRE", "")

# What a run of this corpus rests on. A binary lacking one of these cannot
# produce the payload the fixtures assert, so the run ABORTS naming the token
# rather than grading against a payload with holes in it.
# A leading `KEY=value`, anchored. The first version tested `"=" in token`,
# which ate a QUIRE path containing `=` (ordinary in a worktree or PR
# checkout) and then ran whatever followed — blaming the binary for a
# parse error with a confident, wrong diagnosis.
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

REQUIRED_CAPABILITIES = ("binding_census", "metrics_envelope")


def check_engine() -> str:
    """Refuse a binary that cannot say what it is, or lacks what we assert on."""
    if not QUIRE:
        raise SystemExit(
            "verify: set QUIRE to the binary to test — e.g.\n"
            "  QUIRE=../quire-cli/target/debug/quire make verify\n"
            "Deliberately not a PATH lookup: the installed `quire` is whatever "
            "somebody put there, and grading a corpus with an unidentified "
            "binary is the defect this corpus exists to catch."
        )
    # Probed over a REAL case, with its module. A scope carrying no
    # traceability model errors and emits no payload, which the first version
    # then read as "no provenance block" — accusing a perfectly good binary of
    # predating #68.
    sample = next(iter(sorted(ROOT.glob("cases/*/*/case.yaml"))), None)
    if sample is None:
        raise SystemExit("verify: the corpus has no cases to probe with")
    meta = yaml.safe_load(sample.read_text())
    tokens = meta["reproduce"].replace("quire ", f"{QUIRE} ", 1).split()
    env = dict(os.environ)
    while tokens and ENV_ASSIGNMENT.match(tokens[0]):
        key, _, value = tokens[0].partition("=")
        env[key] = value
        tokens = tokens[1:]
    probe = subprocess.run(tokens, cwd=ROOT, capture_output=True, text=True, env=env)
    try:
        engine = json.loads(probe.stdout).get("engine") or {}
    except json.JSONDecodeError:
        engine = {}
    if not engine:
        raise SystemExit(
            f"verify: {QUIRE} emits no `engine` provenance block, so it predates "
            f"agent-ix/quire-cli#68 and cannot say which engine it links. "
            f"Refusing to grade."
        )
    missing = [t for t in REQUIRED_CAPABILITIES if t not in engine.get("capabilities", [])]
    if missing:
        raise SystemExit(
            f"verify: {QUIRE} lacks required capability token(s): "
            f"{', '.join(missing)}. It reports {engine.get('capabilities')}. "
            f"Aborting rather than grading against a payload with holes in it."
        )
    return f"{engine.get('cli')} (engine {engine.get('engine')})"

# Every key `expect.yaml` may carry. A key here with no handler below is a
# silently-unasserted expectation, so the set is closed and checked.
KNOWN = {
    "backed", "total", "diagnostic_reasons", "absent_diagnostic_reasons",
    "diagnostic_paths", "diagnostic_message_contains", "binding_census",
    "metrics", "no_symbol_rows",
    # `quire validate` findings, for cases whose family is a STRUCTURAL defect
    # rather than a coverage one. `undeclared-type-value` is the first: a cell
    # outside the declared vocabulary is rejected by `validate`, and the
    # coverage payload of such a case is byte-identical to a healthy control —
    # so a corpus that only ran `coverage` asserted nothing about it at all.
    "validate_contains", "validate_absent",
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


def validate_output(meta: dict, name: str, failures: list[str]) -> str:
    """`quire validate` over the case's own spec tree.

    A second command, because a structural defect is not a coverage one. The
    seeded `Telepathy` cell produces a coverage payload byte-identical to the
    healthy control's — the family is only visible to `validate`, so a corpus
    that ran one command asserted nothing about it.
    """
    tokens = meta["reproduce"].replace("quire ", f"{QUIRE} ", 1).split()
    env = dict(os.environ)
    while tokens and ENV_ASSIGNMENT.match(tokens[0]):
        key, _, value = tokens[0].partition("=")
        env[key] = value
        tokens = tokens[1:]
    scope = tokens[tokens.index("--scope") + 1]
    done = subprocess.run(
        [tokens[0], "validate", "--scope", scope, "spec/tests.md"],
        cwd=ROOT, capture_output=True, text=True, env=env,
    )
    return done.stdout + done.stderr


def check(case: pathlib.Path, failures: list[str]) -> bool:
    meta = yaml.safe_load((case / "case.yaml").read_text())
    expect = yaml.safe_load((case / "expect.yaml").read_text()) or {}
    name = meta["id"]

    unknown = set(expect) - KNOWN
    if unknown:
        failures.append(f"{name}: expect.yaml declares unhandled key(s) {sorted(unknown)}")

    # The invocation may carry leading `KEY=value` assignments — the ecosystem
    # declaration is a module PATH, not a single module, so it is selected with
    # IX_FILAMENT_MODULES_PATH rather than `--module` (agent-ix/quire-rs#292).
    tokens = meta["reproduce"].replace("quire ", f"{QUIRE} ", 1).split()
    env = dict(os.environ)
    while tokens and ENV_ASSIGNMENT.match(tokens[0]):
        key, _, value = tokens[0].partition("=")
        env[key] = value
        tokens = tokens[1:]
    done = subprocess.run(tokens, cwd=ROOT, capture_output=True, text=True, env=env)
    if done.returncode != 0 or not done.stdout.strip():
        failures.append(f"{name}: invocation failed: {done.stderr.strip()[:200]}")
        return False
    got = json.loads(done.stdout)

    if expect.get("validate_contains") or expect.get("validate_absent"):
        report = validate_output(meta, name, failures)
        for fragment in expect.get("validate_contains") or []:
            if fragment not in report:
                failures.append(f"{name}: validate output lacks {fragment!r}")
        for fragment in expect.get("validate_absent") or []:
            if fragment in report:
                failures.append(
                    f"{name}: validate output carries {fragment!r} on input that "
                    f"must be clean of it")

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

    for want in expect.get("binding_census") or []:
        # Found BY LANGUAGE, and absent is a failure. The first version zipped
        # positionally, so an engine that stopped emitting `binding_census`
        # yielded zero iterations and not one assertion ran — green here, red
        # under `cargo test`, which finds by language and fails loudly.
        census = next(
            (c for c in got.get("binding_census") or [] if c.get("language") == want["language"]),
            None,
        )
        if census is None:
            failures.append(
                f"{name}: no `{want['language']}` census in {got.get('binding_census')}")
            continue
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
        # By ID, not by count — a count is satisfied by exempting the WRONG
        # row, which is exactly what `corpus_case/mod.rs` warns about and what
        # the first version of this check did. `filter(None)` matches the Rust
        # grader's `filter_map`, so a null-id row does not diverge 0 vs 1.
        #
        # ABSENT and EMPTY are the same claim for this key: the engine omits it
        # when nothing is exempt (FR-050-AC-7 byte-identity), so a strict
        # `null != []` reading would fail every clean corpus.
        actual = sorted(r["row_id"] for r in got.get("no_symbol_rows", []) if r.get("row_id"))
        wanted = sorted(expect["no_symbol_rows"] or [])
        if actual != wanted:
            failures.append(f"{name}: no_symbol_rows expected {wanted}, got {actual}")
    return True


def main() -> int:
    print(f"engine: {check_engine()}")
    failures: list[str] = []
    cases = sorted(ROOT.glob("cases/*/*/case.yaml"))
    ran = 0
    pending, now_passing = [], []

    for path in cases:
        meta = yaml.safe_load(path.read_text())
        mine: list[str] = []
        ran += check(path.parent, mine)
        ticket = meta.get("pending")
        if ticket is None:
            failures.extend(mine)
        elif mine:
            # Expected to fail, and did. This is the state EPIC #264 rule 3
            # wants a fixture to be in BEFORE its fix lands: the defect has a
            # regression the day it is found, and the suite still goes green.
            pending.append((meta["id"], ticket, mine))
        else:
            # Expected to fail and passed: the fix landed and the marker now
            # lies about the engine. Failing here is what stops the corpus
            # filling with stale `pending:` markers nobody revisits.
            now_passing.append((meta["id"], ticket))

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

    # Printed, never hidden. A count of known-failing cases is a measurement of
    # what the engine cannot yet do, and it belongs beside every run.
    for case, ticket, mine in pending:
        print(f"  PENDING {case} ({ticket}) — expected to fail, and did:")
        for detail in mine:
            print(f"      {detail}")
    if pending:
        print(f"pending: {len(pending)} case(s) awaiting a fix")
    for case, ticket in now_passing:
        print(f"  STALE  {case} now PASSES — {ticket} appears to have landed. "
              f"Remove `pending:` from its case.yaml.")

    return 1 if failures or now_passing else 0


if __name__ == "__main__":
    raise SystemExit(main())
