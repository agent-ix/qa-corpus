#!/usr/bin/env python3
"""Prove the case-metadata gate can fail.

A gate that has never been observed to reject anything is indistinguishable
from one that cannot. That is not a hypothetical here: before this file existed,
`bounds.py` had **no** required-field schema and **no** duplicate-id check, and
an outside review demonstrated it by mutating the corpus twice and watching
`python3 bounds.py` exit 0 reporting all 77 fixtures both times
(`agent-ix/quire-rs#336`). The Rust reader rejected both mutations. Two readers
exist so that drift like that is visible; it was not.

So the schema arrives with its own mutation suite rather than a claim. Each case
below copies the corpus to a temporary tree, applies exactly one mutation, and
requires `bounds.py` to exit non-zero **naming the thing that is wrong** — an
exit code alone would pass on an unrelated crash.

    python3 scripts/schema_selftest.py

The first case is the CONTROL: an unmutated copy must still exit 0. Without it
every other case would pass on a corpus that was simply broken by copying, which
is the vacuity this suite is here to rule out.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPY_ITEMS = ("bounds.py", "corpus.yaml", "cases", "modules")


def mutate_yaml(tree: pathlib.Path, rel: str, old: str, new: str) -> None:
    """Textual, not a YAML round-trip.

    Rewriting through the parser would reformat the file and could mask a
    mutation that only exists in the source text.
    """
    path = tree / rel
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"{rel}: mutation anchor not found: {old!r}")
    path.write_text(text.replace(old, new, 1))


# (name, mutation or None for the control, substring the failure must name)
CASES = [
    (
        "control: an unmutated copy still passes",
        None,
        None,
    ),
    (
        "a missing required field is rejected (the review's mutation 1)",
        lambda t: mutate_yaml(
            t, "cases/attachment/tests-directory-topology/case.yaml",
            "issue_ref:", "not_issue_ref:"),
        "required field `issue_ref` is missing",
    ),
    (
        "a duplicate derived id is rejected (the review's mutation 2)",
        lambda t: mutate_yaml(
            t, "cases/attachment/tag-on-non-test-function-control/case.yaml",
            "id: tag-on-non-test-function-control",
            "id: tag-at-module-scope-control"),
        "is already used by",
    ),
    (
        "a required field present but EMPTY is rejected",
        lambda t: mutate_yaml(
            t, "cases/attachment/tests-directory-topology/case.yaml",
            "issue_ref: ", "issue_ref: #"),
        "is present but empty",
    ),
    (
        "a field in neither `required` nor `optional` is rejected",
        lambda t: mutate_yaml(
            t, "cases/attachment/tests-directory-topology/case.yaml",
            "kind:", "kidn: x\nkind:"),
        "is in neither `required` nor `optional`",
    ),
    (
        "a field of the wrong TYPE is rejected, not just a missing one",
        lambda t: mutate_yaml(
            t, "cases/attachment/tag-at-module-scope-control/case.yaml",
            "control_for:\n- tag-at-module-scope",
            "control_for: tag-at-module-scope"),
        "`control_for` must be a list of strings",
    ),
    (
        "a `pending:` with no `pending_reason:` is rejected",
        lambda t: mutate_yaml(
            t, "cases/attachment/tag-on-describe-header/case.yaml",
            "pending_reason:", "unused_reason:"),
        "`pending_reason` is required here",
    ),
]


def run_bounds(tree: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "bounds.py"], cwd=tree,
        capture_output=True, text=True)


def check_scaffolder() -> list[str]:
    """`make new-case` must write metadata this corpus's schema accepts.

    The Makefile says the first thing an author sees is "a skeleton that runs,
    not a schema document". Nothing checked it, and it did not. `new_case.py`
    required `modules/<name>/manifest.yaml`, so it **failed outright for
    `ecosystem` — its own default, and the module every real case binds** —
    because `modules/ecosystem/` is a search PATH holding two module
    directories (CR-108). Had it succeeded it would have written the broken
    `--module modules/ecosystem` invocation CR-108 already recorded as wrong
    for the third time. It also wrote `control_for` as a bare string, where
    every real control and `CaseMeta`'s `Option<Vec<String>>` want a list, and
    wrote `case:` on controls, which `case_schema` forbids.

    Four defects in the on-ramp, none reachable from any gate.

    **Scoped to the metadata, deliberately.** A scaffolded case is incomplete by
    design until its author fills `expect.yaml`, and `bounds.py` rightly refuses
    a case that asserts nothing about its own payload — a case counting its cell
    covered while asserting nothing is the conflation this corpus exists to end.
    So this does not require the whole tree to stay valid; it requires the
    `case.yaml` the scaffolder writes to satisfy `case_schema` (#336).
    """
    import bounds

    schema = bounds.load_declaration()["case_schema"]
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tree = pathlib.Path(tmp) / "corpus"
        tree.mkdir()
        for item in COPY_ITEMS:
            src, dst = ROOT / item, tree / item
            shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
        problems += _scaffold(tree)
        for path in sorted(tree.glob("cases/*/selftest-*/case.yaml")):
            declared = yaml.safe_load(path.read_text()) or {}
            problems += validate_scaffolded(declared, path, tree, schema)
        if not list(tree.glob("cases/*/selftest-*/case.yaml")):
            problems.append(
                "the scaffolder wrote no case.yaml, so nothing below was checked")
    return problems


def validate_scaffolded(
    declared: dict, path: pathlib.Path, tree: pathlib.Path, schema: dict
) -> list[str]:
    import bounds

    where = str(path.relative_to(tree))
    return bounds.validate_case(declared, str(declared.get("kind")), where, schema)


def _scaffold(tree: pathlib.Path) -> list[str]:
    problems: list[str] = []
    shutil.copytree(ROOT / "scripts", tree / "scripts", dirs_exist_ok=True)
    # A PAIR under one `--case`, plus a regression. Scaffolding a failure and a
    # control under different names would leave the failure uncontrolled and the
    # control pointing at nothing, and the run would fail on FR-065-AC-13 rather
    # than on anything the scaffolder wrote — the test would be about the wrong
    # thing while still looking like it worked.
    for case, kind in (
        ("selftest-pair", "failure"),
        ("selftest-pair", "control"),
        ("selftest-pin", "regression"),
    ):
        done = subprocess.run(
            [sys.executable, "scripts/new_case.py",
             "--mode", "minting", "--case", case,
             "--language", "rust", "--kind", kind, "--module", "ecosystem",
             "--issue", "agent-ix/quire-rs#336"],
            cwd=tree, capture_output=True, text=True)
        if done.returncode != 0:
            problems.append(
                f"`new_case.py --kind {kind}` exited {done.returncode}: "
                f"{(done.stdout + done.stderr).strip()[:300]}")
    return problems


def main() -> int:
    failures: list[str] = []

    scaffolder = check_scaffolder()
    if scaffolder:
        failures += [f"the scaffolder writes invalid metadata: {p}" for p in scaffolder]
    else:
        print("  ok   `make new-case` writes metadata `case_schema` accepts")

    for name, mutation, expect in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            tree = pathlib.Path(tmp) / "corpus"
            tree.mkdir()
            for item in COPY_ITEMS:
                src = ROOT / item
                dst = tree / item
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            if mutation is not None:
                mutation(tree)
            done = run_bounds(tree)
            output = done.stdout + done.stderr

            # `expect is None` means the corpus must STILL be valid after the
            # step — the unmutated control, and the scaffolder, whose output is
            # supposed to be a case this corpus accepts.
            if expect is None:
                if done.returncode != 0:
                    failures.append(
                        f"{name}: bounds.py rejected a corpus that must stay "
                        f"valid\n{output[:600]}")
                else:
                    print(f"  ok   {name}")
                continue

            if done.returncode == 0:
                failures.append(
                    f"{name}: bounds.py exited 0 on a mutated corpus — the gate "
                    f"cannot fail")
            elif expect not in output:
                failures.append(
                    f"{name}: rejected, but named something else. Wanted "
                    f"{expect!r}, got:\n{output[:600]}")
            else:
                print(f"  ok   {name}")

    print()
    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        print(f"\n{len(failures)} of {len(CASES)} failed")
        return 1
    print(f"{len(CASES) + 1}/{len(CASES) + 1} — {len(CASES) - 1} mutations "
          f"rejected by name, 1 unmutated control accepted, and the scaffolder "
          f"writes metadata `case_schema` accepts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
