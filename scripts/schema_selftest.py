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

from bounds import validate_case

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


def remove_path(tree: pathlib.Path, rel: str) -> None:
    """Remove one fixture from a disposable corpus copy."""
    path = tree / rel
    if not path.exists():
        raise AssertionError(f"{rel}: removal target not found")
    shutil.rmtree(path) if path.is_dir() else path.unlink()


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
        "a malformed if_field_is_not rule is a stable schema diagnostic",
        lambda t: mutate_yaml(
            t, "corpus.yaml", "  conditional:\n",
            "  conditional:\n  - if_field_is_not: [kind, control]\n    then_required: [control_for]\n"),
        "case_schema.conditional[0].if_field_is_not must be a one-entry mapping",
    ),
    (
        "an applicable language with no case is rejected by the CI policy",
        lambda t: mutate_yaml(
            t, "corpus.yaml",
            "# DEPARTURES FROM THE CONTRACT, declared and ENFORCED.",
            "- mode: detection\n"
            "  case: policy-selftest-missing\n"
            "  source: agent-ix/quire-rs#278\n"
            "  languages: [rust]\n"
            "# DEPARTURES FROM THE CONTRACT, declared and ENFORCED."),
        "detection/policy-selftest-missing/rust",
    ),
    (
        "an out-of-scope language needs a written reason",
        lambda t: mutate_yaml(
            t, "corpus.yaml",
            "    python: >-\n"
            "      the declaration declares NO python test-name-id form. `manifest.yaml` carries\n"
            "      `rust-test-name-id` and `typescript-test-name-id` and no python sibling, so there is\n"
            "      no form for a python fixture to write the defect in.\n"
            "    rust: >-",
            "    python: \"\"\n"
            "    rust: >-"),
        "test-name-id-in-call-title/python: out-of-scope with no reason",
    ),
    (
        "every failure case needs a language-matched control",
        lambda t: remove_path(t, "cases/detection/low-symbol-binding-control"),
        "low-symbol-binding: no control names it",
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
        "a findable failure cannot omit its grading contract",
        lambda t: mutate_yaml(
            t, "cases/detection/low-symbol-binding/case.yaml",
            "grading_contract:", "not_grading_contract:"),
        "must declare `grading_contract`",
    ),
    (
        "a grading level cannot use an unknown applicability state",
        lambda t: mutate_yaml(
            t, "cases/detection/low-symbol-binding/case.yaml",
            "L2: {state: required}", "L2: {state: maybe}"),
        "grading_contract.levels.L2.state 'maybe' is not one of",
    ),
    (
        "a locality exclusion must carry a non-empty reason",
        lambda t: mutate_yaml(
            t, "cases/provenance/hollow-metric/case.yaml",
            "L2: {state: not_applicable, reason: \"the finding concerns an aggregate metric and has no unique source line\"}",
            "L2: {state: not_applicable}"),
        "excludes the case without a non-empty reason",
    ),
    (
        "a behavior channel cannot require a finding level",
        lambda t: mutate_yaml(
            t, "cases/disposition/greenfield-no-symbols/case.yaml",
            "L1: {state: not_applicable, reason: \"graded through the honest zero-population metric payload; no finding is expected\"}",
            "L1: {state: required}"),
        "a behavior case must exclude all finding levels",
    ),
    (
        "a `by_kind` FORBIDDEN field is rejected",
        # `by_kind.control.forbidden` is what stops a control declaring `case:`
        # and claiming an inventory cell it cannot cover — a control measures
        # nothing about its mode. The rule shipped implemented and unexercised:
        # none of the six original mutations reached this branch, so it had
        # never been observed to reject anything (SR-055 FND-005,
        # agent-ix/quire-rs#345).
        lambda t: mutate_yaml(
            t, "cases/attachment/tag-at-module-scope-control/case.yaml",
            "kind: control", "kind: control\ncase: tag-at-module-scope"),
        "a `control` case may not declare `case`",
    ),
    (
        "a `by_kind` VALUES constraint is rejected",
        # The other half, and the one that carries real weight: a control with
        # `findable: true` claims something is findable on healthy input, which
        # inverts what the control is for. Also unexercised until now.
        lambda t: mutate_yaml(
            t, "cases/attachment/tag-at-module-scope-control/case.yaml",
            "findable: false", "findable: true"),
        "is not one of [False] for a `control` case",
    ),
    (
        "an unknown `case_schema.types` spec is rejected, not skipped",
        # The reader's own vocabulary. A type name it does not know reached a
        # branch that appends a problem rather than silently skipping the
        # field — right behaviour, never demonstrated. Without this, adding a
        # type to the declaration and forgetting the reader would make every
        # field of that type unchecked, silently.
        lambda t: mutate_yaml(
            t, "corpus.yaml", "    findable: bool", "    findable: boolean"),
        "which is not a type this reader knows",
    ),
    (
        "`variant_forbidden` is READ, not restated in Python",
        # The one mutation that can tell "the gate follows the declaration"
        # from "the gate happens to agree with it". `discover()` enforced these
        # five names from a Python literal while `corpus.yaml` declared them and
        # nothing read it (SR-055 FND-001, agent-ix/quire-rs#342), so editing
        # the declaration changed nothing and the two were free to drift.
        #
        # ADDING a name rather than removing one, because removal proves
        # nothing on its own: no variant declares `mode:`, so a shrunk list
        # produces no failure to observe. Every one of the 49 per-language
        # `case.yaml` files declares `reproduce` and only `reproduce` — so a
        # declaration that forbids it must make this corpus fail, by name, and
        # can only do so if the declaration is what the reader consults.
        lambda t: mutate_yaml(
            t, "corpus.yaml",
            "  variant_forbidden:\n  - case",
            "  variant_forbidden:\n  - reproduce\n  - case"),
        "a variant may not declare ['reproduce']",
    ),
    (
        "a `pending:` with no `pending_reason:` is rejected",
        # ADDS the marker rather than renaming an existing case's reason.
        #
        # This used to rename `pending_reason:` in
        # `cases/attachment/tag-on-describe-header/case.yaml`, and on 2026-08-25
        # the corpus reached ZERO PENDING — every fixture'"'"'s ticket landed or was
        # answered — so the anchor vanished and the mutation could not apply.
        # A mutation pinned to a specimen stops testing the moment the specimen
        # is fixed, which makes the reward for burning the backlog down a red
        # gate. `marker-mismatch` is not pending and does not need to be: adding
        # `pending:` to any case must make `pending_reason` required.
        lambda t: mutate_yaml(
            t, "cases/attachment/marker-mismatch/case.yaml",
            "kind: failure", "kind: failure\npending: agent-ix/quire-rs#999999"),
        "`pending_reason` is required here",
    ),
    (
        "a variant cannot be both temporary and the declaration under test",
        lambda t: mutate_yaml(
            t, "cases/provenance/implements-never-asked/case.yaml",
            "declaration_under_test:",
            "relaxation_ticket: agent-ix/quire-rs#330\ndeclaration_under_test:"),
        "must declare exactly one of `relaxation_ticket` or `declaration_under_test`",
    ),
    (
        "every emitted diagnostic reason needs positive and negative coverage",
        lambda t: mutate_yaml(
            t, "corpus.yaml",
            "  - undeclared-coverage-vocabulary\n  # Tokens no engine emits YET",
            "  - undeclared-coverage-vocabulary\n  - zzz-unasserted\n  # Tokens no engine emits YET"),
        "asserted present missing ['zzz-unasserted']",
    ),
]


def check_conditional_library_surface() -> None:
    schema = {
        "required": ["kind"],
        "optional": ["ticket"],
        "by_kind": {"failure": {}, "control": {}},
        "conditional": [
            {"if_field_is_not": {"kind": "control"}, "then_required": ["ticket"]}
        ],
    }
    assert validate_case({"kind": "control"}, "control", "control-case", schema) == []
    problems = validate_case({"kind": "failure"}, "failure", "failure-case", schema)
    assert any("`ticket` is required" in problem for problem in problems), problems

    schema["conditional"][0]["if_field_is_not"] = ["kind", "control"]
    problems = validate_case({"kind": "failure"}, "failure", "failure-case", schema)
    assert any("one-entry mapping" in problem and "failure-case" in problem for problem in problems)


def run_bounds(tree: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "bounds.py", "--require-complete"], cwd=tree,
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
            shared = yaml.safe_load(path.read_text()) or {}
            case_dir = path.parent
            variants = sorted(
                directory
                for directory in case_dir.iterdir()
                if (directory / "input").is_dir()
            )
            if (case_dir / "input").is_dir():
                problems += validate_scaffolded(shared, path, tree, schema)
            else:
                for variant in variants:
                    per_case_path = variant / "case.yaml"
                    per_case = (
                        yaml.safe_load(per_case_path.read_text()) or {}
                        if per_case_path.is_file()
                        else {}
                    )
                    effective = {**shared, **per_case, "language": variant.name}
                    problems += validate_scaffolded(effective, per_case_path, tree, schema)
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
    # The last row is a VARIANT module, and it is the row this check was missing.
    # Every invocation here passed `--module ecosystem`, so the one argument that
    # changes which schema rules apply was never exercised — and `--module
    # variants/...` exited 0 writing a `case.yaml` `bounds.py` rejects for a
    # missing `relaxation_ticket` (SR-055 FND-003, agent-ix/quire-rs#343). A
    # check that only ever runs the default is a check with the same blind spot
    # as the thing it checks.
    for case, kind, module in (
        ("selftest-pair", "failure", "ecosystem"),
        ("selftest-pair", "control", "ecosystem"),
        ("selftest-pin", "regression", "ecosystem"),
        ("selftest-variant", "failure", "variants/no-implements-declaration"),
    ):
        done = subprocess.run(
            [sys.executable, "scripts/new_case.py",
             "--mode", "minting", "--case", case,
             "--language", "rust", "--kind", kind, "--module", module,
             "--issue", "agent-ix/quire-rs#336"],
            cwd=tree, capture_output=True, text=True)
        if done.returncode != 0:
            problems.append(
                f"`new_case.py --kind {kind}` exited {done.returncode}: "
                f"{(done.stdout + done.stderr).strip()[:300]}")

    # The EPIC grows one inventory row across languages. The on-ramp used to
    # reject this exact second call as "already exists" and always wrote Rust
    # source even when --language said Python (agent-ix/quoin#241).
    done = subprocess.run(
        [
            sys.executable,
            "scripts/new_case.py",
            "--mode",
            "minting",
            "--case",
            "selftest-pair",
            "--language",
            "python",
            "--kind",
            "failure",
            "--module",
            "ecosystem",
            "--issue",
            "agent-ix/quoin#241",
        ],
        cwd=tree,
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        problems.append(
            "`new_case.py` could not add Python to an existing case: "
            f"{(done.stdout + done.stderr).strip()[:300]}")
    else:
        pair = tree / "cases" / "minting" / "selftest-pair"
        shared = yaml.safe_load((pair / "case.yaml").read_text())
        if "language" in shared or "reproduce" in shared:
            problems.append("language-specific fields remained in the shared case metadata")
        if not (pair / "rust" / "input" / "src" / "lib.rs").is_file():
            problems.append("adding Python did not preserve the original Rust tree")
        if not (pair / "python" / "input" / "src" / "test_example.py").is_file():
            problems.append("--language python did not scaffold Python evidence")
        if (pair / "python" / "input" / "src" / "lib.rs").exists():
            problems.append("--language python still scaffolded Rust evidence")
        variant = yaml.safe_load((pair / "python" / "case.yaml").read_text())
        reproduce = str((variant or {}).get("reproduce", ""))
        if not reproduce.startswith("IX_FILAMENT_MODULES_PATH=modules/ecosystem "):
            problems.append("the second-language reproduce line does not load the module path")
        if "selftest-pair/python/input" not in reproduce:
            problems.append("the second-language reproduce line names the wrong input tree")
    return problems


def main() -> int:
    failures: list[str] = []

    try:
        check_conditional_library_surface()
        print("  ok   conditional rule library surface accepts valid and diagnoses malformed shapes")
    except AssertionError as error:
        failures.append(f"conditional rule library surface: {error}")

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
