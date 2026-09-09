#!/usr/bin/env python3
"""Prove corpus verification selects published recorded revisions.

Regressions for agent-ix/qa-corpus#15 and agent-ix/qa-corpus#17.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_compatibility_corpus.py")
SPEC = importlib.util.spec_from_file_location("build_compatibility_corpus", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def git(repository: Path, *arguments: str) -> str:
    """Run one local Git command and return its stripped stdout."""
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="qa-corpus-source-ref-") as raw:
        root = Path(raw)
        contract_ir = root / "quire-contract-ir"
        code_rs = root / "quire-code-rs"
        quoin = root / "quoin"
        contract_ir.mkdir()
        code_rs.mkdir()
        quoin.mkdir()

        git(contract_ir, "init", "--quiet")
        git(contract_ir, "config", "user.email", "qa-corpus@example.invalid")
        git(contract_ir, "config", "user.name", "QA Corpus Selftest")
        payload = contract_ir / "payload.txt"
        payload.write_text("recorded\n", encoding="utf-8")
        git(contract_ir, "add", "payload.txt")
        git(contract_ir, "commit", "--quiet", "-m", "recorded source")
        recorded = git(contract_ir, "rev-parse", "HEAD")

        payload.unlink()
        git(contract_ir, "add", "--update")
        git(contract_ir, "commit", "--quiet", "-m", "advance source")
        current = git(contract_ir, "rev-parse", "HEAD")
        git(contract_ir, "update-ref", "refs/remotes/origin/main", current)

        BUILDER.CONTRACT_IR = contract_ir
        BUILDER.CODE_RS = code_rs
        BUILDER.QUOIN = quoin
        committed = {
            "cases": [
                {
                    "origin": {
                        "repository": "agent-ix/quire-contract-ir",
                        "revision": recorded,
                    }
                }
            ],
            "producer_cases": [
                {
                    "producer": "agent-ix/quire-code-rs",
                    "revision": recorded,
                },
                {
                    "producer": "agent-ix/quoin tier-1 measurement",
                    "revision": recorded,
                },
            ],
        }
        refs = BUILDER.recorded_source_refs(committed)
        assert BUILDER.read_at(contract_ir, "payload.txt", refs[contract_ir]) == b"recorded\n"
        BUILDER.require_published_source_refs({contract_ir: recorded})

        recorded_tree = git(contract_ir, "rev-parse", f"{recorded}^{{tree}}")
        unpublished = git(
            contract_ir,
            "commit-tree",
            recorded_tree,
            "-m",
            "locally present but unpublished source",
        )
        for unacceptable, expected_diagnostic in (
            (unpublished, "not reachable from origin/main"),
            ("f" * 40, "cannot verify recorded source revision"),
        ):
            try:
                BUILDER.require_published_source_refs({contract_ir: unacceptable})
            except ValueError as error:
                message = str(error)
                assert str(contract_ir) in message
                assert unacceptable in message
                assert expected_diagnostic in message
            else:
                raise AssertionError(
                    f"unpublished source revision was accepted: {unacceptable}"
                )

        try:
            BUILDER.read_at(contract_ir, "payload.txt")
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("floating origin/main unexpectedly retained the old path")

    print("compatibility corpus recorded-source selection selftest passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
