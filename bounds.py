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
            merged = {**shared, **per_case, "language": language}
            merged.setdefault("id", f"{shared.get('id', case_dir.name)}-{language}")
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
        module = c.get("module", "")
        keys = {(c.get("mode"), c.get("case", c.get("id")), c.get("language")),
                (c.get("mode"), c.get("id"), c.get("language"))}
        if module == "ecosystem":
            covered_by |= keys
        else:
            for key in keys:
                on_variant[key] = (c.get("id"), module, c.get("relaxation_ticket"))
    have = covered_by

    matrix, counts = [], {"covered": 0, "GAP": 0, "out-of-scope": 0}
    for row in declaration["inventory"]:
        scoped_out = row.get("out_of_scope", {})
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
        matrix.append({"mode": row["mode"], "case": row["case"],
                       "source": row["source"], "cells": cells})

    declared = sum(counts.values())
    if counts["covered"] + counts["GAP"] + counts["out-of-scope"] != declared:
        raise CorpusError("the sum invariant does not hold — a cell is in no state")

    return {
        "gap_count": counts["GAP"],
        "covered_count": counts["covered"],
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

    print(f"fixtures on disk        : {len(cases)}")
    print(f"declared cells          : {bounds['declared_cells']}")
    print(f"  covered               : {bounds['covered_count']}")
    print(f"  out-of-scope          : {bounds['out_of_scope_count']}")
    print(f"  GAP                   : {bounds['gap_count']}")
    print()
    for row in bounds["matrix"]:
        states = " ".join(
            f"{lang}={cell['state']}" for lang, cell in sorted(row["cells"].items())
        )
        print(f"  {row['mode']:12s} {row['case']:32s} {states}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
