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
    check_expectations(cases)
    check_controls(cases)
    return cases


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
    declaration = yaml.safe_load((ROOT / "corpus.yaml").read_text())
    gaps = declaration.get("known_gaps") or {}
    module_gaps = set((gaps.get("control_binds_another_module") or {}).get("cases") or [])
    uncontrolled = set((gaps.get("uncontrolled_failure_cases") or {}).get("cases") or [])

    partners = {}
    for c in cases:
        if c.get("kind") != "failure":
            continue
        partners[(c["id"], c.get("language"))] = c
        if c.get("case"):
            partners[(c["case"], c.get("language"))] = c
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
                    if c.get(field) == other.get(field) or c["id"] in module_gaps:
                        continue
                    if True:
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
    controlled = {
        (partner, c.get("language"))
        for c in cases if c.get("kind") == "control"
        and isinstance(c.get("control_for"), list)
        for partner in c["control_for"]
    }
    for c in cases:
        if c.get("kind") != "failure":
            continue
        row = c.get("case") or c["id"]
        if (row, c.get("language")) in controlled or (c["id"], c.get("language")) in controlled:
            continue
        if row in uncontrolled or c["id"] in uncontrolled:
            continue
        problems.append(
            f"{c['id']}: no control names it (FR-065-AC-13). Without one, a check "
            f"firing on every input scores perfect recall. Declare it under "
            f"`known_gaps.uncontrolled_failure_cases` if that is deliberate.")
    known = {c.get("case") or c["id"] for c in cases} | {c["id"] for c in cases}
    stale = sorted(uncontrolled - known) + sorted(module_gaps - known)
    if stale:
        problems.append(
            f"known_gaps names {stale}, which is no case in the corpus — a "
            f"declared gap that has outlived its fixture")


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
        check_reasons(name, live, "expect.yaml", case, emitted, forward)
        if not forward_path.is_file():
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


def asserts_something(block: dict) -> bool:
    """Whether a block asserts anything at all, field by field.

    A block that grades zero assertions trivially passes, which for a forward
    block means every runner reports its ticket as landed.
    """
    return any(
        block.get(key) not in (None, [], {})
        for key in KNOWN_EXPECT_KEYS
    )


# Every key an expectation block may carry. Shared with `verify.py`, which
# grades them; declared here because the LOADER now rejects a typo rather than
# grading one.
KNOWN_EXPECT_KEYS = {
    "backed", "total", "diagnostic_reasons", "absent_diagnostic_reasons",
    "diagnostic_paths", "diagnostic_message_contains", "binding_census",
    "metrics", "no_symbol_rows", "unbacked_rows", "groups",
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
        print(json.dumps({"bounds": bounds, "cases": cases}, indent=1))
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
