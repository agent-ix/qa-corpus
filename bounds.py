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

        if (case_dir / "input").is_dir():
            cases.append({**shared, "dir": str(rel), "expect": str(rel / "expect.yaml")})
            continue

        variants = sorted(d for d in case_dir.iterdir() if (d / "input").is_dir())
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
            })
    return cases


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
