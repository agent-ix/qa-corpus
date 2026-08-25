#!/usr/bin/env python3
"""Scaffold a runnable case skeleton.

The first thing an author sees should be a directory that runs, not a schema
document. Everything written here is the minimum a case needs to be discovered,
graded and reproduced by hand.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def resolve_module(module: str) -> str | None:
    """`--module <dir>` for one module, `IX_FILAMENT_MODULES_PATH=<dir>` for a path.

    `None` when the name resolves to neither.

    This used to require `modules/<name>/manifest.yaml` and emit
    `--module modules/<name>` unconditionally, which meant **`make new-case`
    failed for `ecosystem` — its own default, and the module every real case
    binds.** `modules/ecosystem/` holds `spec-artifacts-process` and
    `spec-artifacts-iso` side by side, because archetypes reference their schema
    files relative to a module root and the FR/TestMatrix archetypes live in the
    second one (CR-108). It is a search PATH, and `--module` takes one
    directory.

    So the documented on-ramp — the thing whose Makefile comment says "the first
    thing an author sees is a skeleton that runs, not a schema document" — could
    not produce a single case, and had it somehow produced one, the invocation it
    wrote would have been the exact broken `--module modules/ecosystem` form
    CR-108 recorded as wrong for the third time: it exits 0 with no output, and a
    reader concludes the case is clean.

    The same one-or-a-path rule TC-1021 applies to `module:` (#336).
    """
    directory = ROOT / "modules" / module
    if (directory / "manifest.yaml").is_file():
        return f"--module modules/{module}"
    if directory.is_dir() and any(
        child.joinpath("manifest.yaml").is_file() for child in directory.iterdir()
    ):
        return f"IX_FILAMENT_MODULES_PATH=modules/{module}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--case", required=True)
    ap.add_argument("--language", default="rust")
    ap.add_argument("--kind", default="failure",
                    choices=["failure", "control", "regression"])
    ap.add_argument("--module", default="ecosystem")
    ap.add_argument("--issue", default="", help="the filing this case regresses")
    args = ap.parse_args()

    declaration = yaml.safe_load((ROOT / "corpus.yaml").read_text())
    if args.mode not in declaration["mode_families"]:
        print(f"`{args.mode}` is not a declared mode family: "
              f"{declaration['mode_families']}", file=sys.stderr)
        return 1
    selector = resolve_module(args.module)
    if selector is None:
        print(f"module `{args.module}` names neither a manifest nor a directory "
              f"of them under modules/", file=sys.stderr)
        return 1

    case_id = f"{args.case}-control" if args.kind == "control" else args.case
    case_dir = ROOT / "cases" / args.mode / case_id
    if case_dir.exists():
        print(f"{case_dir.relative_to(ROOT)} already exists", file=sys.stderr)
        return 1

    for sub in ("spec", "src"):
        (case_dir / "input" / sub).mkdir(parents=True)

    (case_dir / "input" / "spec" / "FR-001.md").write_text(
        "---\nid: FR-001\ntype: FR\n---\n\n## Acceptance Criteria\n\n"
        "| ID | Criteria | Verification |\n|----|----------|--------------|\n"
        "| FR-001-AC-1 | Every finding shall default to warning. | Test (TC-001) |\n"
    )
    (case_dir / "input" / "spec" / "tests.md").write_text(
        "---\nid: TM-001\ntype: TestMatrix\n---\n\n## Test Case Summary\n\n"
        "| Test ID | Traces To | Status |\n|---------|-----------|--------|\n"
        "| TC-001 | FR-001-AC-1 | 🚧 |\n"
    )
    (case_dir / "input" / "src" / "lib.rs").write_text(
        "//! Replace with the miniature repository this case is about.\n\n"
        "#[cfg(test)]\nmod tests {\n    #[trace(\"TC-001\")]\n    #[test]\n"
        "    fn covers_the_criterion() {\n        assert_eq!(1 + 1, 2);\n    }\n}\n"
    )

    relative = case_dir.relative_to(ROOT)
    # A single module is selected with `--module` INSIDE the command; a module
    # PATH with an `IX_FILAMENT_MODULES_PATH=` assignment BEFORE it, which both
    # readers strip as a leading `KEY=value` token. TC-1020 requires the
    # invocation to name the module the case declares, either way.
    env, flag = (selector, "") if selector.startswith("IX_") else ("", selector)
    reproduce = " ".join(
        part for part in
        (env, "quire coverage --scope", f"{relative}/input", flag, "--json")
        if part
    )
    meta = {
        "id": case_id,
        "issue_ref": args.issue or "REQUIRED — name the filing this case regresses",
        "mode": args.mode,
        "language": args.language,
        "module": args.module,
        "kind": args.kind,
        "findable": args.kind == "failure",
        "reproduce": reproduce,
        "tags": ["TC-REPLACE-ME"],
        "comment": "What this case is about, and the measurement that made it worth "
                   "a fixture.",
    }
    # `case` names the INVENTORY ROW a fixture credits, and only a failure case
    # credits one. It was written on every kind, including controls — where
    # `case_schema` now forbids it, because a control measures nothing about the
    # mode and a `case:` on one is a claim to a cell it cannot cover.
    if args.kind == "failure" and args.case != case_id:
        meta["case"] = args.case
    # A LIST, always. This emitted a bare string, which every real control in
    # the corpus contradicts and `CaseMeta`'s `Option<Vec<String>>` refuses — so
    # `--kind control` produced a case the Rust reader could not read, and
    # nothing ran the scaffolder to find out (#336).
    if args.kind == "control":
        meta["control_for"] = [args.case]
    (case_dir / "case.yaml").write_text(
        yaml.safe_dump(meta, sort_keys=False, width=100, allow_unicode=True))

    (case_dir / "expect.yaml").write_text(
        "# Assert ONLY what this case is about. Every field is optional, and a\n"
        "# corpus where each case pins the whole envelope fails forty cases on one\n"
        "# unrelated change and is then relaxed wholesale.\n"
        "#\n"
        "# A failure case asserts `diagnostic_reasons`; its control asserts\n"
        "# `absent_diagnostic_reasons` for the same token.\n"
    )

    print(f"scaffolded {relative}")
    print(f"  run it:  {meta['reproduce']}")
    print(f"  then:    fill expect.yaml from what it printed, and set issue_ref")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
