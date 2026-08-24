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

MODULE_YAML = "spec/tests.md"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--case", required=True)
    ap.add_argument("--language", default="rust")
    ap.add_argument("--kind", default="failure", choices=["failure", "control"])
    ap.add_argument("--module", default="ecosystem")
    ap.add_argument("--issue", default="", help="the filing this case regresses")
    args = ap.parse_args()

    declaration = yaml.safe_load((ROOT / "corpus.yaml").read_text())
    if args.mode not in declaration["mode_families"]:
        print(f"`{args.mode}` is not a declared mode family: "
              f"{declaration['mode_families']}", file=sys.stderr)
        return 1
    if not (ROOT / "modules" / args.module / "manifest.yaml").is_file():
        print(f"module `{args.module}` has no manifest under modules/", file=sys.stderr)
        return 1

    case_id = args.case if args.kind == "failure" else f"{args.case}-control"
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
    meta = {
        "id": case_id,
        "case": args.case,
        "issue_ref": args.issue or "REQUIRED — name the filing this case regresses",
        "mode": args.mode,
        "language": args.language,
        "module": args.module,
        "kind": args.kind,
        "findable": args.kind == "failure",
        "reproduce": f"quire coverage --scope {relative}/input "
                     f"--module modules/{args.module} --json",
        "tags": ["TC-REPLACE-ME"],
        "comment": "What this case is about, and the measurement that made it worth "
                   "a fixture.",
    }
    if args.kind == "control":
        meta["control_for"] = args.case
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
