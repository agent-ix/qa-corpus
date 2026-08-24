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

from bounds import CorpusError, discover

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
    # Through `discover()`, not a raw glob. The glob took the first sorted
    # `case.yaml` and read `reproduce` off it — a language SET's shared
    # declaration has none, so the first set sorting before a single-language
    # case would have killed this with a bare `KeyError` before a case ran.
    sample = next(iter(discover()), None)
    if sample is None:
        raise SystemExit("verify: the corpus has no cases to probe with")
    meta = sample
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
    "metrics", "no_symbol_rows", "unbacked_rows", "groups",
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


def check(meta: dict, failures: list[str], ahead: list[str]) -> bool:
    """Run one DISCOVERED case and grade BOTH its contracts.

    `expect.yaml` is the LIVE contract and goes to `failures`: it must hold
    today whether or not the case is pending. `expect-pending.yaml` is the
    FORWARD contract and goes to `ahead`: it must NOT hold yet.

    They were one block, and `pending:` excused the whole of it — so the rule
    became "a pending fixture asserts only what is pending" and every fact that
    was true today went unasserted. `unbacked_rows` was one of them, and it is
    the only field distinguishing the two minting fixtures from each other
    (reviewed, agent-ix/quire-rs#297).
    """
    case = pathlib.Path(meta["dir"])
    name = meta["id"]

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

    live_path = pathlib.Path(meta["expect"])
    forward_path = case / "expect-pending.yaml"
    grade(yaml.safe_load(live_path.read_text()) or {}, got, meta, name, failures)

    # The pairing itself is the LOADER's check (`bounds.check_expectations`,
    # FR-065-AC-26) and reaching here means it held. Asserted, not assumed: an
    # earlier version handled it inline and left `ahead` empty in the
    # missing-file branch, so main() ALSO reported the ticket as landed — one
    # corpus state, two contradictory messages, and following the second one
    # landed you in the opposite pairing error.
    assert forward_path.is_file() == bool(meta.get("pending")), name
    if forward_path.is_file():
        grade(yaml.safe_load(forward_path.read_text()) or {}, got, meta, name, ahead)
    return True


def grade(expect: dict, got: dict, meta: dict, name: str, failures: list[str]) -> None:
    """Assert ONE expectation block against a payload."""
    case = pathlib.Path(meta["dir"])

    unknown = set(expect) - KNOWN
    if unknown:
        failures.append(f"{name}: declares unhandled expectation key(s) {sorted(unknown)}")

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

    # L3: the message names the things to change. A LIST, because L3 for a
    # mismatch is two facts — found and declared — and one substring is
    # satisfied by naming either.
    for reason, fragments in (expect.get("diagnostic_message_contains") or {}).items():
        # A SCALAR iterates its characters and asserts each one, which every
        # message satisfies. Measured: the old string form left this reader at
        # `0 mismatches` on an assertion Rust rejects outright at parse — one
        # corpus, one file, one reader green and one dead. Rejected explicitly
        # rather than coerced, so the two readers take the same input.
        if isinstance(fragments, str):
            failures.append(
                f"{name}: diagnostic_message_contains.{reason} is a string; it "
                f"takes a LIST of substrings (FR-065-AC-29)")
            continue
        message = next((d["message"] for d in diagnostics if d["reason"] == reason), None)
        for fragment in fragments:
            if message is None or fragment not in message:
                failures.append(f"{name}: {reason} message lacks {fragment!r}; got {message!r}")

    # L2. EXACT, both directions, and the field that tells two minting defects
    # apart. A wrong section name strands the whole table — nothing mints, so
    # this is empty. A wrong id column still reads the table and mints a row
    # with a NULL identity. Every other key of those two payloads is
    # byte-identical; until this was asserted the corpus could not distinguish
    # them (reviewed, agent-ix/quire-rs#297). An empty list is an assertion.
    if (want := expect.get("unbacked_rows")) is not None:
        rows = [
            {"document": r.get("document"), "row_id": r.get("row_id"),
             "target_ids": r.get("target_ids")}
            for r in (got.get("unbacked_rows") or [])
        ]
        if rows != want:
            failures.append(f"{name}: unbacked_rows expected {want}, got {rows}")

    # L1. What MINTED, per document per target kind. A control's real job is
    # proving the row it is about mints at all; `total` alone is satisfied by
    # any two backed ids from anywhere.
    if (want := expect.get("groups")) is not None:
        groups = [
            {"document": g.get("document"), "target": g.get("target"),
             "backed": g.get("backed"), "total": g.get("total")}
            for g in (got.get("groups") or [])
        ]
        if groups != want:
            failures.append(f"{name}: groups expected {want}, got {groups}")

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


def main() -> int:
    print(f"engine: {check_engine()}")
    failures: list[str] = []
    # ONE discovery, shared with `bounds.py`. This globbed `cases/*/*/case.yaml`
    # and so could not see a language SET — it found the case-level `case.yaml`,
    # looked for an `expect.yaml` beside it, and died. Two readers of one corpus
    # disagreeing about what a case IS is the drift FR-065 exists to prevent.
    cases = discover()
    ran = 0
    pending, now_passing = [], []

    for case in cases:
        meta = case
        mine: list[str] = []
        forward: list[str] = []
        ran += check(case, mine, forward)
        # The LIVE contract is a failure for every case. Pending never excuses
        # it — that excuse is what left the live facts unasserted.
        failures.extend(mine)
        ticket = meta.get("pending")
        if ticket is None:
            continue
        if forward:
            pending.append((meta["id"], ticket, forward))
        else:
            now_passing.append((meta["id"], ticket))

    # RESTORED. The shared-discovery refactor deleted this loop and nothing
    # replaced it, so the Python runner enforced zero corpus-level conformance:
    # deleting the flagship failure case left `26/26, 0 mismatches, rc 0` with
    # the PENDING lines simply gone. The commit that dropped it claimed to be
    # preventing the two readers from disagreeing.
    #
    # FAILURE cases only: including controls puts each control's own `case` in
    # the set, so `control_for` resolves against itself (FR-065-AC-13).
    partners = set()
    for c in cases:
        if c.get("kind") != "failure":
            continue
        partners.add((c["id"], c.get("language")))
        if c.get("case"):
            partners.add((c["case"], c.get("language")))
    for c in cases:
        if c.get("kind") != "control":
            continue
        # A LIST, always. One control can legitimately serve several failure
        # cases — the healthy repair of two single-cell defects in one document
        # is the same document — and a string form alongside a list form would
        # be two spellings of one claim.
        declared = c.get("control_for")
        if not declared:
            failures.append(f"{c['id']}: a control declares no `control_for`")
        elif not isinstance(declared, list):
            failures.append(
                f"{c['id']}: control_for is {declared!r}; it takes a LIST of "
                f"failure-case names")
        else:
            for partner in declared:
                if (partner, c.get("language")) not in partners:
                    failures.append(
                        f"{c['id']}: control_for names {partner!r}, which is no "
                        f"failure case in {c.get('language')}")
        if c.get("findable"):
            failures.append(f"{c['id']}: a control cannot be findable")

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


def cli() -> int:
    """`main`, with the loader's conformance errors reported as failures.

    Uncaught they printed a traceback, which reads as this script being broken
    rather than as the corpus being invalid — and `check_engine()` calls
    `discover()` too, so the guard belongs at the entry point rather than at
    any one call site.
    """
    try:
        return main()
    except CorpusError as error:
        print(f"corpus: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
