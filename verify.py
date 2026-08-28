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

from bounds import (KNOWN_EXPECT_KEYS, CorpusError, controls_by_case, discover,
                    load_declaration)

ROOT = pathlib.Path(__file__).resolve().parent

# NOT a PATH lookup. `quire` on PATH is whatever somebody installed — measured
# at 0.29.0 on this machine, which pins engine v0.42.0 and predates
# `binding_census` entirely, so half these fixtures grade against a payload that
# cannot carry what they assert. That is agent-ix/quire-rs#265's defect, one
# repository over, and this corpus is the thing that is supposed to catch it.
#
# Pass an explicit binary: `QUIRE=/path/to/quire make verify`.
QUIRE = os.environ.get("QUIRE", "")
QUOIN = os.environ.get("QUOIN", "")

# What a run of this corpus rests on. A binary lacking one of these cannot
# produce the payload the fixtures assert, so the run ABORTS naming the token
# rather than grading against a payload with holes in it.
# A leading `KEY=value`, anchored. The first version tested `"=" in token`,
# which ate a QUIRE path containing `=` (ordinary in a worktree or PR
# checkout) and then ran whatever followed — blaming the binary for a
# parse error with a confident, wrong diagnosis.
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

REQUIRED_CAPABILITIES = (
    "binding_census",
    "binding_census.tagged",
    "metrics_envelope",
)


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
    sample = next(
        (case for case in discover() if case.get("mode") != "reporting"), None
    )
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

# Every key `expect.yaml` may carry, READ FROM THE LOADER rather than restated.
#
# This was a second hand-written copy of `bounds.KNOWN_EXPECT_KEYS`, and the two
# drifted the moment a key was added to one: `suspicions` landed in the loader
# and this reader rejected it as unhandled. A rule stated twice is a rule that
# can disagree with itself, which is the defect agent-ix/quire-rs#349 records
# one list over.
KNOWN = KNOWN_EXPECT_KEYS


def inspect_external(meta: dict, expected: list[dict], name: str,
                     failures: list[str]) -> list[dict]:
    """Run the Quoin producer(s) named by an external witness block."""
    if not QUOIN:
        failures.append(
            f"{name}: declares external_observations but QUOIN is unset; "
            "refusing to grade an external finding as absent")
        return []
    repo = str(ROOT / meta["dir"] / "input")
    kinds = {item.get("kind") for item in expected}
    observations = []

    def produce(args: list[str], producer: str) -> dict:
        done = subprocess.run(
            [QUOIN, *args], cwd=ROOT, capture_output=True, text=True,
            env={**os.environ, "CI": "1"})
        if done.returncode != 0:
            failures.append(
                f"{name}: {producer} failed: {done.stderr.strip()[:300]}")
            return {}
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            failures.append(
                f"{name}: {producer} emitted no JSON: {done.stdout[:200]!r}")
            return {}

    # Run every registered producer, including for an expected empty list. An
    # empty expectation means "looked and found none", not "selected no tool".
    payload = produce(
        ["evidence", "inspect-mocks", "--repo", repo,
         "--suite", "SUITE-CORPUS", "--commit", "0" * 40,
         "--dry-run", "--json"], "mock inspection")
    observations.extend({
        "kind": "mock-injection-observed",
        "path": item.get("path"),
        "line": item.get("line"),
        "symbol": item.get("symbol"),
        "injects": item.get("injects") or [],
    } for item in payload.get("injections", []))

    payload = produce(["validate", "--repo", repo, "--json"],
                      "gate validation")
    observations.extend({
        "kind": item.get("kind"),
        "obligation": item.get("obligation"),
        "path": item.get("path"),
        "line": item.get("line"),
    } for item in payload.get("findings", [])
      if item.get("kind") == "gate-that-gates-nothing")

    known = {"mock-injection-observed", "gate-that-gates-nothing"}
    unknown = sorted(str(kind) for kind in kinds - known)
    if unknown:
        failures.append(f"{name}: no external producer owns {unknown}")
    return sorted(observations, key=lambda item: (
        item.get("kind") or "", item.get("path") or "", item.get("line") or 0))


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
    """`quire validate` over the spec tree `meta` names.

    A second command, because a structural defect is not a coverage one. The
    seeded `Telepathy` cell produces a coverage payload byte-identical to a
    HEALTHY TREE's — `wrong-type-cell` has no control, so "the healthy
    control's", which this sentence said until CR-132, named nothing. The
    family is only visible to `validate`, so a corpus that ran one command
    asserted nothing about it.

    WHOSE tree is a parameter, not "the case being graded". `quire validate`
    reads a spec TREE and cannot be recomputed from a coverage payload, so when
    the differential grades a case's block against its CONTROL, these keys have
    to be re-run over the control's tree or they contribute no discrimination at
    all (FR-065-AC-42, and `ValidateSource` in the Rust harness says the same).

    RETRACTION (CR-132), stated rather than quietly edited. This docstring used
    to finish "`wrong-type-cell`'s entire claim is structural, and recomputing
    it from its own tree would make it read as blind" — a claim about a fixture
    that is in the differential. It is not in the differential. **[RAN]** at
    `qa-corpus 2bc486d`: exactly two of the 77 fixtures declare a `validate_*`
    key — `wrong-type-cell`, a `failure` listed under
    `known_gaps.uncontrolled_failure_cases`, which no control names and which
    both readers therefore skip, and `clean-control`, a `control`, which the
    differential does not iterate (it iterates `kind == "failure"`). **Zero of
    the 35 graded pairs carry a `validate_*` key**, in either reader, and
    `git log -S 'wrong-type-cell' -- cases/` returns one commit — the fixture's
    own introduction — so no `control_for` has ever named it.

    THE RULE STAYS, and its reach over this corpus is 0 pairs of 35. It is
    correct and it has no current subject: the moment `#286` gives
    `wrong-type-cell` a control, validating its own tree is what would reject
    it as blind. FR-065's requirement text is the hedged form — "would be
    rejected as blind **the moment it gained a control**" — and this comment now
    matches it instead of contradicting it. `parity_selftest.py` case 4
    manufactures a `validate_absent` precisely because no fixture supplies one.
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


def find_diagnostic(diagnostics: list, key: str):
    """The diagnostic a key names, honouring the DECLARATION when one is given.

    Every diagnostic carries the declaration that raised it, and neither reader
    read it — both took the first entry with a matching `reason`. Two
    declarations can raise the same reason on one payload, and then the wrong
    finding is graded: measured, declaring a `constraint` target made
    `constraint`'s `section-matches-nothing` displace `test-case`'s in six
    fixtures, including the #270 pair, and the diagnosis was that the token was
    "not scoped to its declaration" — an engine defect that does not exist.
    The engine had always published `declaration`; this reader ignored it.

    A key is either `reason` (any declaration — what every fixture writes
    today) or `declaration/reason` (that declaration only). Scoping is opt-in
    so no existing assertion changes meaning, and picking it up RAISES an
    assertion rather than lowering one.
    """
    declaration, _, reason = key.rpartition("/")
    for d in diagnostics:
        if d["reason"] != reason:
            continue
        if declaration and d.get("declaration") != declaration:
            continue
        return d
    return None


def finding_text(finding: dict) -> str:
    """All producer-owned text a reader sees for L3 guidance.

    Human messages remain part of the contract, but action guidance now has
    typed fields so consumers need not parse prose. Old payloads still grade
    on `message`; current payloads may satisfy a controlled fragment through
    their subject, change target, remedy, or safe diagnostic step.
    """
    fields = (
        "message", "evidence", "subject", "change_target", "changeTarget",
        "remedy", "next_diagnostic_step", "nextDiagnosticStep",
    )
    return " ".join(
        value.strip()
        for field in fields
        if isinstance((value := finding.get(field)), str) and value.strip()
    )


def check(meta: dict, failures: list[str], ahead: list[str], payloads: dict | None = None) -> bool:
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
    # The filing rides along with the id, so a red line says what to go and
    # read. `issue_ref` is required of every case and was, until #336, declared
    # and never once consumed by this reader — a required field nothing uses is
    # a required field nobody notices the absence of. The Rust harness has
    # printed it in `Outcome::report` since the ladder landed.
    name = f"{meta['id']} ({meta['issue_ref']})"

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
    live = yaml.safe_load(live_path.read_text()) or {}
    if "external_observations" in live:
        got["external_observations"] = inspect_external(
            meta, live.get("external_observations") or [], name, failures)
    # Kept for the differential, which needs each CONTROL's payload and must not
    # re-run 34 of them to get it. One run per case, exactly as before.
    if payloads is not None:
        payloads[(meta["id"], meta.get("language"))] = got

    forward_path = case / "expect-pending.yaml"
    grade(live, got, meta, name, failures)

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


def grade(expect: dict, got: dict, meta: dict, name: str, failures: list[str],
          validate_meta: dict | None = None, report_unknown: bool = True) -> None:
    """Assert ONE expectation block against a payload.

    `validate_meta` is whose spec tree the `validate_*` keys are run over,
    defaulting to `meta`'s. The differential passes the CONTROL's.

    `report_unknown` is off in the differential. There, a mismatch is the
    DESIRED outcome, so an "unhandled key" complaint would satisfy the
    discrimination rule without any assertion having discriminated — a gate
    passing on its own schema error, which is the shape this corpus keeps
    finding. The live pass reports it, once, where it means something.
    """
    case = pathlib.Path(meta["dir"])

    if report_unknown:
        unknown = set(expect) - KNOWN
        if unknown:
            failures.append(f"{name}: declares unhandled expectation key(s) {sorted(unknown)}")

    if expect.get("validate_contains") or expect.get("validate_absent"):
        report = validate_output(validate_meta or meta, name, failures)
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
    have |= {f"{d.get('declaration')}/{d['reason']}" for d in diagnostics}
    for reason in expect.get("diagnostic_reasons") or []:
        if reason not in have:
            failures.append(f"{name}: `{reason}` did not fire; got {sorted(have)}")
    for reason in expect.get("absent_diagnostic_reasons") or []:
        if reason in have:
            failures.append(f"{name}: `{reason}` fired on input that must stay silent")

    # Suspicions, graded on the same ladder as a diagnostic: the kind is L1,
    # the locus L2, the message L3 (agent-ix/quire-rs#358). A fixture pinning
    # only `kind` is making the L1 claim and no more, which is the same choice
    # `diagnostic_reasons` and `diagnostic_paths` already offer.
    suspicions = got.get("suspicions", [])
    kinds = [s.get("kind") for s in suspicions]
    for want in expect.get("suspicions") or []:
        if isinstance(want, str):
            # A bare string would assert the kind and silently drop any locus
            # the author meant to write. Rejected rather than coerced, for the
            # reason `diagnostic_message_contains` rejects a scalar: two readers
            # must take the same input.
            failures.append(
                f"{name}: `suspicions` entries are mappings with a `kind`, not "
                f"bare strings; got {want!r}"
            )
            continue
        found = next((s for s in suspicions if s.get("kind") == want["kind"]), None)
        if found is None:
            failures.append(
                f"{name}: suspicion `{want['kind']}` did not fire; got {kinds}"
            )
            continue
        for field in ("path", "line", "symbol"):
            if field in want and found.get(field) != want[field]:
                failures.append(
                    f"{name}: suspicion `{want['kind']}` {field} expected "
                    f"{want[field]!r}, got {found.get(field)!r}"
                )
        for fragment in want.get("message_contains") or []:
            if fragment not in finding_text(found):
                failures.append(
                    f"{name}: suspicion `{want['kind']}` finding text lacks "
                    f"{fragment!r}"
                )
    for kind in expect.get("absent_suspicions") or []:
        if kind in kinds:
            failures.append(
                f"{name}: suspicion `{kind}` fired on input that must stay silent"
            )

    if "external_observations" in expect:
        wanted = expect.get("external_observations") or []
        actual = got.get("external_observations") or []
        if actual != wanted:
            failures.append(
                f"{name}: external_observations expected {wanted}, got {actual}")

    # L2: the finding names the right place.
    for reason, want in (expect.get("diagnostic_paths") or {}).items():
        found = find_diagnostic(diagnostics, reason)
        actual = found.get("path") if found else None
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
        found = find_diagnostic(diagnostics, reason)
        text = finding_text(found) if found else None
        for fragment in fragments:
            if text is None or fragment not in text:
                failures.append(
                    f"{name}: {reason} finding text lacks {fragment!r}; got {text!r}")

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

    # L2. Symbols that bind a trace id no minted row answers for. This is the
    # field that already makes #272's defect observable: rows spread across
    # headings the declaration cannot reach mint nothing, so the tests that
    # answer for them land here instead — with a path and a line, today.
    if (want := expect.get("untracked_symbols")) is not None:
        untracked = [
            {"symbol": u.get("symbol"), "trace_id": u.get("trace_id"), "path": u.get("path")}
            for u in (got.get("untracked_symbols") or [])
        ]
        if untracked != want:
            failures.append(f"{name}: untracked_symbols expected {want}, got {untracked}")

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
        for key in ("language", "candidates", "tagged", "bound"):
            if key in want and want[key] != census.get(key):
                failures.append(
                    f"{name}: binding_census.{key} expected {want[key]}, got {census.get(key)}")
        if "unbound_example" in want:
            example = census.get("unbound_example")
            actual = f"{example['path']}:{example['line']}" if example else None
            if want["unbound_example"] != actual:
                failures.append(
                    f"{name}: unbound_example expected {want['unbound_example']}, got {actual}")
        if "unmatched_example" in want:
            example = census.get("unmatched_example")
            actual = f"{example['path']}:{example['line']}" if example else None
            if want["unmatched_example"] != actual:
                failures.append(
                    f"{name}: unmatched_example expected {want['unmatched_example']}, got {actual}")

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


def check_witness_channels(declaration: dict) -> dict:
    """`witness_channels`, validated before a single pair is graded.

    FR-065-AC-47 IN THIS READER TOO. AC-47 shipped in the Rust harness alone
    (`tests/corpus_cases.rs`, TC-1028) — which is the exact defect CR-128 was
    written to end, recurring one commit later. Reproduced by the outside review
    of 2026-08-24 at `quire-rs 26af2c8` / `qa-corpus 2bc486d`: change
    `witness_channels.disposition`'s `unbacked_rows` to `unbacked_rowz`, one
    character, and `verify.py` reported `cases run: 77/77`, `differential pairs
    graded: 35`, `mismatches: 0`, **exit 0**, while `cargo test --test
    corpus_cases tc1028` panicked naming the channel. `bounds.py` never reads
    `witness_channels`, `schema_selftest.py` does not cover it and
    `parity_selftest.py` still passed 6/6, so the whole of `make ci` was green
    on a corpus where FR-065-AC-46 had been silently weakened for a mode.

    WHY IT IS SILENT WITHOUT THIS. The restriction below is a dict-key filter:
    a name no `expect.yaml` key matches simply contributes nothing to
    `restricted`. Dropping it makes AC-46 quietly WEAKER for precisely the mode
    that declared the channel — a rule-shaped hole rather than a rule.

    THREE CLAIMS, and each is the Rust harness's claim restated over this
    reader's own vocabulary rather than a second hand-written copy of it:

    * every declared channel is a key `grade` handles (`KNOWN`), which is what
      `CaseExpect::channel_names()` is on the other side;
    * a channel list is a LIST. `set(witness.get(mode, []))` over the scalar
      `minting: total` yields `{'t','o','a','l'}` and fails CLOSED with a
      misleading message about the fixture; Rust rejects the same YAML outright
      at `as_sequence().expect("a list of channel names")`. This file already
      made exactly this correction once, for `diagnostic_message_contains` (see
      the `isinstance(fragments, str)` branch in `grade`);
    * every declared `mode_family` has an entry, and every entry names a
      declared family. Both readers otherwise notice an unwitnessed family only
      when a CONTROLLED failure case of that mode is graded — and a new family
      arrives with no controlled case, which is how every mode in this corpus
      started.

    Raised as a `CorpusError`, not appended to `failures`: a declaration this
    reader cannot grade against is a corpus that does not load, and grading 35
    pairs under a rule with a hole in it is the outcome to avoid.
    """
    witness = declaration.get("witness_channels") or {}
    if not witness:
        # Not a skip. A reader that silently grades nothing when its rules are
        # absent is indistinguishable from one that graded and found nothing.
        raise CorpusError(
            "corpus.yaml declares no `witness_channels`, so FR-065-AC-46 cannot "
            "be graded and AC-42 would silently fall back to the floor")

    problems: list[str] = []
    for mode, channels in sorted(witness.items()):
        if not isinstance(channels, list):
            problems.append(
                f"`witness_channels.{mode}` is {channels!r}; it takes a LIST of "
                f"channel names. A scalar iterates its characters and restricts "
                f"on none of them (FR-065-AC-47)")
            continue
        if not channels:
            problems.append(
                f"`witness_channels.{mode}` is empty, so every block of this mode "
                f"restricts to nothing and FR-065-AC-46 rejects the whole family")
            continue
        unknown = sorted(set(channels) - KNOWN)
        if unknown:
            problems.append(
                f"`witness_channels.{mode}` names {unknown}, which this reader "
                f"cannot restrict on — it would be dropped and FR-065-AC-46 would "
                f"silently weaken for this mode (FR-065-AC-47)")

    families = declaration.get("mode_families") or []
    unwitnessed = sorted(set(families) - set(witness))
    if unwitnessed:
        problems.append(
            f"`mode_families` declares {unwitnessed} with no `witness_channels` "
            f"entry, so FR-065-AC-46 is unenforced for that family until one of "
            f"its failure cases gains a control (FR-065-AC-47)")
    stray = sorted(set(witness) - set(families))
    if stray:
        problems.append(
            f"`witness_channels` declares {stray}, which `mode_families` does not "
            f"— a channel set no case can ever be graded against (FR-065-AC-47)")

    if problems:
        raise CorpusError("; ".join(problems))
    return witness


def differential(cases: list[dict], payloads: dict, failures: list[str]) -> int:
    """FR-065-AC-42 IN THIS READER. Returns the number of pairs graded.

    THE CENTREPIECE CHECK, AND IT EXISTED IN ONE OF THE TWO READERS. The Rust
    harness has graded every failure case's `expect.yaml` against its control's
    payload since TC-1028 landed; this script ran each case once, against its
    own payload, and never cross-graded anything. The loader checks that a
    control is NAMED, which is a predicate on shape — the class of defect AC-42
    exists to close. So the claimed two-reader independence stopped immediately
    before the strongest rule (outside review, `agent-ix/quire-rs#337`).

    WHAT IT ASSERTS. A failure case's live block, graded against the payload of
    a control — healthy input, the same tree, the defect repaired — must produce
    at least one mismatch. A block that cannot tell the two apart is not about
    its defect, whatever its shape: an empty block cannot mismatch, a row count
    true of the corpus is true of the control too, and a fixture whose `input/`
    was swapped for a sibling's stops separating anything.

    It is a FLOOR, not closure, and the floor is low. "Assert one fact that
    differs" is weaker than "assert a fact about the defect". Method: run every
    failure case and every control and compare `totals.total`. Population: the
    whole controlled set, no sample, at corpus `2bc486d` (fixtures
    byte-identical to `801afd5`) with CLI 0.30.2 / engine 0.33.0.

        per CASE  (34 controlled failure cases):  20 share it, 14 differ
        per PAIR  (35 case-control pairs):        21 share it, 14 differ

    Where they share it the incidental scalar is not even available as an
    evasion; for the 14 that differ it is. **THE UNIT WAS WRONG HERE UNTIL
    CR-132**: this docstring published "20 pairs", which is 20 CASES — over
    pairs it is 21. The 14 is right under both units, which is why only the noun
    moved. A mode-specific witness is `agent-ix/quire-rs#301`, not this.

    EVERY control that names the case, not one of them. Two name
    `marker-form-mismatch`, and picking one picks it by iteration order.

    `regression` cases are exempt by construction — this iterates `failure`
    only. A regression case IS the healthy counterpart; there is no defect for a
    control to be the repair of (FR-065-AC-43).

    An uncontrolled failure case is skipped here and caught by the LOADER, which
    requires it to be declared under `known_gaps.uncontrolled_failure_cases`.
    No rule of this kind can reach it, which is why the exemption is a
    declaration rather than a matter of taste.
    """
    declaration = load_declaration()
    behaviour_change = set(declaration.get("behaviour_change_tickets") or [])
    witness = check_witness_channels(declaration)
    pairs = controls_by_case(cases)
    graded = 0

    for case in cases:
        if case.get("kind") != "failure":
            continue
        for control in pairs.get((case["id"], case.get("language")), []):
            healthy = payloads.get((control["id"], control.get("language")))
            if healthy is None:
                failures.append(
                    f"{case['id']}: its control {control['id']} produced no payload, "
                    f"so FR-065-AC-42 could not be graded for this pair")
                continue
            name = f"{case['id']} ({case['issue_ref']})"
            live = yaml.safe_load((ROOT / case["expect"]).read_text()) or {}
            blind: list[str] = []
            grade(live, healthy, case, name, blind,
                  validate_meta=control, report_unknown=False)
            if not blind:
                failures.append(
                    f"{name}: its expect.yaml HOLDS against {control['id']}'s payload, "
                    f"so it does not separate its own input from healthy input "
                    f"(FR-065-AC-42)")
            graded += 1

            # A BEHAVIOUR-CHANGE forward block is held to the OPPOSITE rule, and
            # it is the strongest check available to one. The control is the
            # repaired tree, which is what the engine should produce once the
            # fix lands, so the forward block must HOLD against it. Without this
            # the loader's shape rule ("re-state the live block's graded keys
            # with one different value") is satisfied by `total: 999` —
            # different from today, and wrong after the fix too.
            #
            # A TOKEN forward block is NOT held to it. AC-36 requires it to name
            # a token AC-35 guarantees no engine emits, so it cannot hold
            # against any payload and grading it here restates a theorem.
            #
            # BEFORE THE AC-46 BLOCK, and the ordering is the fix rather than a
            # tidy-up. It used to sit after it, and the AC-46 `continue` taken
            # when a block names no witness channel therefore skipped this rule
            # in THIS reader and not in the Rust one, where the forward block is
            # graded first (`tests/corpus_cases.rs`, TC-1028). Reach today is
            # 1 pair — `tag-on-describe-header` is the only case pending on a
            # `behaviour_change_ticket` — and it names a witness, so the
            # divergence was unreachable. It was still a reader divergence in
            # the file whose whole subject is reader divergence.
            ticket = case.get("pending")
            forward_path = ROOT / case["dir"] / "expect-pending.yaml"
            if ticket in behaviour_change and forward_path.is_file():
                ahead: list[str] = []
                grade(yaml.safe_load(forward_path.read_text()) or {}, healthy,
                      case, name, ahead, validate_meta=control, report_unknown=False)
                if ahead:
                    failures.append(
                        f"{name}: its expect-pending.yaml does NOT hold against "
                        f"{control['id']}'s payload. That control is the repaired "
                        f"tree, which is what the engine should produce once "
                        f"{ticket} lands, so a forward block failing against it "
                        f"describes no reachable state (FR-065-AC-42): "
                        + "; ".join(ahead))

            # THE MODE-SPECIFIC WITNESS (FR-065-AC-46). The block above proves
            # the assertion tells these two payloads apart; this proves it does
            # so THROUGH THE CHANNEL THIS MODE IS ABOUT.
            #
            # Graded by RESTRICTION rather than by inspecting which mismatch
            # fired: drop every key outside the mode's witness set and re-grade.
            # Restriction is what makes the claim exactly "the witness channel
            # itself discriminates" — a mismatch list would only tell us one
            # fired somewhere, which is the weaker thing already asserted.
            #
            # `total` is a witness for `minting` and for nothing else, which is
            # the rule the review asked for: an incidental global row count is
            # not detection of an attachment, parser or join defect.
            # `check_witness_channels` has already established that this is a
            # LIST of names `grade` handles, so the restriction below cannot
            # silently drop one (FR-065-AC-47). Unvalidated, `set()` over the
            # scalar `minting: total` yields `{'t','o','a','l'}` and this reader
            # rejects the whole mode with a message about the fixture.
            channels = set(witness.get(case.get("mode"), []))
            restricted = {k: v for k, v in live.items() if k in channels}
            if not restricted:
                failures.append(
                    f"{name}: its expect.yaml names no `{case.get('mode')}` witness "
                    f"channel {sorted(channels)}, so nothing it asserts constitutes "
                    f"detection of this defect family (FR-065-AC-46)")
                continue
            witnessed: list[str] = []
            grade(restricted, healthy, case, name, witnessed,
                  validate_meta=control, report_unknown=False)
            if not witnessed:
                failures.append(
                    f"{name}: separates itself from {control['id']} only OUTSIDE its "
                    f"`{case.get('mode')}` witness channels {sorted(channels)} — "
                    f"restricted to them its block holds against healthy input, so "
                    f"what it detects is not this defect family (FR-065-AC-46)")

    # Non-vacuous. A resolution bug that paired nothing would otherwise report
    # a clean differential over zero pairs, which is how this check would come
    # to exist and assert nothing — the state it was just written to end.
    if not graded:
        failures.append(
            "no failure case was graded against a control, so the FR-065-AC-42 "
            "differential asserted nothing")
    # A guard for "a control resolved to a case that does not exist" USED TO SIT
    # HERE, and it had reach 0 — it could not fire on any corpus. `pairs` is
    # keyed on `(failure["id"], failure.get("language"))` where `failure` comes
    # out of `controls_by_case`'s resolution through `failure_partners`, whose
    # values are elements of `cases`; `by_key` was keyed identically over all of
    # `cases`. Every key was present by construction. Deleted rather than left
    # as reassurance, because a branch that cannot fire is a gate a reader
    # counts and a corpus does not have (outside review, 2026-08-24).
    #
    # THE CLAIM IS NOT LOST, and it is checked where it has reach:
    # `bounds.check_controls` rejects `control_for` naming a name that is no
    # failure case in that language, at LOAD, before any binary runs — that is
    # FR-065-AC-13/AC-26 and TC-1017. Mutation-verified when this was deleted.
    return graded


def main() -> int:
    print(f"engine: {check_engine()}")
    failures: list[str] = []
    # ONE discovery, shared with `bounds.py`. This globbed `cases/*/*/case.yaml`
    # and so could not see a language SET — it found the case-level `case.yaml`,
    # looked for an `expect.yaml` beside it, and died. Two readers of one corpus
    # disagreeing about what a case IS is the drift FR-065 exists to prevent.
    cases = [case for case in discover() if case.get("mode") != "reporting"]
    ran = 0
    pending, now_passing = [], []
    payloads: dict = {}

    for case in cases:
        meta = case
        mine: list[str] = []
        forward: list[str] = []
        ran += check(case, mine, forward, payloads)
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

    graded = differential(cases, payloads, failures)

    print(f"cases run: {ran}/{len(cases)}")
    print(f"differential pairs graded: {graded}")
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
