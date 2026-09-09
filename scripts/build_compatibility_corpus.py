#!/usr/bin/env python3
"""Assemble the accepted compatibility-fixture corpus.

Consumed by `agent-ix/engineering-assurance` FR-011, which pins this repository
as a submodule and reads the corpus in place. The corpus lives here rather than
there because it retains real governance evidence, and engineering-assurance is
a public repository whose publication boundary permits fictional fixtures only.


Retains real bytes from real repositories and records, for every constructed
case, exactly what was changed and why. Legacy PGM-01 history contains no
failed, unavailable, not-computed, stale, or tampered record — a fact worth
stating rather than papering over — so those cases are derived from real bytes
by one named mutation each, and the corpus says so per case.

Run from the repository root:

    python3 scripts/build_compatibility_corpus.py --check   # verify, write nothing
    python3 scripts/build_compatibility_corpus.py           # rewrite the corpus

The sources are read in place and never written to. `--check` is what the gate
runs; a plain run is how a maintainer refreshes the corpus after a source
repository advances.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = REPO_ROOT / "compatibility"
# Sibling checkouts of the source repositories. Overridable so the corpus can
# be rebuilt anywhere; a hard-coded developer path would also be a workstation
# location this repository's content-rights gate rightly refuses to publish.
DEV_ROOT = Path(os.environ.get("ASSURANCE_SOURCE_ROOT", REPO_ROOT.parent))

CONTRACT_IR = DEV_ROOT / "quire-contract-ir"
CODE_RS = DEV_ROOT / "quire-code-rs"
QUOIN = DEV_ROOT / "quoin"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def revision(repo: Path, ref: str = "origin/main") -> str:
    """Resolve the selected source ref, not whatever is checked out.

    Refresh mode selects the published ``origin/main`` commit. Check mode
    supplies the immutable revision already recorded by the committed corpus.
    A working tree can sit on a branch, mid-review, or dirty, so neither mode
    reads ``HEAD`` implicitly.
    """
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", ref],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def read_at(repo: Path, path: str, ref: str = "origin/main") -> bytes:
    """Read one path from the selected immutable source revision."""
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def read(path: Path) -> bytes:
    return path.read_bytes()


def compact(value: Any) -> bytes:
    """Deterministic bytes for a constructed record."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def legacy_source(record_id: str, source_ref: str) -> bytes:
    return read_at(
        CONTRACT_IR, f"evidence/{record_id}/manifest.json", source_ref
    )


def recorded_digest(record_id: str, source_ref: str) -> str:
    """The digest the source repository itself recorded for the manifest."""
    checksums = read_at(
        CONTRACT_IR, f"evidence/{record_id}.sha256", source_ref
    ).decode("utf-8")
    for line in checksums.splitlines():
        if line.endswith(f"evidence/{record_id}/manifest.json"):
            return line.split()[0]
    raise SystemExit(f"{record_id} records no manifest digest")


def recorded_source_refs(committed: dict[str, Any]) -> dict[Path, str]:
    """Return the one recorded revision for every external source repository.

    A committed corpus that attributes one repository to multiple revisions is
    internally ambiguous and cannot select an immutable verification source.
    """
    repositories = {
        "agent-ix/quire-contract-ir": CONTRACT_IR,
        "agent-ix/quire-code-rs": CODE_RS,
        "agent-ix/quoin": QUOIN,
    }
    revisions: dict[str, set[str]] = {name: set() for name in repositories}
    for case in committed.get("cases", []):
        origin = case.get("origin")
        if not isinstance(origin, dict):
            continue
        repository = origin.get("repository")
        source_revision = origin.get("revision")
        if repository in revisions and isinstance(source_revision, str):
            revisions[repository].add(source_revision)
    for case in committed.get("producer_cases", []):
        producer = case.get("producer")
        source_revision = case.get("revision")
        if not isinstance(producer, str) or not isinstance(source_revision, str):
            continue
        repository = producer.split(" ", 1)[0]
        if repository in revisions:
            revisions[repository].add(source_revision)

    selected: dict[Path, str] = {}
    for repository, path in repositories.items():
        candidates = revisions[repository]
        if len(candidates) != 1:
            raise ValueError(
                f"committed corpus records {len(candidates)} revisions for "
                f"{repository}: {sorted(candidates)}"
            )
        selected[path] = next(iter(candidates))
    return selected


def require_published_source_refs(source_refs: dict[Path, str]) -> None:
    """Reject recorded revisions not reachable from each published main ref.

    Object availability is insufficient: a local checkout can retain an
    orphaned or synthetic commit that a clean verifier cannot fetch. The
    remote-tracking ref is deliberately checked without fetching so corpus
    verification remains an offline, non-mutating operation.
    """
    for repository, source_revision in source_refs.items():
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "merge-base",
                "--is-ancestor",
                source_revision,
                "origin/main",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 1:
            raise ValueError(
                "recorded source revision is not reachable from origin/main: "
                f"{repository} at {source_revision}"
            )
        if result.returncode != 0:
            diagnostic = result.stderr.strip() or "Git could not resolve the revision"
            raise ValueError(
                "cannot verify recorded source revision against origin/main: "
                f"{repository} at {source_revision}: {diagnostic}"
            )


def build(source_refs: dict[Path, str] | None = None) -> dict[str, Any]:
    source_refs = source_refs or {}
    contract_ir_ref = source_refs.get(CONTRACT_IR, "origin/main")
    code_rs_ref = source_refs.get(CODE_RS, "origin/main")
    quoin_ref = source_refs.get(QUOIN, "origin/main")
    contract_ir_revision = revision(CONTRACT_IR, contract_ir_ref)
    code_rs_revision = revision(CODE_RS, code_rs_ref)
    quoin_revision = revision(QUOIN, quoin_ref)

    cases: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}

    def legacy_case(case_id: str, record_id: str, note: str) -> bytes:
        raw = legacy_source(record_id, contract_ir_ref)
        payloads[case_id] = raw
        cases.append(
            {
                "id": case_id,
                "kind": "legacy",
                "family": "pgm01-v1",
                "retained_path": f"records/{case_id}.json",
                "retained_sha256": digest(raw),
                "origin": {
                    "repository": "agent-ix/quire-contract-ir",
                    "revision": contract_ir_revision,
                    "path": f"evidence/{record_id}/manifest.json",
                    "recorded_sha256": recorded_digest(record_id, contract_ir_ref),
                },
                "derivation": None,
                "expected": {"outcome": "lossy", "note": note},
            }
        )
        return raw

    base = legacy_case(
        "legacy-v1-passing",
        "pgm-01-02568b1",
        "A real accepted record. Every mapped check is passed or skipped.",
    )
    legacy_case(
        "legacy-v1-inconclusive",
        "pgm-01-e8dc1e9",
        "A real record carrying inconclusive checks; inconclusive is preserved, "
        "not rounded to passed or failed.",
    )
    legacy_case(
        "legacy-v1-skipped",
        "pgm-01-097f24a",
        "A real record carrying skipped checks alongside inconclusive ones.",
    )

    def derived_case(
        case_id: str,
        kind: str,
        raw: bytes,
        operation: str,
        reason: str,
        expected: dict[str, Any],
        family: str = "pgm01-v1",
    ) -> None:
        payloads[case_id] = raw
        cases.append(
            {
                "id": case_id,
                "kind": kind,
                "family": family,
                "retained_path": f"records/{case_id}.json",
                "retained_sha256": digest(raw),
                "origin": {
                    "repository": "agent-ix/quire-contract-ir",
                    "revision": contract_ir_revision,
                    "path": "evidence/pgm-01-02568b1/manifest.json",
                    "recorded_sha256": recorded_digest(
                        "pgm-01-02568b1", contract_ir_ref
                    ),
                },
                "derivation": {"from": "legacy-v1-passing", "operation": operation,
                               "reason": reason},
                "expected": expected,
            }
        )

    decoded = json.loads(base)

    failed = json.loads(base)
    failed["checks"][0]["status"] = "fail"
    derived_case(
        "derived-failed",
        "failed",
        compact(failed),
        "/checks/0/status: 'pass' -> 'fail'",
        "PGM-01 history records no failed check. A failing legacy record has to "
        "exist in the corpus, so one is constructed from real bytes by a single "
        "named edit rather than written from imagination.",
        {
            "outcome": "lossy",
            "required_mappings": [
                {"source_path": "/checks/0/status", "value": "failed"}
            ],
            "note": "A failed legacy check maps to failed and stays failed.",
        },
    )

    unavailable = json.loads(base)
    unavailable["checks"][0]["status"] = "unavailable"
    derived_case(
        "derived-unavailable",
        "unavailable",
        compact(unavailable),
        "/checks/0/status: 'pass' -> 'unavailable'",
        "PGM-01 history records no unavailable check.",
        {
            "outcome": "lossy",
            "required_mappings": [
                {"source_path": "/checks/0/status", "value": "unavailable"}
            ],
            "note": "Unavailable is neither passed nor failed and is not "
            "collapsed into either.",
        },
    )

    not_computed = json.loads(base)
    not_computed["checks"][0]["status"] = "not_computed"
    derived_case(
        "derived-not-computed",
        "not_computed",
        compact(not_computed),
        "/checks/0/status: 'pass' -> 'not_computed'",
        "The shared model carries not_computed; PGM-01 v1 has no such status "
        "and its mapper does not know one. The expected outcome records that "
        "refusal rather than inventing a translation for it.",
        {
            "outcome": "unreadable",
            "required_unmapped_reason": "unknown",
            "note": "A legacy status the mapping does not know is refused. "
            "Not-computed reaches the shared model through a current-model "
            "producer record, not through a PGM-01 back-translation.",
        },
    )

    malformed = json.loads(base)
    del malformed["collector"]
    derived_case(
        "derived-malformed",
        "malformed",
        compact(malformed),
        "remove /collector",
        "A truncated legacy record must be reported as unreadable rather than "
        "read as a record with no producer.",
        {
            "outcome": "unreadable",
            "note": "A missing required legacy field is unreadable, not empty.",
        },
    )

    tampered = base.replace(
        decoded["subjectRevision"].encode("ascii"), b"0" * 40, 1
    )
    if tampered == base:
        raise SystemExit("tampered derivation changed nothing")
    payloads["derived-tampered"] = tampered
    cases.append(
        {
            "id": "derived-tampered",
            "kind": "tampered",
            "family": "pgm01-v1",
            "retained_path": "records/derived-tampered.json",
            "retained_sha256": digest(tampered),
            "origin": {
                "repository": "agent-ix/quire-contract-ir",
                "revision": contract_ir_revision,
                "path": "evidence/pgm-01-02568b1/manifest.json",
                "recorded_sha256": recorded_digest(
                    "pgm-01-02568b1", contract_ir_ref
                ),
            },
            "derivation": {
                "from": "legacy-v1-passing",
                "operation": "/subjectRevision replaced with 40 zeroes",
                "reason": "Verified against the UNCHANGED record's digest, so "
                "the mapping sees bytes that do not match the identity it was "
                "handed.",
            },
            "expected": {
                "outcome": "incompatible",
                "verify_against_digest_of": "legacy-v1-passing",
                "require_no_mappings": True,
                "note": "Altered bytes yield no interpreted field at all.",
            },
        }
    )

    unreadable = b"not json at all\n"
    payloads["derived-unreadable"] = unreadable
    cases.append(
        {
            "id": "derived-unreadable",
            "kind": "malformed",
            "family": "pgm01-v1",
            "retained_path": "records/derived-unreadable.json",
            "retained_sha256": digest(unreadable),
            "origin": None,
            "derivation": {
                "from": None,
                "operation": "constructed non-JSON bytes",
                "reason": "The bytes are the whole point; there is no real "
                "record to derive them from.",
            },
            "expected": {
                "outcome": "unreadable",
                "note": "Bytes that are not JSON are unreadable, not absent.",
            },
        }
    )

    incompatible = json.loads(base)
    incompatible["schemaVersion"] = "quire.pgm01-evidence/v99"
    derived_case(
        "derived-incompatible-version",
        "legacy",
        compact(incompatible),
        "/schemaVersion: 'quire.pgm01-evidence/v1' -> 'quire.pgm01-evidence/v99'",
        "An unknown schema version must refuse, not fall back to the newest "
        "mapping it happens to know.",
        {
            "outcome": "incompatible",
            "note": "An unknown schema version is refused explicitly.",
        },
    )

    stale_source = CORPUS_ROOT / "sources" / "pgm01-v2.json"
    stale = json.loads(read(stale_source))
    stale["historicalDisposition"] = "retracted"
    stale_bytes = compact(stale)
    payloads["derived-stale"] = stale_bytes
    cases.append(
        {
            "id": "derived-stale",
            "kind": "stale",
            "family": "pgm01-v2",
            "retained_path": "records/derived-stale.json",
            "retained_sha256": digest(stale_bytes),
            "origin": {
                "repository": "agent-ix/qa-corpus",
                "revision": None,
                "path": "compatibility/sources/pgm01-v2.json",
                "recorded_sha256": digest(read(stale_source)),
            },
            "derivation": {
                "from": None,
                "operation": "/historicalDisposition: 'active' -> 'retracted'",
                "reason": "No real PGM-01 v2 record exists in this ecosystem — "
                "all ten retained records are v1 — so the v2 case is built on "
                "the constructed v2 fixture and labelled as constructed.",
            },
            "expected": {
                "outcome": "lossy",
                "required_mappings": [
                    {"source_path": "/historicalDisposition", "value": "stale"}
                ],
                "note": "A retracted legacy record is stale evidence, not "
                "absent evidence and not a failure.",
            },
        }
    )

    # The current-model case is the receipt the chain below produced. It is the
    # one record in the corpus that is NOT legacy, so the gate can show that a
    # current record and a legacy record are read by different contracts rather
    # than by one contract that happens to accept both.
    receipt_bytes = read(CORPUS_ROOT / "chain" / "receipt.json")
    cases.append(
        {
            "id": "current-verification-receipt",
            "kind": "current",
            "family": "quoin-verification-receipt-v1",
            "retained_path": "chain/receipt.json",
            "retained_sha256": digest(receipt_bytes),
            "origin": {
                "repository": "agent-ix/quoin",
                "revision": quoin_revision,
                "path": "produced by quoin change-assurance receipt",
                "recorded_sha256": None,
            },
            "derivation": None,
            "expected": {
                "outcome": "valid",
                "schema": "chain/quoin-verification-receipt-v1.schema.json",
                "note": "A current-model receipt is validated against Quoin's "
                "packaged schema, not through the PGM-01 mapping.",
            },
        }
    )

    producers = [
        {
            "id": "producer-code-graph",
            "language": "rust",
            "producer": "agent-ix/quire-code-rs",
            "revision": code_rs_revision,
            "path": "tests/golden/fixture.json",
            "source": (CODE_RS, "tests/golden/fixture.json"),
            "feeds": "verification_definition",
            "retention": "retained",
            "note": "A real governed code-graph producer's own golden output.",
        },
        {
            "id": "producer-contract-conformance",
            "language": "rust",
            "producer": "agent-ix/quire-contract-ir",
            "revision": contract_ir_revision,
            "path": "corpus/contract-v0.1/manifest.json",
            "source": (CONTRACT_IR, "corpus/contract-v0.1/manifest.json"),
            "feeds": "verification_definition",
            "retention": "retained",
            "note": "The contract conformance corpus the runner replays.",
        },
        {
            "id": "producer-measurement",
            "language": "typescript",
            "producer": "agent-ix/quoin tier-1 measurement",
            "revision": quoin_revision,
            "path": "spec/evidence/measurements/"
            "tier1-20260826153027044-9fc213e27a72.json",
            "source": (
                QUOIN,
                "spec/evidence/measurements/"
                "tier1-20260826153027044-9fc213e27a72.json",
            ),
            "feeds": "measurement",
            "retention": "retained",
            "note": "A real retained measurement collection with its config, "
            "corpus, and scorer digests.",
        },
        {
            "id": "producer-static-scan",
            "language": "text",
            "producer": "agent-ix/quoin audit-static",
            "revision": quoin_revision,
            "path": "tests/fixtures/evidence/audit-static-real.txt",
            "source": (QUOIN, "tests/fixtures/evidence/audit-static-real.txt"),
            "feeds": "diagnostic",
            "retention": "retained",
            "note": "A console-stream artifact retained because it IS the "
            "material diagnostic, not because stdout is scraped.",
        },
        {
            "id": "producer-external-engine",
            "language": "rust",
            "producer": "cargo-audit",
            "revision": quoin_revision,
            "path": "tests/fixtures/evidence/cargo-audit-real.json",
            "source": (QUOIN, "tests/fixtures/evidence/cargo-audit-real.json"),
            "feeds": "check_result",
            "retention": "referenced",
            "note": "Real external-engine output, pinned by digest but NOT "
            "copied here: it embeds third-party advisory prose and upstream "
            "issue links, which sit outside this repository's publishable "
            "content boundary. A holder of the source repository can verify "
            "the digest; this corpus does not republish the bytes.",
        },
        {
            "id": "producer-agent-eval",
            "language": "typescript",
            "producer": "agent-ix/quoin agent-eval",
            "revision": quoin_revision,
            "path": "tests/fixtures/evidence/agent-eval-real.json",
            "source": (QUOIN, "tests/fixtures/evidence/agent-eval-real.json"),
            "feeds": "measurement",
            "retention": "referenced",
            "note": "Real agent-evaluation output, pinned by digest but NOT "
            "copied here: it records an absolute transcript path from the "
            "machine that produced it, which this repository does not publish.",
        },
    ]

    producer_cases = []
    for entry in producers:
        repo, relative = entry.pop("source")
        raw = read_at(repo, relative, source_refs.get(repo, "origin/main"))
        record = {
            **{k: v for k, v in entry.items() if k != "id"},
            "id": entry["id"],
            "source_sha256": digest(raw),
        }
        if entry["retention"] == "retained":
            suffix = Path(relative).suffix or ".txt"
            record["retained_path"] = f"producers/{entry['id']}{suffix}"
            record["retained_sha256"] = digest(raw)
            payloads[entry["id"]] = raw
        producer_cases.append(record)

    # The chain artifacts are retained evidence, not something rebuilt on every
    # check: they were produced once by the exact tools named below, and the
    # committed bytes are what a reviewer verifies. Re-running the chain here
    # would replace the evidence with a fresh claim about it.
    chain_files = [
        ("quire-provenance.json", "quire_provenance", "quire provenance"),
        ("record-sealed.json", "change_assurance_record",
         "quoin change-assurance seal-record"),
        ("attestation-sealed.json", "proof_attestation",
         "quoin change-assurance seal-attestation"),
        ("decisions.json", "human_decision", "retained ix-flow decision history"),
        ("audits.json", "audit_report", "retained FR-032 audit report"),
        ("receipt.json", "verification_receipt", "quoin change-assurance receipt"),
        ("quoin-verification-receipt-v1.schema.json", "receipt_schema",
         "packaged Quoin schema asset, copied byte-for-byte"),
    ]
    chain = {
        "purpose": (
            "One Quire static export carried through Quoin intake and audit to "
            "a verification receipt, with every intermediate artifact retained "
            "verbatim. Nothing re-runs it; the bytes are the demonstration."
        ),
        "subject": {
            "repository": "agent-ix/quire-contract-ir",
            "revision": contract_ir_revision,
        },
        "tools": {
            "quire": {
                "version": "0.31.0",
                "cli_source_revision": "4f6ed024cf27298b2dc49c7051941571197fddff",
                "engine_version": "0.46.0",
                "engine_source_revision": "ca7362d4dacecb96f01d74d1d971327118c25917",
            },
            "quoin": {
                "version": "0.23.1",
                "release": "npm @agent-ix/quoin@0.23.1",
                "source_revision": "9fb3aa258575d234274dcc7e639c17d7621e1db0",
                "note": "The released artifact, installed from the registry and "
                "run as `quoin`. The chain reproduced byte-identically from the "
                "source build that preceded it — same record, attestation, "
                "export, and receipt digests — so the release changed the "
                "provenance of this evidence and not the evidence.",
            },
        },
        "artifacts": [],
    }
    for name, role, command in chain_files:
        raw = read(CORPUS_ROOT / "chain" / name)
        chain["artifacts"].append(
            {
                "role": role,
                "produced_by": command,
                "retention": "retained",
                "retained_path": f"chain/{name}",
                "retained_sha256": digest(raw),
            }
        )

    # The Quire export itself is NOT republished: the engine records the
    # absolute module-manifest path of the machine that produced it, which is a
    # workstation location this repository does not publish. It needs no
    # separate digest constant — the retained attestation already binds its
    # exact bytes, so the reference below is read back from evidence rather
    # than asserted here.
    attestation = json.loads(read(CORPUS_ROOT / "chain" / "attestation-sealed.json"))
    chain["referenced_inputs"] = [
        {
            "role": "quire_export",
            "produced_by": "quire coverage --scope <pinned checkout> --json",
            "retention": "referenced",
            "media_type": attestation["retained_output"]["media_type"],
            "blake3": attestation["retained_output"]["digest"],
            "size_bytes": attestation["retained_output"]["size_bytes"],
            "bound_by": "chain/attestation-sealed.json",
            "reason": "Contains the absolute module-manifest path of the "
            "machine that produced it. The attestation and the receipt bind "
            "these exact bytes, so a holder of them verifies the whole chain.",
        }
    ]

    return {
        "corpus_version": "engineering-assurance.compatibility-corpus/v1",
        "purpose": (
            "The accepted fixture set for the contract campaign. Every legacy "
            "case is real bytes or a single named mutation of real bytes; every "
            "producer case is a real producer's own output. Nothing here is a "
            "verdict, and nothing here is executed."
        ),
        "limitations": [
            "Legacy PGM-01 history in this ecosystem is entirely v1 and records "
            "only pass, skipped, and inconclusive. The failed, unavailable, "
            "not-computed, stale, and tampered cases are therefore derived, and "
            "each one records the exact edit that produced it.",
            "PGM-01 v1 has no not-computed status. The mapping refuses one "
            "rather than translating it; not-computed reaches the shared model "
            "through a current-model producer record.",
            "No real PGM-01 v2 record exists to retain, so the v2 case is built "
            "on the constructed v2 fixture and is labelled as constructed.",
            "Retaining these bytes proves fixture integrity and mapping "
            "behaviour offline. It does not re-observe the source repositories.",
            "Two producer cases are referenced by digest rather than retained: "
            "the external-engine result embeds third-party advisory prose, and "
            "the agent-evaluation result records an absolute path from the "
            "machine that produced it. Both sit outside this repository's "
            "publishable content boundary, and a pinned digest is what can "
            "honestly be published in their place.",
        ],
        "cases": cases,
        "producer_cases": producer_cases,
        "chain": chain,
    }, payloads


def write(corpus: dict[str, Any], payloads: dict[str, bytes]) -> None:
    (CORPUS_ROOT / "records").mkdir(parents=True, exist_ok=True)
    (CORPUS_ROOT / "producers").mkdir(parents=True, exist_ok=True)
    for case in corpus["cases"]:
        # The current-model case points at a retained chain artifact rather than
        # a payload this script produced; it is evidence, not a derivation.
        if case["id"] in payloads:
            (CORPUS_ROOT / case["retained_path"]).write_bytes(payloads[case["id"]])
    for case in corpus["producer_cases"]:
        if case["retention"] == "retained":
            (CORPUS_ROOT / case["retained_path"]).write_bytes(payloads[case["id"]])
    (CORPUS_ROOT / "corpus.json").write_text(
        json.dumps(corpus, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed corpus reproduces from source; write nothing",
    )
    args = parser.parse_args()

    committed = None
    if args.check:
        committed = json.loads((CORPUS_ROOT / "corpus.json").read_text("utf-8"))
        source_refs = recorded_source_refs(committed)
        require_published_source_refs(source_refs)
        corpus, payloads = build(source_refs)
    else:
        corpus, payloads = build()
        write(corpus, payloads)
        print(f"wrote {len(corpus['cases'])} legacy and "
              f"{len(corpus['producer_cases'])} producer cases")
        return 0

    assert committed is not None
    differences = []
    if committed.get("cases") != corpus["cases"]:
        differences.append("cases")
    if committed.get("producer_cases") != corpus["producer_cases"]:
        differences.append("producer_cases")
    if committed.get("chain") != corpus["chain"]:
        differences.append("chain")
    for case in corpus["cases"] + corpus["producer_cases"]:
        if "retained_path" not in case:
            continue
        path = CORPUS_ROOT / case["retained_path"]
        if case["id"] not in payloads:
            if not path.exists() or digest(path.read_bytes()) != case["retained_sha256"]:
                differences.append(case["retained_path"])
            continue
        if not path.exists() or path.read_bytes() != payloads[case["id"]]:
            differences.append(case["retained_path"])
    if differences:
        print("corpus does not reproduce from source:", ", ".join(differences))
        return 1
    print("corpus reproduces from source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
