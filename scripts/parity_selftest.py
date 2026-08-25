#!/usr/bin/env python3
"""Prove `verify.py`'s FR-065-AC-42 differential can fail, and grades the right tree.

WHY THIS FILE EXISTS. AC-42 — a failure case's `expect.yaml`, graded against its
CONTROL's payload, must produce at least one mismatch — is the strongest rule in
FR-065, and until `agent-ix/quire-rs#337` it existed in ONE of the two readers.
The Rust harness had graded it since TC-1028 landed. `verify.py` ran each case
once, against its own payload, and never cross-graded anything; the Python loader
checked that a control was NAMED, which is a predicate on shape and therefore the
exact class of defect AC-42 exists to close. So the two-reader independence this
corpus is built on stopped immediately before the check that carries it.

A gate that has never been observed to reject anything is indistinguishable from
one that cannot, so the differential arrives with its own mutation suite. Each
case copies the corpus to a temporary tree, applies exactly ONE mutation, and
requires `verify.py` to exit non-zero **naming the defect** — an exit code alone
would pass on an unrelated crash.

    QUIRE=/path/to/quire python3 scripts/parity_selftest.py

TWO OF THE CASES MUST STAY GREEN, and they are not padding.

* The unmutated CONTROL: without it every rejection below could be a corpus
  merely broken by copying.
* The `validate_*` SOURCE case. `quire validate` reads a spec TREE and cannot be
  recomputed from a coverage payload, so the differential has to re-run it over
  the CONTROL's tree; recomputed from the case's own, those keys contribute no
  discrimination and `wrong-type-cell` — whose coverage payload is byte-identical
  to a healthy tree's and whose entire claim is structural — would read as blind.
  That case blinds a fixture down to one incidental scalar plus a `validate_absent`
  naming the control's own input path. It passes only if the control's tree was
  the one validated: grade the case's own tree instead and nothing mismatches, the
  block is blind, and the run goes red.

THE PARITY CONSTRUCTION the review asked for is case 2. Before #337 that mutated
corpus was accepted by `verify.py` (`mismatches: 0`, exit 0) and rejected by
`cargo test --test corpus_cases` (TC-1028). It is now rejected by both.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPY_ITEMS = ("bounds.py", "verify.py", "corpus.yaml", "cases", "modules")

FAILURE = "cases/disposition/real-tests-zero-tags/rust/expect.yaml"
CONTROL_INPUT = "real-tests-zero-tags-control/rust/input"
FORWARD = "cases/attachment/tag-on-describe-header/expect-pending.yaml"


def write(tree: pathlib.Path, rel: str, text: str) -> None:
    (tree / rel).write_text(text)


def replace(tree: pathlib.Path, rel: str, old: str, new: str) -> None:
    """Textual, not a YAML round-trip — a round-trip reformats the file and can
    mask a mutation that exists only in the source text."""
    path = tree / rel
    body = path.read_text()
    if old not in body:
        raise AssertionError(f"{rel}: mutation anchor not found: {old!r}")
    path.write_text(body.replace(old, new, 1))


# `real-tests-zero-tags-rust` totals 4 and so does its control, which is what
# makes this the review's own example: an assertion true of the defective tree
# and of the repaired one. It satisfies every SHAPE rule the loader has — it is
# non-empty, its keys are known, and a controlled case is exempt from the
# "`findable` names what finds it" proxy precisely because AC-42 is stronger.
# The `unbacked_rows` list that actually separates this pair is gone.
BLIND_LIVE = "total: 4\n"

# The same blinding, plus one key that can only mismatch if the CONTROL's tree
# was validated: the control's own input path, which appears in every finding
# `quire validate` reports about it and in none about the case's own tree.
VALIDATE_SOURCE = f'total: 4\nvalidate_absent:\n  - "{CONTROL_INPUT}"\n'

# FR-065-AC-46, both branches. `real-tests-zero-tags` is `disposition`, whose
# witness channels are the dispositions themselves — `metrics`, `groups`,
# `unbacked_rows`, `untracked_symbols` and the diagnostics. `backed` is not one:
# a repository-wide backing count is the population, not the bucketing.
#
# NO WITNESS AT ALL. `backed: 0` against a control that reports 2 mismatches, so
# it clears AC-42's floor — and names no disposition channel whatsoever, so
# under AC-46 it detects nothing about this family.
NO_WITNESS = "backed: 0\n"

# A WITNESS THAT DOES NOT DISCRIMINATE. Same evasion, plus one real witness key
# whose value holds for the control too. AC-42 passes on `backed`, the witness
# set is non-empty, and restricted to it the block is blind — which is the
# distinction AC-46 exists to draw and the one a "names a witness key" shape
# check could not.
BLIND_WITNESS = "backed: 0\nabsent_diagnostic_reasons:\n  - hollow-denominator\n"

# (name, mutation or None, substring the failure must name — None means the
#  corpus must STAY valid)
CASES = [
    (
        "control: an unmutated copy still passes",
        None,
        None,
    ),
    (
        "THE PARITY CASE — a live block blinded to one incidental scalar",
        lambda t: write(t, FAILURE, BLIND_LIVE),
        "HOLDS against real-tests-zero-tags-control-rust's payload",
    ),
    (
        "a behaviour-change forward block that no repaired tree could produce",
        lambda t: replace(t, FORWARD, "backed: 2", "backed: 99"),
        "describes no reachable state",
    ),
    (
        "the `validate_*` keys are graded over the CONTROL's tree",
        lambda t: write(t, FAILURE, VALIDATE_SOURCE),
        None,
    ),
    (
        "AC-46 — a block that clears AC-42 and names NO witness channel",
        lambda t: write(t, FAILURE, NO_WITNESS),
        "names no `disposition` witness channel",
    ),
    (
        "AC-46 — a witness channel that is named but does not discriminate",
        lambda t: write(t, FAILURE, BLIND_WITNESS),
        "only OUTSIDE its `disposition` witness channels",
    ),
]


def run_verify(tree: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "verify.py"], cwd=tree, capture_output=True, text=True,
        env={**os.environ, "QUIRE": os.environ["QUIRE"]})


def main() -> int:
    if not os.environ.get("QUIRE"):
        print("parity: set QUIRE to the binary to test — the differential needs a\n"
              "        payload from every control, and grading a corpus with an\n"
              "        unidentified binary is the defect this corpus exists to catch.",
              file=sys.stderr)
        return 1

    failures: list[str] = []
    for name, mutation, expect in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            tree = pathlib.Path(tmp) / "corpus"
            tree.mkdir()
            for item in COPY_ITEMS:
                src, dst = ROOT / item, tree / item
                shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
            if mutation is not None:
                mutation(tree)
            done = run_verify(tree)
            output = done.stdout + done.stderr

            # Every case, mutated or not, must actually have graded pairs. A
            # resolution bug that paired nothing would report a clean
            # differential over an empty set, and every assertion here would
            # pass on a check that ran zero times.
            graded = re.search(r"differential pairs graded: (\d+)", output)
            if not graded or int(graded.group(1)) == 0:
                failures.append(
                    f"{name}: the differential graded no pairs, so it asserted "
                    f"nothing\n{output[:600]}")
                continue

            if expect is None:
                if done.returncode != 0:
                    failures.append(
                        f"{name}: verify.py rejected a corpus that must stay "
                        f"valid\n{output[:900]}")
                else:
                    print(f"  ok   {name} ({graded.group(1)} pairs)")
                continue

            if done.returncode == 0:
                failures.append(
                    f"{name}: verify.py exited 0 on a mutated corpus — the "
                    f"differential cannot fail")
            elif expect not in output:
                failures.append(
                    f"{name}: rejected, but named something else. Wanted "
                    f"{expect!r}, got:\n{output[:900]}")
            else:
                print(f"  ok   {name} ({graded.group(1)} pairs)")

    print()
    if failures:
        for problem in failures:
            print(f"FAIL  {problem}")
        print(f"\n{len(failures)} of {len(CASES)} failed")
        return 1
    rejecting = sum(1 for _, _, expect in CASES if expect is not None)
    print(f"{len(CASES)}/{len(CASES)} — {rejecting} mutations rejected by name "
          f"(2 for AC-42, 2 for AC-46), 1 unmutated control accepted, and 1 case "
          f"that passes only when the control's tree is the one validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
