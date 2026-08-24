#!/usr/bin/env python3
"""Derive the bounds matrix from the inventory and the filesystem.

`corpus.yaml` declares **intent** — for each case, the languages it should
exist in, and any cell deliberately scoped out with a reason. This computes the
**state**: which of those cells have a fixture, which do not, and the counts.

Nothing is stored. A stored count is a number that can go stale; a derived one
cannot disagree with the tree it describes. It also means adding a fixture
flips its own cell and drops `gap_count` with **no edit to any central file**,
which is what makes a forty-fixture change reviewable (#289).

    python3 bounds.py            # human summary
    python3 bounds.py --json     # the matrix, for a runner

Two case layouts are read, and a directory in neither is an error rather than a
silent omission:

    cases/<mode>/<case>/{case.yaml,input/,expect.yaml}              one language
    cases/<mode>/<case>/case.yaml + <language>/{input/,expect.yaml} a set
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent


class CorpusError(Exception):
    """A corpus that cannot be read as declared."""


def load_declaration() -> dict:
    return yaml.safe_load((ROOT / "corpus.yaml").read_text())


def discover() -> list[dict]:
    """Every fixture on disk, in either layout.

    A `case.yaml` with neither an `input/` beside it nor any `<language>/`
    subdirectory carrying one is **rejected**. Skipping it silently is how a
    half-authored fixture reads as an absent one, and absent is what
    `gap_count` is supposed to mean.
    """
    cases: list[dict] = []
    for case_yaml in sorted((ROOT / "cases").glob("*/*/case.yaml")):
        case_dir = case_yaml.parent
        shared = yaml.safe_load(case_yaml.read_text()) or {}
        rel = case_dir.relative_to(ROOT)

        sub_languages = [d for d in case_dir.iterdir() if (d / "input").is_dir()]
        if (case_dir / "input").is_dir():
            # FR-065: a directory in BOTH layouts is rejected rather than
            # silently read as one of them. Both readers took the `input/`
            # branch and moved on, so a half-migrated case would have had its
            # language variants disappear from the matrix without a word.
            if sub_languages:
                raise CorpusError(
                    f"{rel}: carries both an `input/` and "
                    f"{sorted(d.name for d in sub_languages)} — a case is one "
                    f"layout or the other, and reading it as one silently drops "
                    f"the other.")
            cases.append({
                **shared, "dir": str(rel), "expect": str(rel / "expect.yaml"),
                "_declared": shared,
            })
            continue

        variants = sorted(sub_languages)
        if not variants:
            raise CorpusError(
                f"{rel}: neither an `input/` nor any `<language>/input/`. A "
                f"half-authored fixture read as an absent one would make "
                f"gap_count mean something else."
            )
        for variant in variants:
            language = variant.name
            per_case = yaml.safe_load((variant / "case.yaml").read_text()) if (
                variant / "case.yaml"
            ).is_file() else {}
            # A variant may vary its EXPECTATIONS and its invocation, not what
            # case it is. Overriding `case`/`mode` silently re-points the cell
            # a fixture credits — measured: one line in a variant file moved a
            # covered cell to a different inventory row and `gap_count` did not
            # change. `module`/`kind`/`pending` are the same class of claim.
            # PRESENCE, not disagreement. The first version required the field
            # in BOTH files, so a variant could INJECT one the shared file
            # omitted and nothing fired. Measured: adding `pending:` to one
            # control variant and then breaking that control left
            # `32/32, 0 mismatches, rc 0` and this matrix unmoved — a control
            # that exists to prove a check stays silent on healthy input,
            # converted into an expected failure by one line.
            protected = {"case", "mode", "module", "kind", "pending"}
            declared = sorted(k for k in protected if k in per_case)
            if declared:
                raise CorpusError(
                    f"{rel}/{language}: a variant may not declare {declared} at "
                    f"all — those say WHICH case this is, and the shared "
                    f"`case.yaml` is where that claim lives (FR-065-AC-22).")
            merged = {**shared, **per_case, "language": language}
            # The variant's id must be its OWN. `setdefault` never fired here
            # because the shared `case.yaml` already carries `id`, so all three
            # language variants reported one id — indistinguishable in the
            # pending list, and a duplicate-id check would have called them one
            # case.
            # Derived from the MERGED map and always suffixed, matching the
            # Rust harness exactly. This honoured a variant-declared `id`
            # verbatim while Rust overwrote it, so one fixture had two
            # identities and nothing keyed on `id` — a pending ticket, a
            # baseline row, a result record — could be joined across runners.
            base = merged.get("id", case_dir.name)
            merged["case"] = merged.get("case", base)
            merged["id"] = f"{base}-{language}"
            cases.append({
                **merged,
                "dir": str(variant.relative_to(ROOT)),
                "expect": str(variant.relative_to(ROOT) / "expect.yaml"),
                # The declaration AS WRITTEN. `merged` gains a derived `case`,
                # so a check on whether the author wrote one needs the original.
                "_declared": {**shared, **per_case},
            })
    check_known_gaps(load_declaration())
    check_controls(cases)
    check_expectations(cases)
    return cases


def check_known_gaps(declaration: dict) -> None:
    """Every declared departure names a ticket.

    `pending:` requires a `pending_reason`; a variant `module` requires a
    `relaxation_ticket`. A `known_gaps` entry required neither, so one appended
    line was a total, permanent exemption from a contract clause with nothing
    recording who would undo it.
    """
    for name, entry in (declaration.get("known_gaps") or {}).items():
        reason = (entry or {}).get("reason") or ""
        if not re.search(r"#\d+", reason):
            raise CorpusError(
                f"known_gaps.{name}: its reason names no ticket. An exemption "
                f"from the contract with nothing tracking its removal is a "
                f"departure that becomes permanent by default.")
        if not ((entry or {}).get("cases") or []):
            raise CorpusError(
                f"known_gaps.{name}: declares no cases. An empty exemption is "
                f"a clause nobody removed when the last case was fixed.")


def controlled_cases(cases: list[dict]) -> set:
    """Every failure case, by id+language, that some control names."""
    partners = {}
    for c in cases:
        if c.get("kind") == "failure" and c.get("case"):
            partners.setdefault((c["case"], c.get("language")), c)
    for c in cases:
        if c.get("kind") == "failure":
            partners[(c["id"], c.get("language"))] = c
    return {
        (partners[(p, c.get("language"))]["id"], c.get("language"))
        for c in cases if c.get("kind") == "control"
        and isinstance(c.get("control_for"), list)
        for p in c["control_for"]
        if (p, c.get("language")) in partners
    }


def check_controls(cases: list[dict]) -> None:
    """Control pairing and `known_gaps`, checked at LOAD.

    These are corpus CONFORMANCE, not payload grading, so they belong to the
    loader — and there they need no engine binary, which is what lets a test
    drive them over a mutated copy. They lived in `verify.py`, where the only
    way to exercise them was to have a working `quire` in hand.
    """
    problems: list[str] = []
    # RESTORED. The shared-discovery refactor deleted this loop and nothing
    # replaced it, so the Python runner enforced zero corpus-level conformance:
    # deleting the flagship failure case left `26/26, 0 mismatches, rc 0` with
    # the PENDING lines simply gone. The commit that dropped it claimed to be
    # preventing the two readers from disagreeing.
    #
    # FAILURE cases only: including controls puts each control's own `case` in
    # the set, so `control_for` resolves against itself (FR-065-AC-13).
    declaration = load_declaration()
    gaps = declaration.get("known_gaps") or {}
    module_gaps = set((gaps.get("control_binds_another_module") or {}).get("cases") or [])
    uncontrolled = set((gaps.get("uncontrolled_failure_cases") or {}).get("cases") or [])

    # Keyed by `id` FIRST, and an alias never displaces one. This was a set
    # before the checks moved here; converting it to a dict to carry each
    # partner's mode and module introduced a silent overwrite, because one
    # case's `case:` alias can equal another case's `id`. Two real collisions
    # existed on this corpus — `catch-all-headline` and `marker-form-mismatch`
    # each name both a bench-legacy fixture and an ecosystem one — and the
    # later-sorted alias won. That misdiagnosed THREE controls as binding the
    # wrong module (they do not; their partners match exactly) and let a case
    # with no control of its own inherit somebody else's.
    partners = {}
    for c in cases:
        if c.get("kind") != "failure":
            continue
        if c.get("case"):
            partners.setdefault((c["case"], c.get("language")), c)
    for c in cases:
        if c.get("kind") != "failure":
            continue
        partners[(c["id"], c.get("language"))] = c
    for c in cases:
        if c.get("kind") != "control":
            continue
        # A LIST, always. One control can legitimately serve several failure
        # cases — the healthy repair of two single-cell defects in one document
        # is the same document — and a string form alongside a list form would
        # be two spellings of one claim.
        declared = c.get("control_for")
        if not declared:
            problems.append(f"{c['id']}: a control declares no `control_for`")
        elif not isinstance(declared, list):
            problems.append(
                f"{c['id']}: control_for is {declared!r}; it takes a LIST of "
                f"failure-case names")
        else:
            for partner in declared:
                key = (partner, c.get("language"))
                if key not in partners:
                    problems.append(
                        f"{c['id']}: control_for names {partner!r}, which is no "
                        f"failure case in {c.get('language')}")
                    continue
                # A control is the HEALTHY version of its partner, so it has to
                # be the same kind of thing. Nothing checked this once the field
                # became a list: measured, a `detection` control on the
                # bench-legacy variant could claim a `minting` case on the
                # ecosystem declaration — a different tree entirely — and every
                # gate stayed green.
                other = partners[key]
                for field in ("mode", "module"):
                    if c.get(field) == other.get(field):
                        continue
                    # Scoped to `module`. The exemption is declared for a
                    # control binding another MODULE; it excused a mode
                    # mismatch too, so a `detection` control could claim a
                    # `minting` partner and stay green.
                    if field == "module" and c["id"] in module_gaps:
                        continue
                    problems.append(
                            f"{c['id']}: control_for names {partner!r}, whose "
                            f"{field} is {other.get(field)!r} against this "
                            f"control's {c.get(field)!r}. A control is the "
                            f"healthy version of its partner, not any case that "
                            f"happens to resolve.")
        if c.get("findable"):
            problems.append(f"{c['id']}: a control cannot be findable")

    # AC-13's OTHER direction, which nothing enforced: every failure case is
    # named by SOME control. Eleven were not, while the declaration listed
    # three — and that declaration was read by no code at all.
    # Resolved through the id-first `partners` map, and keyed by the partner's
    # ID. Built from raw `control_for` strings, this had the same alias/id
    # collision the map above was just fixed for, in the other direction:
    # deleting `clean-control` — the ONLY control for the ecosystem case
    # `catch-all-properties` — left the loader green, because that case's
    # `case:` alias is also the ID of a bench-legacy fixture that has its own
    # control, so it silently inherited a stranger's.
    controlled = {
        (partners[(partner, c.get("language"))]["id"], c.get("language"))
        for c in cases if c.get("kind") == "control"
        and isinstance(c.get("control_for"), list)
        for partner in c["control_for"]
        if (partner, c.get("language")) in partners
    }
    for c in cases:
        if c.get("kind") != "failure":
            continue
        row = c.get("case") or c["id"]
        if (c["id"], c.get("language")) in controlled:
            continue
        if row in uncontrolled or c["id"] in uncontrolled:
            continue
        problems.append(
            f"{c['id']}: no control names it (FR-065-AC-13). Without one, a check "
            f"firing on every input scores perfect recall. Declare it under "
            f"`known_gaps.uncontrolled_failure_cases` if that is deliberate.")
    # EVERY list under `known_gaps`, not a hand-picked two. The first version
    # named `uncontrolled_failure_cases` and `control_binds_another_module`
    # explicitly, so adding a third list gave it a set of exemptions no staleness
    # check covered — a declaration going stale in exactly the way this check
    # exists to prevent.
    known = {c.get("case") or c["id"] for c in cases} | {c["id"] for c in cases}
    for gap, entry in (declaration.get("known_gaps") or {}).items():
        stale = sorted(set((entry or {}).get("cases") or []) - known)
        if stale:
            problems.append(
                f"known_gaps.{gap} names {stale}, which is no case in the "
                f"corpus — a declared gap that has outlived its fixture")


    if problems:
        raise CorpusError("; ".join(problems))


def check_expectations(cases: list[dict]) -> None:
    """Every expectation block, checked at LOAD.

    FR-065-AC-26 says the corpus LOADER rejects a broken pairing. It did not:
    only the two runners objected, so `bounds.py` — one of the three gates —
    exited 0 and printed an unchanged matrix, still counting six pending, over
    a corpus state the spec calls invalid.

    The reason vocabulary is checked here too. A forward block naming a token
    no ticket introduces sat pending forever with nothing to say so.
    """
    declaration = load_declaration()
    vocabulary = declaration.get("diagnostic_reasons") or {}
    emitted = set(vocabulary.get("emitted") or [])
    forward = dict(vocabulary.get("forward") or {})
    gaps = declaration.get("known_gaps") or {}
    undetected = set((gaps.get("findable_but_undetected") or {}).get("cases") or [])
    controlled = controlled_cases(cases)
    behaviour_change = set(declaration.get("behaviour_change_tickets") or [])

    for case in cases:
        directory = ROOT / case["dir"]
        live_path = ROOT / case["expect"]
        forward_path = directory / "expect-pending.yaml"
        ticket = case.get("pending")
        name = case["id"]

        if ticket and not forward_path.is_file():
            raise CorpusError(
                f"{name}: declares `pending: {ticket}` and ships no "
                f"expect-pending.yaml — the behaviour it waits on is asserted "
                f"nowhere (FR-065-AC-26).")
        if forward_path.is_file() and not ticket:
            raise CorpusError(
                f"{name}: ships expect-pending.yaml and declares no `pending:` "
                f"— a forward claim naming no ticket (FR-065-AC-26).")
        # FR-065 requires this of the LOADER; only the Rust runner checked it.
        if ticket and not (case.get("pending_reason") or "").strip():
            raise CorpusError(
                f"{name}: is pending on {ticket} with no `pending_reason`. A "
                f"marker with no stated reason is one nobody can decide whether "
                f"to remove.")
        # F9: a control serves inventory rows through its partners, not through
        # a `case:` of its own. One control now names TWO partners and could
        # only name one row — measured, pointing it at a row that does not
        # exist left every gate green, because `build()` credits only failure
        # cases and the field is dead for a control.
        if case.get("kind") == "control" and "case" in (case.get("_declared") or {}):
            raise CorpusError(
                f"{name}: a control declares `case:`. A control credits no cell; "
                f"the rows it serves are its `control_for` partners.")

        live = yaml.safe_load(live_path.read_text()) or {}
        # THE LIVE BLOCK TOO. This was enforced on the forward block by both
        # readers and on `expect.yaml` by neither, so emptying any failure
        # case's `expect.yaml` left every gate green with its cell still
        # `covered` — round one's defect exactly, reached by truncating the
        # file instead of by the `pending:` key. `unbacked_rows`, the one field
        # separating the two minting fixtures, is precisely what an empty live
        # block drops.
        if not asserts_something(live):
            raise CorpusError(
                f"{name}: expect.yaml asserts nothing. A case that asserts "
                f"nothing about its own payload still counts its cell covered, "
                f"which is the conflation this corpus exists to end.")
        unknown = set(live) - KNOWN_EXPECT_KEYS
        if unknown:
            raise CorpusError(
                f"{name}: expect.yaml declares unhandled key(s) {sorted(unknown)}.")
        check_reasons(name, live, "expect.yaml", case, emitted, forward)

        if not forward_path.is_file():
            check_findable(name, case, live, {}, undetected, controlled)
            continue

        ahead = yaml.safe_load(forward_path.read_text()) or {}
        # A typo'd key in a forward block was GRADED — reported as the reason
        # the ticket has not landed, forever. `diagnostic_reason:` (singular)
        # produced `PENDING … declares unhandled expectation key(s)`, and the
        # fixture's own schema error was counted as evidence about the engine.
        unknown = set(ahead) - KNOWN_EXPECT_KEYS
        if unknown:
            raise CorpusError(
                f"{name}: expect-pending.yaml declares unhandled key(s) "
                f"{sorted(unknown)}. In a forward block a typo grades as a "
                f"failure, so it reads as `the ticket has not landed` and never "
                f"stops doing so.")
        # An EMPTY forward block grades zero assertions, so it trivially
        # "holds" — and both runners then report that the ticket has landed.
        # Measured with a 0-byte file and with `{}`: the engine untouched, and
        # a reader told to delete the marker, which converts the regression
        # fixture into a green case asserting nothing.
        #
        # Field by field, matching the Rust harness. A truthiness test passed
        # `diagnostic_reasons: []` — non-empty as YAML, zero assertions when
        # graded — so this loader exited 0 and `verify.py` then announced the
        # ticket had landed. Same for `binding_census: []`, `metrics: []`,
        # `diagnostic_paths: {}` and any key with a null value.
        if not asserts_something(ahead):
            raise CorpusError(
                f"{name}: expect-pending.yaml asserts nothing. An empty forward "
                f"block always holds, which every runner reads as `{ticket} has "
                f"landed`.")
        check_reasons(name, ahead, "expect-pending.yaml", case, emitted, forward)

        # THE BLOCK MUST BE ABOUT ITS TICKET. Two rounds of review found the
        # forward half unpoliced, and the second fix constrained only reason
        # TOKENS — so `backed: 99` was still accepted: false today, false
        # forever, and the case stays pending after its ticket ships with no
        # gate saying so. A forward block has to REQUIRE at least one token
        # the named ticket introduces.
        # A BEHAVIOUR-CHANGE ticket adds no diagnostic, so there is no token to
        # name — #272 makes `TraceTarget.section` accept several headings and
        # rows that were invisible start minting. The forward block must
        # instead re-state the same exactly-graded keys its live block does,
        # with at least one different value: the same measurement, after.
        #
        # That is what the token rule was really asking for. `backed: 99` still
        # fails, because the live block asserts `total`, `groups` and
        # `untracked_symbols` and the forward block has to cover the same
        # ground rather than one field of its choosing.
        if ticket in behaviour_change:
            graded = {k for k in EXACTLY_GRADED if live.get(k) is not None}
            missing = sorted(graded - {k for k in EXACTLY_GRADED if ahead.get(k) is not None})
            if missing:
                raise CorpusError(
                    f"{name}: is pending on the behaviour change {ticket} and its "
                    f"expect-pending.yaml is silent on {missing}, which its "
                    f"expect.yaml asserts. A behaviour-change forward block is the "
                    f"SAME measurement after the fix, so it states the same keys.")
            if all(ahead.get(k) == live.get(k) for k in graded):
                raise CorpusError(
                    f"{name}: its expect-pending.yaml asserts exactly what its "
                    f"expect.yaml does, so {ticket} landing would change nothing "
                    f"it can see.")
            check_findable(name, case, live, ahead, undetected, controlled)
            continue

        claimed = set(ahead.get("diagnostic_reasons") or [])
        claimed |= set(ahead.get("diagnostic_paths") or {})
        claimed |= set(ahead.get("diagnostic_message_contains") or {})
        owned = {r for r in claimed if forward.get(r) == ticket}
        if not owned:
            raise CorpusError(
                f"{name}: expect-pending.yaml requires no token that {ticket} "
                f"introduces. A forward block that is merely FALSE stays false "
                f"after the fix lands — it has to be ABOUT the ticket, or "
                f"nothing ever tells you the fixture went stale.")

        check_findable(name, case, live, ahead, undetected, controlled)


def check_findable(
    name: str, case: dict, live: dict, ahead: dict, undetected: set, controlled: set
) -> None:
    """A `findable` case names something that finds it.

    The flag tells a recall-scoring consumer to expect a finding on that input.
    Measured: three `skeptic` fixtures ship BYTE-IDENTICAL live blocks —
    `backed: 1`, `total: 3`, one bound rust symbol — true of any healthy
    three-row corpus, with no diagnostic asserted anywhere. Replacing one's
    entire `input/` tree with another's left every gate green and the cell
    still `covered`, so the fixture was not about its own defect at all.

    Called LAST and from BOTH branches. Sitting inside the pending-only branch,
    it ran for six cases out of twenty-nine and diagnosed a truncated forward
    file as a missing detection claim.
    """
    if case.get("kind") != "failure" or not case.get("findable"):
        return
    # A case with a CONTROL is held to FR-065-AC-42 instead, which is strictly
    # stronger: its assertions must separate its own input from healthy input,
    # whatever form they take. "names a diagnostic" is a proxy for that, and a
    # narrow one — `no-symbol-method-in-the-verification-column` discriminates
    # through `no_symbol_rows` and names no diagnostic at all.
    if (case["id"], case.get("language")) in controlled:
        return
    claims = any(
        block.get(key)
        for block in (live, ahead)
        for key in ("diagnostic_reasons", "validate_contains")
    )
    if claims or (case.get("case") or case["id"]) in undetected:
        return
    raise CorpusError(
        f"{name}: is `findable` and requires no finding, in either block. A "
        f"case claiming its defect is DETECTABLE has to say what detects it, "
        f"or its cell counts as covered for a mode nothing measures. Declare "
        f"it under `known_gaps.findable_but_undetected` if the engine truly "
        f"finds nothing yet.")


def asserts_something(block: dict) -> bool:
    """Whether a block asserts anything at all, field by field.

    A block that grades zero assertions trivially passes, which for a forward
    block means every runner reports its ticket as landed.
    """
    # PRESENCE for the keys graded exactly, non-emptiness for the rest —
    # matching the Rust harness field for field. A blanket "not in (None, [],
    # {})" scored `unbacked_rows: []` as asserting nothing, while FR-065-AC-28
    # says an empty list IS an assertion and `grade()` grades it as one. So a
    # forward block of `unbacked_rows: []` was rejected at load by this reader
    # and accepted-and-graded by the other.
    exact = {"backed", "total", "unbacked_rows", "groups", "no_symbol_rows",
             "untracked_symbols"}
    return any(
        block.get(key) is not None if key in exact else block.get(key) not in (None, [], {})
        for key in KNOWN_EXPECT_KEYS
    )


# Every key an expectation block may carry. Shared with `verify.py`, which
# grades them; declared here because the LOADER now rejects a typo rather than
# grading one.
# The keys graded EXACTLY — presence is an assertion and an empty list is a
# claim, so these are what a behaviour-change forward block must re-state.
EXACTLY_GRADED = ("backed", "total", "unbacked_rows", "groups", "no_symbol_rows",
                  "untracked_symbols")

KNOWN_EXPECT_KEYS = {
    "backed", "total", "diagnostic_reasons", "absent_diagnostic_reasons",
    "diagnostic_paths", "diagnostic_message_contains", "binding_census",
    "metrics", "no_symbol_rows", "unbacked_rows", "groups",
    "untracked_symbols",
    "validate_contains", "validate_absent",
}


def check_reasons(
    name: str, block: dict, where: str, case: dict, emitted: set, forward: dict
) -> None:
    """Every reason token a block names is declared, and declared for THIS case."""
    ticket = case.get("pending")
    present = list(block.get("diagnostic_reasons") or [])
    present += list(block.get("diagnostic_paths") or {})
    present += list(block.get("diagnostic_message_contains") or {})
    absent = list(block.get("absent_diagnostic_reasons") or [])

    for reason in present + absent:
        if reason not in emitted and reason not in forward:
            raise CorpusError(
                f"{name}: {where} names `{reason}`, which `corpus.yaml` declares "
                f"neither emitted nor forward. A token in neither list is a typo "
                f"nothing can ever satisfy.")

    for reason in present:
        if reason not in forward:
            # FR-065: a forward block requires ONLY `forward` tokens. Both
            # readers implemented the weaker ticket-match rule and skipped
            # here, so a forward block could require `catch-all-universal` with
            # an unreachable message fragment — false today, false forever, and
            # exactly the shape a PARTIAL landing of a ticket takes.
            if where == "expect-pending.yaml":
                raise CorpusError(
                    f"{name}: expect-pending.yaml requires `{reason}`, which the "
                    f"engine already emits. A forward block states what the "
                    f"ticket ADDS; an already-emitted token there is satisfied "
                    f"or not for reasons that have nothing to do with it.")
            continue
        if where != "expect-pending.yaml":
            raise CorpusError(
                f"{name}: {where} requires `{reason}`, which no engine emits yet "
                f"({forward[reason]}). A live block must hold TODAY; this belongs "
                f"in expect-pending.yaml.")
        if forward[reason] != ticket:
            raise CorpusError(
                f"{name}: is pending on {ticket} and asserts `{reason}`, which "
                f"{forward[reason]} introduces. A fixture cannot wait on one "
                f"ticket while asserting another's behaviour.")

    for reason in absent:
        if reason not in forward:
            continue
        # A CONTROL asserting the absence of a not-yet-emitted token is vacuous
        # today and load-bearing the day the ticket lands — which is what a
        # control is for. A FAILURE case doing it asserts the absence of the
        # very thing it is waiting for, so its live block is guaranteed to
        # break on the fix instead of passing it.
        if case.get("kind") != "control":
            raise CorpusError(
                f"{name}: {where} asserts `{reason}` is ABSENT, but {forward[reason]} "
                f"adds it and this case is not a control. The day that ticket lands "
                f"this block fails — a live block must survive the fix it waits for.")
        if where != "expect.yaml":
            raise CorpusError(
                f"{name}: a control's forward absence claim belongs in expect.yaml; "
                f"a forward block must FAIL today, and this cannot.")


def build(declaration: dict, cases: list[dict]) -> dict:
    """The matrix, computed. `covered` iff a fixture exists for the cell."""
    # A fixture covers a cell only when it binds the ECOSYSTEM declaration.
    # One binding a relaxation variant exercises no ecosystem mode — a corpus
    # whose manifest heading always matches cannot exhibit the defect that
    # strands 3,514 TC ids — so it is still a GAP, and the reason names the
    # ticket that will move it (FR-065 CON-3, #285).
    covered_by, on_variant = set(), {}
    for c in cases:
        # Only a FAILURE fixture covers a cell. A control asserts that healthy
        # input stays silent; it measures nothing about the mode. The first
        # version credited either, so deleting the only ecosystem failure
        # fixture and keeping its control left `gap_count` unmoved.
        if c.get("kind") != "failure":
            continue
        # The inventory row this fixture claims, by `case:` — falling back to
        # the id only for a fixture whose id IS the inventory name. Both keys
        # were added before, so a control's id leaked into the namespace and
        # could collide with a future row.
        key = (c.get("mode"), c.get("case") or c.get("id"), c.get("language"))
        if c.get("module") == "ecosystem":
            covered_by.add(key)
        else:
            on_variant[key] = (c.get("id"), c.get("module"), c.get("relaxation_ticket"))
    have = covered_by

    # #289 acceptance: a case naming a module with no manifest is REJECTED.
    # The first version emitted a GAP whose reason named a module that was not
    # there, and an exact-string `== "ecosystem"` meant `./ecosystem` silently
    # became a variant while the Rust harness loaded it fine.
    for c in cases:
        module = (c.get("module") or "").strip().strip("./").rstrip("/")
        if not module:
            raise CorpusError(f"{c.get('id')}: declares no `module`")
        base = ROOT / "modules" / module
        # A module id names either a single module (`manifest.yaml` directly) or
        # a module PATH — a directory of module directories. `ecosystem` is the
        # second: the real declaration is spec-artifacts-process AND
        # spec-artifacts-iso, and vendoring only the first meant criteria
        # classification silently produced nothing (agent-ix/quire-rs#292).
        if not (base / "manifest.yaml").is_file() and not any(
            d.joinpath("manifest.yaml").is_file() for d in base.glob("*") if d.is_dir()
        ):
            raise CorpusError(
                f"{c.get('id')}: module `{c.get('module')}` has no manifest under "
                f"modules/{module}/")
        c["module"] = module
        # FR-065-CON-3 / AC-15: a variant binding names its relaxation ticket.
        if module != "ecosystem" and not c.get("relaxation_ticket"):
            raise CorpusError(
                f"{c.get('id')}: binds variant `{module}` and names no "
                f"`relaxation_ticket`. A corpus whose manifest always matches "
                f"cannot exhibit a declaration defect, so an unticketed "
                f"relaxation is the state CON-3 forbids.")

    # A cell covered by a PENDING fixture is covered — a case exists and
    # exercises the mode — but the engine demonstrably fails it. Reported
    # separately so `covered` cannot be read as `working`, which is the exact
    # conflation this corpus exists to end.
    pending_cases = {
        (c.get("mode"), c.get("case") or c.get("id"), c.get("language"))
        for c in cases
        if c.get("pending")
    }
    matrix, counts = [], {"covered": 0, "GAP": 0, "out-of-scope": 0}
    covered_pending = 0
    for row in declaration["inventory"]:
        scoped_out = row.get("out_of_scope", {})
        # FR-065-AC-7: an out-of-scope cell carries a non-empty reason.
        for lang, reason in scoped_out.items():
            if not (reason or "").strip():
                raise CorpusError(
                    f"{row['case']}/{lang}: out-of-scope with no reason. "
                    f"Scoping a cell out is a claim, and an unexplained one is "
                    f"indistinguishable from forgetting it.")
            if lang not in row["languages"]:
                raise CorpusError(
                    f"{row['case']}: out-of-scope names `{lang}`, which the row "
                    f"does not declare applicable — the cell would vanish "
                    f"rather than be scoped out.")
        cells = {}
        for language in row["languages"]:
            if language in scoped_out:
                cells[language] = {"state": "out-of-scope", "reason": scoped_out[language]}
            elif (row["mode"], row["case"], language) in have:
                cells[language] = {"state": "covered"}
            elif (row["mode"], row["case"], language) in on_variant:
                fixture, module, ticket = on_variant[(row["mode"], row["case"], language)]
                cells[language] = {
                    "state": "GAP",
                    "reason": f"`{fixture}` ships but binds `{module}` rather than the "
                              f"ecosystem declaration, so it exercises no ecosystem "
                              f"mode ({ticket or 'no relaxation ticket named'})",
                }
            else:
                cells[language] = {"state": "GAP"}
            counts[cells[language]["state"]] += 1
            if cells[language]["state"] == "covered" and (
                row["mode"], row["case"], language
            ) in pending_cases:
                cells[language]["pending"] = True
                covered_pending += 1
        matrix.append({"mode": row["mode"], "case": row["case"],
                       "source": row["source"], "cells": cells})

    # The invariant compares the states against an INDEPENDENT count of what
    # the inventory declares. The first version computed
    # `declared = sum(counts.values())` and then compared that same sum to
    # itself — `x != x`, which can never fire. A cell dropped or double-counted
    # moved both sides together and stayed green.
    declared = sum(len(row["languages"]) for row in declaration["inventory"])
    graded = counts["covered"] + counts["GAP"] + counts["out-of-scope"]
    if graded != declared:
        raise CorpusError(
            f"the sum invariant does not hold: the inventory declares {declared} "
            f"cells and {graded} were graded (covered {counts['covered']}, GAP "
            f"{counts['GAP']}, out-of-scope {counts['out-of-scope']}). A cell is "
            f"in no state, or in two."
        )
    duplicates = [
        row["case"] for row in declaration["inventory"]
        if len(row["languages"]) != len(set(row["languages"]))
    ]
    if duplicates:
        raise CorpusError(f"inventory rows declare a language twice: {duplicates}")

    return {
        "gap_count": counts["GAP"],
        "covered_count": counts["covered"],
        "covered_pending_count": covered_pending,
        "out_of_scope_count": counts["out-of-scope"],
        "declared_cells": declared,
        "matrix": matrix,
    }


def main() -> int:
    try:
        declaration = load_declaration()
        cases = discover()
        bounds = build(declaration, cases)
    except CorpusError as error:
        print(f"corpus: {error}", file=sys.stderr)
        return 1

    if "--json" in sys.argv:
        # `_declared` is loader scaffolding — the declaration as written, kept
        # so a check can ask whether the AUTHOR wrote a field rather than
        # whether it was derived. It is not part of the payload a runner reads,
        # and leaving it in duplicated every declared field in a nested copy.
        public = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cases]
        print(json.dumps({"bounds": bounds, "cases": public}, indent=1))
        return 0

    pending = [c for c in cases if c.get("pending")]
    print(f"fixtures on disk        : {len(cases)}")
    if pending:
        print(f"  pending a fix         : {len(pending)}")
        for c in pending:
            print(f"      {c['id']} -> {c['pending']}")
    print(f"declared cells          : {bounds['declared_cells']}")
    print(f"  covered               : {bounds['covered_count']}"
          + (f"  ({bounds['covered_pending_count']} of them PENDING — a case "
             f"exists and the engine fails it)" if bounds["covered_pending_count"] else ""))
    print(f"  out-of-scope          : {bounds['out_of_scope_count']}")
    print(f"  GAP                   : {bounds['gap_count']}")
    print()
    # The per-cell PENDING flag is printed, not just counted in the summary.
    # Without it the matrix reads `covered` on rows the engine detects nothing
    # on, and `covered` here means only "a fixture exists" — the exact
    # conflation between "there is a case" and "it works" that this corpus was
    # built to end. Two whole minting rows are covered in three languages
    # today with no detector behind either.
    for row in bounds["matrix"]:
        states = " ".join(
            f"{lang}={cell['state']}" + ("(pending)" if cell.get("pending") else "")
            for lang, cell in sorted(row["cells"].items())
        )
        print(f"  {row['mode']:12s} {row['case']:32s} {states}")
    print()
    print("  covered = a fixture exists for the cell. covered(pending) = it "
          "exists AND the engine fails it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
