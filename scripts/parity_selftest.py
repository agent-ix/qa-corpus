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
  discrimination and a fixture whose whole claim is structural would read as
  blind. That case blinds a fixture down to one incidental scalar plus a
  `validate_absent` naming the control's own input path. It passes only if the
  control's tree was the one validated: grade the case's own tree instead and
  nothing mismatches, the block is blind, and the run goes red.

  **THE RULE HAS NEARLY NO REACH OVER THE REAL CORPUS, and this case is why it
  is tested at all** (CR-132, retracting the unhedged form this docstring used
  to carry).

  RETRACTED AGAIN, and this time by the tree rather than by a reader. This
  paragraph said "two of 77 fixtures declare a `validate_*` key … zero of the 35
  graded pairs carry one", and ended by naming `#286` giving `wrong-type-cell` a
  control as what would raise the reach above zero. **#286 did that.** Three
  files declare a `validate_*` key now, `wrong-type-cell` has a control, that
  pair is graded, and the reach is 1 pair — not 0 of 35, and not over 35 pairs.
  The prediction came true and the sentence describing the world before it kept
  being published, which is the same defect as the fixture counts one file over
  (<derived:fixtures=189> today).

  The case below still MANUFACTURES a `validate_absent` on
  `real-tests-zero-tags`, and still should: one pair is not a demonstration that
  the rule can fail on demand, and a correct rule with almost no subject has to
  be shown capable of failing or it is indistinguishable from one that is not
  there.

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
COPY_ITEMS = ("bounds.py", "verify.py", "corpus.yaml", "cases", "modules", "config")

FAILURE = "cases/disposition/real-tests-zero-tags/rust/expect.yaml"
CONTROL_INPUT = "real-tests-zero-tags-control/rust/input"
# THE FORWARD SUBJECT IS SYNTHESIZED, NOT BORROWED.
#
# This named `cases/attachment/tag-on-describe-header/expect-pending.yaml`, and
# on 2026-08-25 the corpus reached ZERO PENDING — every fixture's ticket landed
# or was answered — so no forward block exists to mutate and this gate could not
# run at all. A gate that works only while the backlog holds a specimen makes
# the reward for fixing every known defect a red build.
#
# A pending case is built in the copy instead: any live case, made pending on a
# ticket that does not exist, declared a behaviour change, with a forward block
# restating its live measurement.
FORWARD_CASE = "cases/attachment/tag-on-describe-header"
FORWARD = f"{FORWARD_CASE}/expect-pending.yaml"
FORWARD_TICKET = "agent-ix/quire-rs#999999"


def graded_live(tree: pathlib.Path) -> str:
    """`FORWARD_CASE`'s live block, reduced to its graded measurements.

    Comments and diagnostic keys are dropped: a behaviour-change forward block
    restates the SAME measurement after the fix, and a token the engine already
    emits is refused there by a different rule.
    """
    out, skipping = [], False
    for line in (tree / FORWARD_CASE / "expect.yaml").read_text().splitlines():
        if line[:1] not in (" ", "\t", "-", "#") and ":" in line:
            skipping = line.startswith(("diagnostic_", "absent_diagnostic_"))
        if skipping or line.startswith("#") or not line.strip():
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def make_pending(tree: pathlib.Path, forward_block: str) -> None:
    """Make `FORWARD_CASE` pending on a synthetic behaviour-change ticket."""
    case = tree / FORWARD_CASE / "case.yaml"
    case.write_text(
        case.read_text()
        + f"pending: {FORWARD_TICKET}\n"
        + "pending_reason: >-\n  A subject synthesized by parity_selftest so the"
          " gate does not depend on the corpus holding one.\n"
    )
    decl = tree / "corpus.yaml"
    decl.write_text(
        decl.read_text().replace(
            "behaviour_change_tickets: []",
            f"behaviour_change_tickets:\n- {FORWARD_TICKET}",
        )
    )
    write(tree, FORWARD, forward_block)


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

# THE SKEPTIC PAIR, whose ONLY discriminator is the suspicion channel
# (agent-ix/quire-rs#358). `vacuous-property-suite` and its control have
# identical `backed`, `total` and `binding_census` by construction — that
# identity is the point, because it is exactly the payload the failure case
# published for months while asserting nothing about its own defect.
#
# So this mutation is the one that would have caught the original bug: strip
# `suspicions`/`absent_suspicions` and the two blocks are indistinguishable,
# which is what a reader that silently ignored an unmodelled key would produce.
# Written as the counts alone rather than as a deletion, so the block still
# satisfies every SHAPE rule — non-empty, known keys, controlled case — and
# fails only on the differential.
SKEPTIC_FAILURE = "cases/skeptic/vacuous-property-suite/expect.yaml"
BLIND_SKEPTIC = "backed: 1\ntotal: 3\n"

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
        # The VALUE is read, not transcribed: pinning the literal `backed: 2`
        # here made the mutation a no-op the moment the live block re-measured.
        lambda t: make_pending(
            t, re.sub(r"^backed: \d+$", "backed: 99", graded_live(t),
                      count=1, flags=re.M)),
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
    (
        "a reader that drops the `suspicions` channel",
        lambda t: write(t, SKEPTIC_FAILURE, BLIND_SKEPTIC),
        "HOLDS against vacuous-property-suite-control's payload",
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
