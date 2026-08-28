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
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent


class CorpusError(Exception):
    """A corpus that cannot be read as declared."""


def load_declaration() -> dict:
    return load_yaml(ROOT / "corpus.yaml")


def validate_case(declared: dict, kind: str, where: str, schema: dict) -> list[str]:
    """Grade ONE effective case record against `corpus.yaml`'s `case_schema`.

    Returns every problem rather than raising on the first, because an author
    who omitted three fields should be told three times, not once per run.

    THE POINT OF THIS FUNCTION is that its rules are not written here. Two
    readers implement this corpus so that reader drift is visible; an outside
    review checked and found it was not — the Rust reader rejects a missing
    required field (serde) and duplicate ids, and this one checked neither.
    Reproduced: removing `issue_ref` from a `case.yaml`, and pointing two cases
    at one id, each left `bounds.py` exiting 0 over all 77 fixtures
    (agent-ix/quire-rs#336). A second hand-written list of required fields in
    Python would be the same defect one level up, so the list lives in
    `corpus.yaml` and both readers are held to it.

    `declared` is the record AS WRITTEN — for a language set, the shared
    `case.yaml` merged with the per-language one, plus the `language` taken from
    the directory. NOT the derived record: `discover()` injects a `case`, and
    grading the injection would make the "did the author write one?" checks
    vacuous.
    """
    problems: list[str] = []
    required = list(schema.get("required") or [])
    optional = list(schema.get("optional") or [])

    by_kind = (schema.get("by_kind") or {}).get(kind) or {}
    if kind not in (schema.get("by_kind") or {}):
        # Not this function's job to police the kind vocabulary — `case_kinds`
        # does that — but silently applying no per-kind rule to an unknown kind
        # would make every rule below optional for the price of a typo.
        problems.append(
            f"{where}: kind `{kind}` has no `case_schema.by_kind` entry, so no "
            f"per-kind rule could be applied")

    for field in required + list(by_kind.get("required") or []):
        if field not in declared:
            problems.append(f"{where}: required field `{field}` is missing")
        elif declared[field] is None or (
            isinstance(declared[field], (str, list, dict)) and not declared[field]
        ):
            # Empty is its own failure mode. `issue_ref: ""` satisfies a
            # presence check and records nothing, which is the state this
            # corpus's attribution rule exists to prevent.
            problems.append(f"{where}: `{field}` is present but empty")

    for field in by_kind.get("forbidden") or []:
        if field in declared:
            problems.append(
                f"{where}: a `{kind}` case may not declare `{field}`")

    for field, allowed in (by_kind.get("values") or {}).items():
        if field in declared and declared[field] not in allowed:
            problems.append(
                f"{where}: `{field}: {declared[field]!r}` is not one of "
                f"{allowed} for a `{kind}` case")

    for field, spec in (schema.get("types") or {}).items():
        if field not in declared:
            continue
        value = declared[field]
        if spec == "str":
            ok, want = isinstance(value, str), "a string"
        elif spec == "bool":
            ok, want = isinstance(value, bool), "true or false"
        elif spec == ["str"]:
            ok = isinstance(value, list) and all(isinstance(v, str) for v in value)
            want = "a list of strings"
        elif spec == "grading_contract":
            ok = isinstance(value, dict)
            want = "a grading contract mapping"
        else:
            problems.append(
                f"{where}: `case_schema.types` declares `{field}: {spec!r}`, "
                f"which is not a type this reader knows")
            continue
        if not ok:
            # Presence alone let `control_for: <string>` through here while the
            # Rust reader's `Option<Vec<String>>` refused it — one corpus, two
            # readers, one of them wrong, and no gate between them (#336).
            problems.append(
                f"{where}: `{field}` must be {want}, got "
                f"{type(value).__name__} {value!r}")

    known = set(required) | set(optional) | {"language"}
    for field in sorted(set(declared) - known):
        problems.append(
            f"{where}: `{field}` is in neither `required` nor `optional` — an "
            f"unmodelled field is a field nothing checks")

    for rule in schema.get("conditional") or []:
        trigger = rule.get("if_present")
        if trigger is not None:
            fires = trigger in declared
        else:
            (field, value), = (rule.get("if_field_is_not") or {}).items()
            fires = declared.get(field) != value
        if not fires:
            continue
        for field in rule.get("then_required") or []:
            if field not in declared:
                because = rule.get("why") or "declared in `case_schema`"
                problems.append(
                    f"{where}: `{field}` is required here — {because}")

    return problems


def discover() -> list[dict]:
    """Every fixture on disk, in either layout.

    A `case.yaml` with neither an `input/` beside it nor any `<language>/`
    subdirectory carrying one is **rejected**. Skipping it silently is how a
    half-authored fixture reads as an absent one, and absent is what
    `gap_count` is supposed to mean.
    """
    # `variant_forbidden` comes from the DECLARATION, not from a literal below.
    # It was declared in `corpus.yaml` and read by nothing, while this function
    # enforced the identical five names from a Python set — one contract, one
    # reader, and no relationship between them (SR-055 FND-001,
    # `agent-ix/quire-rs#342`). That is `result_record` with the sign flipped,
    # in the commit whose change record says a second hand-written list in
    # Python is the defect one level up.
    #
    # Absent is a HARD FAILURE, not a skip: a reader that enforces nothing when
    # its rule is missing is indistinguishable from one that enforced it and
    # found nothing, which is the confusion this corpus exists to end.
    schema = (load_declaration() or {}).get("case_schema") or {}
    protected = set(schema.get("variant_forbidden") or [])
    if not protected:
        raise CorpusError(
            "corpus.yaml declares no `case_schema.variant_forbidden`, so a "
            "variant could re-point the cell its fixture credits and nothing "
            "would fire (FR-065-AC-22, agent-ix/quire-rs#342)")

    cases: list[dict] = []
    for case_yaml in sorted((ROOT / "cases").glob("*/*/case.yaml")):
        case_dir = case_yaml.parent
        shared = load_yaml(case_yaml) or {}
        rel = case_dir.relative_to(ROOT)

        sub_languages = [d for d in case_dir.iterdir() if (d / "input").is_dir()]
        if (case_dir / "input").is_dir():
            # FR-065: a directory in BOTH layouts is rejected rather than
            # silently read as one of them. Both readers took the `input/`
            # branch and moved on, so a half-migrated case would have had its
            # language variants disappear from the matrix without a word.
            if sub_languages:
                raise CorpusError(
                    f"{rel}: carries both an `input/` and "
                    f"{sorted(d.name for d in sub_languages)} — a case is one "
                    f"layout or the other, and reading it as one silently drops "
                    f"the other.")
            cases.append({
                **shared, "dir": str(rel), "expect": str(rel / "expect.yaml"),
                "_declared": shared, "_where": str(rel),
            })
            continue

        variants = sorted(sub_languages)
        if not variants:
            raise CorpusError(
                f"{rel}: neither an `input/` nor any `<language>/input/`. A "
                f"half-authored fixture read as an absent one would make "
                f"gap_count mean something else."
            )
        for variant in variants:
            language = variant.name
            per_case = load_yaml(variant / "case.yaml") if (
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
            # baseline row, a baseline join — could be keyed across runners.
            base = merged.get("id", case_dir.name)
            merged["case"] = merged.get("case", base)
            merged["id"] = f"{base}-{language}"
            cases.append({
                **merged,
                "dir": str(variant.relative_to(ROOT)),
                "expect": str(variant.relative_to(ROOT) / "expect.yaml"),
                # The declaration AS WRITTEN. `merged` gains a derived `case`,
                # so a check on whether the author wrote one needs the original.
                # `language` comes from the directory and is part of the record
                # even though no file declares it (CR-109).
                "_declared": {**shared, **per_case, "language": language},
                "_where": f"{rel}/{language}",
            })
    declaration = load_declaration()
    check_grading_contracts(declaration, cases)
    check_case_schema(declaration, cases)
    check_known_gaps(declaration)
    detection = [case for case in cases if case.get("mode") != "reporting"]
    check_controls(detection)
    check_expectations(detection)
    return cases


def check_grading_contracts(declaration: dict, cases: list[dict]) -> None:
    """Require explicit finding-recall applicability on every scored failure.

    A behavior fixture and a finding fixture are both intentionally
    `findable`: one is found through a directly graded payload and the other
    through a producer finding. Treating the shared boolean as a promise that
    all three finding levels apply manufactured locality misses. The contract
    below makes that distinction authored data and refuses silent exclusions.
    """
    channels = {"finding", "direct-observation", "behavior"}
    levels = tuple(declaration.get("grading_levels") or [])
    states = {"required", "not_applicable"}
    problems: list[str] = []

    for case in cases:
        if (
            case.get("kind") != "failure"
            or not case.get("findable")
            or case.get("mode") == "reporting"
        ):
            continue
        contract = case.get("grading_contract")
        if not isinstance(contract, dict):
            problems.append(
                f"{case['id']}: a findable failure must declare "
                "`grading_contract` rather than inheriting finding levels "
                "from its fixture shape")
            continue
        unknown = set(contract) - {"channel", "levels"}
        if unknown:
            problems.append(
                f"{case['id']}: grading_contract has unknown keys "
                f"{sorted(unknown)}")
        channel = contract.get("channel")
        if channel not in channels:
            problems.append(
                f"{case['id']}: grading_contract.channel {channel!r} is not "
                f"one of {sorted(channels)}")
        declared_levels = contract.get("levels")
        if not isinstance(declared_levels, dict):
            problems.append(
                f"{case['id']}: grading_contract.levels must be a mapping")
            continue
        missing = set(levels) - set(declared_levels)
        extra = set(declared_levels) - set(levels)
        if missing or extra:
            problems.append(
                f"{case['id']}: grading_contract.levels missing "
                f"{sorted(missing)} and adds {sorted(extra)}")
        for level in levels:
            entry = declared_levels.get(level)
            if not isinstance(entry, dict):
                problems.append(
                    f"{case['id']}: grading_contract.levels.{level} must be "
                    "a mapping")
                continue
            unknown_entry = set(entry) - {"state", "reason"}
            if unknown_entry:
                problems.append(
                    f"{case['id']}: grading_contract.levels.{level} has "
                    f"unknown keys {sorted(unknown_entry)}")
            state = entry.get("state")
            if state not in states:
                problems.append(
                    f"{case['id']}: grading_contract.levels.{level}.state "
                    f"{state!r} is not one of {sorted(states)}")
            reason = entry.get("reason")
            if state == "not_applicable" and not (
                isinstance(reason, str) and reason.strip()
            ):
                problems.append(
                    f"{case['id']}: grading_contract.levels.{level} excludes "
                    "the case without a non-empty reason")
            if state == "required" and "reason" in entry:
                problems.append(
                    f"{case['id']}: grading_contract.levels.{level} is "
                    "required and therefore may not carry an exclusion reason")

        states_by_level = {
            level: (declared_levels.get(level) or {}).get("state")
            for level in levels
        }
        if channel == "behavior" and any(
            state != "not_applicable" for state in states_by_level.values()
        ):
            problems.append(
                f"{case['id']}: a behavior case must exclude all finding "
                "levels; its payload expectations remain the oracle")
        if channel == "direct-observation" and states_by_level != {
            "L1": "required", "L2": "required", "L3": "not_applicable"
        }:
            problems.append(
                f"{case['id']}: a direct observation requires L1/L2 and "
                "excludes finding-level L3")
        if channel == "finding" and states_by_level.get("L1") != "required":
            problems.append(
                f"{case['id']}: a finding channel must require L1")

    if problems:
        raise CorpusError(
            f"{len(problems)} grading-contract problem(s):\n  "
            + "\n  ".join(problems))


def check_case_schema(declaration: dict, cases: list[dict]) -> None:
    """Hold every case to `corpus.yaml`'s `case_schema`, and ids to uniqueness.

    Runs BEFORE anything derives a matrix from these records. A count computed
    over a corpus that does not satisfy its own schema is a number about
    something else.

    Fails ONCE with every problem. An author who omitted three fields is told
    three times rather than once per run, and a reviewer reads the whole state
    of the tree instead of its alphabetically-first defect.
    """
    schema = declaration.get("case_schema")
    if not schema:
        # Not a skip. A reader that quietly does nothing when its rules are
        # absent is indistinguishable from one that checked and found nothing,
        # which is the exact confusion this corpus exists to end.
        raise CorpusError(
            "corpus.yaml declares no `case_schema`, so no case metadata can be "
            "validated — the Rust reader would still reject what this one now "
            "cannot see (agent-ix/quire-rs#336)")

    problems: list[str] = []
    for case in cases:
        problems += validate_case(
            case["_declared"], str(case["_declared"].get("kind")),
            case["_where"], schema)

    # Uniqueness on the DERIVED id, because that is what a join is keyed on —
    # a language set's `<shared id>-<language>` is the id a baseline row, a
    # pending entry or a cross-runner record carries. Two cases sharing one
    # silently merge in every one of them.
    for field in schema.get("unique") or []:
        seen: dict[str, str] = {}
        for case in cases:
            value = case.get(field)
            if value is None:
                continue
            if value in seen:
                problems.append(
                    f"{case['_where']}: `{field}` {value!r} is already used by "
                    f"{seen[value]} — a collision merges two cases in every "
                    f"join keyed on `{field}`")
            else:
                seen[value] = case["_where"]

    if problems:
        raise CorpusError(
            f"{len(problems)} case-metadata problem(s):\n  "
            + "\n  ".join(problems))


def check_known_gaps(declaration: dict) -> None:
    """Every declared departure names a ticket.

    `pending:` requires a `pending_reason`; a variant `module` requires a
    `relaxation_ticket`. A `known_gaps` entry required neither, so one appended
    line was a total, permanent exemption from a contract clause with nothing
    recording who would undo it.
    """
    for name, entry in (declaration.get("known_gaps") or {}).items():
        reason = (entry or {}).get("reason") or ""
        if not re.search(r"#\d+", reason):
            raise CorpusError(
                f"known_gaps.{name}: its reason names no ticket. An exemption "
                f"from the contract with nothing tracking its removal is a "
                f"departure that becomes permanent by default.")
        if not ((entry or {}).get("cases") or []):
            raise CorpusError(
                f"known_gaps.{name}: declares no cases. An empty exemption is "
                f"a clause nobody removed when the last case was fixed.")


def failure_partners(cases: list[dict]) -> dict:
    """What a `control_for` NAME resolves to: `(name, language) -> failure case`.

    ID FIRST, `case:` alias second. One case's alias can equal another case's
    id — two do on this corpus — and an alias must never displace a real id.
    Written as setdefault-the-aliases-then-overwrite-with-the-ids rather than as
    a lookup order at each call site, because a single map is the thing three
    callers can share without re-deriving the precedence and getting it
    different.
    """
    partners: dict = {}
    for c in cases:
        if c.get("kind") == "failure" and c.get("case"):
            partners.setdefault((c["case"], c.get("language")), c)
    for c in cases:
        if c.get("kind") == "failure":
            partners[(c["id"], c.get("language"))] = c
    return partners


def controls_by_case(cases: list[dict]) -> dict:
    """`(failure id, language) -> [every control that names it]`.

    THE one resolution of "which control is this failure case's", shared by the
    loader's AC-13 pairing check, by `controlled_cases`, and by `verify.py`'s
    AC-42 differential. It was open-coded three times and the copies disagreed.

    A LIST, not one control. Two controls legitimately name
    `marker-form-mismatch` — `marker-form-declared` and
    `marker-form-mismatch-control` — so any rule that picks ONE of them picks it
    by iteration order: the Rust harness took the last, this reader would have
    taken the first, and that is a differing verdict about one corpus from the
    two readers that exist to make disagreement visible. Both now grade against
    EVERY control that names the case, which is stronger and order-independent
    (`agent-ix/quire-rs#337`).

    Resolution runs through `failure_partners`, so `control_for: [x]` credits
    the case whose **id** is `x` when one exists. The Rust harness instead keyed
    on the raw `control_for` string and fell back to the failure case's `case:`
    alias — which handed `marker-mismatch`, a case this corpus DECLARES under
    `known_gaps.uncontrolled_failure_cases`, the control belonging to
    `marker-form-mismatch`, so it never reached the declared-gap branch and was
    counted as controlled. That is where FR-065's "35 controlled failure cases
    at `3ff72c0`" came from; `bounds.py` counted 34 at the same revision.
    """
    partners = failure_partners(cases)
    pairs: dict = {}
    for c in cases:
        if c.get("kind") != "control" or not isinstance(c.get("control_for"), list):
            continue
        for name in c["control_for"]:
            failure = partners.get((name, c.get("language")))
            if failure is None:
                continue
            pairs.setdefault((failure["id"], failure.get("language")), []).append(c)
    return pairs


def controlled_cases(cases: list[dict]) -> set:
    """Every failure case, by id+language, that some control names."""
    return set(controls_by_case(cases))


def check_controls(cases: list[dict]) -> None:
    """Control pairing and `known_gaps`, checked at LOAD.

    These are corpus CONFORMANCE, not payload grading, so they belong to the
    loader — and there they need no engine binary, which is what lets a test
    drive them over a mutated copy. They lived in `verify.py`, where the only
    way to exercise them was to have a working `quire` in hand.
    """
    problems: list[str] = []
    # RESTORED. The shared-discovery refactor deleted this loop and nothing
    # replaced it, so the Python runner enforced zero corpus-level conformance:
    # deleting the flagship failure case left `26/26, 0 mismatches, rc 0` with
    # the PENDING lines simply gone. The commit that dropped it claimed to be
    # preventing the two readers from disagreeing.
    #
    # FAILURE cases only: including controls puts each control's own `case` in
    # the set, so `control_for` resolves against itself (FR-065-AC-13).
    declaration = load_declaration()
    gaps = declaration.get("known_gaps") or {}
    module_gaps = set((gaps.get("control_binds_another_module") or {}).get("cases") or [])
    uncontrolled = set((gaps.get("uncontrolled_failure_cases") or {}).get("cases") or [])

    # Keyed by `id` FIRST, and an alias never displaces one. This was a set
    # before the checks moved here; converting it to a dict to carry each
    # partner's mode and module introduced a silent overwrite, because one
    # case's `case:` alias can equal another case's `id`. Two real collisions
    # existed on this corpus — `catch-all-headline` and `marker-form-mismatch`
    # each name both a bench-legacy fixture and an ecosystem one — and the
    # later-sorted alias won. That misdiagnosed THREE controls as binding the
    # wrong module (they do not; their partners match exactly) and let a case
    # with no control of its own inherit somebody else's.
    #
    # SHARED with `controls_by_case` rather than open-coded here, which is how
    # the precedence came to be written twice in this file and a third time in
    # the Rust harness — where it was written differently (#337).
    partners = failure_partners(cases)
    for c in cases:
        if c.get("kind") != "control":
            continue
        # A LIST, always. One control can legitimately serve several failure
        # cases — the healthy repair of two single-cell defects in one document
        # is the same document — and a string form alongside a list form would
        # be two spellings of one claim.
        declared = c.get("control_for")
        if not declared:
            problems.append(f"{c['id']}: a control declares no `control_for`")
        elif not isinstance(declared, list):
            problems.append(
                f"{c['id']}: control_for is {declared!r}; it takes a LIST of "
                f"failure-case names")
        else:
            for partner in declared:
                key = (partner, c.get("language"))
                if key not in partners:
                    problems.append(
                        f"{c['id']}: control_for names {partner!r}, which is no "
                        f"failure case in {c.get('language')}")
                    continue
                # A control is the HEALTHY version of its partner, so it has to
                # be the same kind of thing. Nothing checked this once the field
                # became a list: measured, a `detection` control on the
                # bench-legacy variant could claim a `minting` case on the
                # ecosystem declaration — a different tree entirely — and every
                # gate stayed green.
                other = partners[key]
                for field in ("mode", "module"):
                    if c.get(field) == other.get(field):
                        continue
                    # Scoped to `module`. The exemption is declared for a
                    # control binding another MODULE; it excused a mode
                    # mismatch too, so a `detection` control could claim a
                    # `minting` partner and stay green.
                    if field == "module" and c["id"] in module_gaps:
                        continue
                    problems.append(
                            f"{c['id']}: control_for names {partner!r}, whose "
                            f"{field} is {other.get(field)!r} against this "
                            f"control's {c.get(field)!r}. A control is the "
                            f"healthy version of its partner, not any case that "
                            f"happens to resolve.")
        if c.get("findable"):
            problems.append(f"{c['id']}: a control cannot be findable")

    # AC-13's OTHER direction, which nothing enforced: every failure case is
    # named by SOME control. Eleven were not, while the declaration listed
    # three — and that declaration was read by no code at all.
    # Resolved through the id-first `partners` map, and keyed by the partner's
    # ID. Built from raw `control_for` strings, this had the same alias/id
    # collision the map above was just fixed for, in the other direction:
    # deleting `clean-control` — the ONLY control for the ecosystem case
    # `catch-all-properties` — left the loader green, because that case's
    # `case:` alias is also the ID of a bench-legacy fixture that has its own
    # control, so it silently inherited a stranger's.
    controlled = controlled_cases(cases)
    for c in cases:
        # A regression case is exempt: AC-13 exists so a check cannot score
        # perfect recall against input with no healthy counterpart, and a
        # regression case IS the healthy counterpart — there is no defect.
        if c.get("kind") != "failure":
            continue
        row = c.get("case") or c["id"]
        if (c["id"], c.get("language")) in controlled:
            continue
        if row in uncontrolled or c["id"] in uncontrolled:
            continue
        problems.append(
            f"{c['id']}: no control names it (FR-065-AC-13). Without one, a check "
            f"firing on every input scores perfect recall. Declare it under "
            f"`known_gaps.uncontrolled_failure_cases` if that is deliberate.")
    # EVERY list under `known_gaps`, not a hand-picked two. The first version
    # named `uncontrolled_failure_cases` and `control_binds_another_module`
    # explicitly, so adding a third list gave it a set of exemptions no staleness
    # check covered — a declaration going stale in exactly the way this check
    # exists to prevent.
    known = {c.get("case") or c["id"] for c in cases} | {c["id"] for c in cases}
    # `behaviour_change_tickets` is a declaration about the corpus exactly as
    # `known_gaps` is, and it sat outside this loop — measured, appending a
    # ticket no case is pending on was silently accepted, and an entry would
    # persist after its fixtures folded in with nothing saying so.
    waited_on = {c.get("pending") for c in cases if c.get("pending")}
    orphaned = sorted(set(declaration.get("behaviour_change_tickets") or []) - waited_on)
    if orphaned:
        problems.append(
            f"behaviour_change_tickets names {orphaned}, which no case is pending "
            f"on — a declaration that has outlived its fixtures")

    for gap, entry in (declaration.get("known_gaps") or {}).items():
        stale = sorted(set((entry or {}).get("cases") or []) - known)
        if stale:
            problems.append(
                f"known_gaps.{gap} names {stale}, which is no case in the "
                f"corpus — a declared gap that has outlived its fixture")


    if problems:
        raise CorpusError("; ".join(problems))


def check_expectations(cases: list[dict]) -> None:
    """Every expectation block, checked at LOAD.

    FR-065-AC-26 says the corpus LOADER rejects a broken pairing. It did not:
    only the two runners objected, so `bounds.py` — one of the three gates —
    exited 0 and printed an unchanged matrix, still counting six pending, over
    a corpus state the spec calls invalid.

    The reason vocabulary is checked here too. A forward block naming a token
    no ticket introduces sat pending forever with nothing to say so.
    """
    declaration = load_declaration()
    vocabulary = declaration.get("diagnostic_reasons") or {}
    emitted = set(vocabulary.get("emitted") or [])
    forward = dict(vocabulary.get("forward") or {})
    # A SUPPRESSED token behaves like a forward one for expectation purposes —
    # it cannot hold today — but unlike a forward one its literal is already in
    # the engine, which is TC-1026's business, not this function's.
    forward.update(vocabulary.get("suppressed") or {})
    gaps = declaration.get("known_gaps") or {}
    undetected = set((gaps.get("findable_but_undetected") or {}).get("cases") or [])
    controlled = controlled_cases(cases)
    behaviour_change = set(declaration.get("behaviour_change_tickets") or [])
    asserted_present: set[str] = set()
    asserted_absent: set[str] = set()

    for case in cases:
        directory = ROOT / case["dir"]
        live_path = ROOT / case["expect"]
        forward_path = directory / "expect-pending.yaml"
        ticket = case.get("pending")
        name = case["id"]

        if ticket and not forward_path.is_file():
            raise CorpusError(
                f"{name}: declares `pending: {ticket}` and ships no "
                f"expect-pending.yaml — the behaviour it waits on is asserted "
                f"nowhere (FR-065-AC-26).")
        if forward_path.is_file() and not ticket:
            raise CorpusError(
                f"{name}: ships expect-pending.yaml and declares no `pending:` "
                f"— a forward claim naming no ticket (FR-065-AC-26).")
        # FR-065 requires this of the LOADER; only the Rust runner checked it.
        if ticket and not (case.get("pending_reason") or "").strip():
            raise CorpusError(
                f"{name}: is pending on {ticket} with no `pending_reason`. A "
                f"marker with no stated reason is one nobody can decide whether "
                f"to remove.")
        # F9: a control serves inventory rows through its partners, not through
        # a `case:` of its own. One control now names TWO partners and could
        # only name one row — measured, pointing it at a row that does not
        # exist left every gate green, because `build()` credits only failure
        # cases and the field is dead for a control.
        if case.get("kind") == "control" and "case" in (case.get("_declared") or {}):
            raise CorpusError(
                f"{name}: a control declares `case:`. A control credits no cell; "
                f"the rows it serves are its `control_for` partners.")

        check_regression(name, case, forward_path)

        live = load_yaml(live_path) or {}
        # THE LIVE BLOCK TOO. This was enforced on the forward block by both
        # readers and on `expect.yaml` by neither, so emptying any failure
        # case's `expect.yaml` left every gate green with its cell still
        # `covered` — round one's defect exactly, reached by truncating the
        # file instead of by the `pending:` key. `unbacked_rows`, the one field
        # separating the two minting fixtures, is precisely what an empty live
        # block drops.
        if not asserts_something(live):
            raise CorpusError(
                f"{name}: expect.yaml asserts nothing. A case that asserts "
                f"nothing about its own payload still counts its cell covered, "
                f"which is the conflation this corpus exists to end.")
        unknown = set(live) - KNOWN_EXPECT_KEYS
        if unknown:
            raise CorpusError(
                f"{name}: expect.yaml declares unhandled key(s) {sorted(unknown)}.")
        check_reasons(name, live, "expect.yaml", case, emitted, forward)
        positive = set(live.get("diagnostic_reasons") or [])
        positive.update(live.get("diagnostic_paths") or {})
        positive.update(live.get("diagnostic_message_contains") or {})
        asserted_present.update(reason.rsplit("/", 1)[-1] for reason in positive)
        asserted_absent.update(
            reason.rsplit("/", 1)[-1]
            for reason in (live.get("absent_diagnostic_reasons") or []))

        if not forward_path.is_file():
            check_findable(name, case, live, {}, undetected, controlled)
            continue

        ahead = load_yaml(forward_path) or {}
        # A typo'd key in a forward block was GRADED — reported as the reason
        # the ticket has not landed, forever. `diagnostic_reason:` (singular)
        # produced `PENDING … declares unhandled expectation key(s)`, and the
        # fixture's own schema error was counted as evidence about the engine.
        unknown = set(ahead) - KNOWN_EXPECT_KEYS
        if unknown:
            raise CorpusError(
                f"{name}: expect-pending.yaml declares unhandled key(s) "
                f"{sorted(unknown)}. In a forward block a typo grades as a "
                f"failure, so it reads as `the ticket has not landed` and never "
                f"stops doing so.")
        # An EMPTY forward block grades zero assertions, so it trivially
        # "holds" — and both runners then report that the ticket has landed.
        # Measured with a 0-byte file and with `{}`: the engine untouched, and
        # a reader told to delete the marker, which converts the regression
        # fixture into a green case asserting nothing.
        #
        # Field by field, matching the Rust harness. A truthiness test passed
        # `diagnostic_reasons: []` — non-empty as YAML, zero assertions when
        # graded — so this loader exited 0 and `verify.py` then announced the
        # ticket had landed. Same for `binding_census: []`, `metrics: []`,
        # `diagnostic_paths: {}` and any key with a null value.
        if not asserts_something(ahead):
            raise CorpusError(
                f"{name}: expect-pending.yaml asserts nothing. An empty forward "
                f"block always holds, which every runner reads as `{ticket} has "
                f"landed`.")
        check_reasons(name, ahead, "expect-pending.yaml", case, emitted, forward)

        # THE BLOCK MUST BE ABOUT ITS TICKET. Two rounds of review found the
        # forward half unpoliced, and the second fix constrained only reason
        # TOKENS — so `backed: 99` was still accepted: false today, false
        # forever, and the case stays pending after its ticket ships with no
        # gate saying so. A forward block has to REQUIRE at least one token
        # the named ticket introduces.
        # A BEHAVIOUR-CHANGE ticket adds no diagnostic, so there is no token to
        # name — #272 makes `TraceTarget.section` accept several headings and
        # rows that were invisible start minting. The forward block must
        # instead re-state the same exactly-graded keys its live block does,
        # with at least one different value: the same measurement, after.
        #
        # This is a SHAPE rule and it does not close the vacuity on its own:
        # `total: 999` alongside the other graded keys restates everything and
        # differs from today, yet is wrong after the fix too. What closes it is
        # FR-065-AC-42's differential, which requires a behaviour-change
        # forward block to HOLD against its control's payload — the control
        # being the repaired tree, which is what the engine should produce once
        # the ticket lands. That check needs an engine, so it lives in the
        # graders; this one only rules out the cheapest evasions.
        if ticket in behaviour_change:
            graded = {k for k in EXACTLY_GRADED if live.get(k) is not None}
            missing = sorted(graded - {k for k in EXACTLY_GRADED if ahead.get(k) is not None})
            if missing:
                raise CorpusError(
                    f"{name}: is pending on the behaviour change {ticket} and its "
                    f"expect-pending.yaml is silent on {missing}, which its "
                    f"expect.yaml asserts. A behaviour-change forward block is the "
                    f"SAME measurement after the fix, so it states the same keys.")
            if not graded:
                raise CorpusError(
                    f"{name}: is pending on the behaviour change {ticket} and its "
                    f"expect.yaml asserts no exactly-graded key, so there is no "
                    f"measurement for the forward block to restate.")
            if all(ahead.get(k) == live.get(k) for k in graded):
                raise CorpusError(
                    f"{name}: its expect-pending.yaml asserts exactly what its "
                    f"expect.yaml does, so {ticket} landing would change nothing "
                    f"it can see.")
            check_findable(name, case, live, ahead, undetected, controlled)
            continue

        claimed = set(ahead.get("diagnostic_reasons") or [])
        claimed |= set(ahead.get("diagnostic_paths") or {})
        claimed |= set(ahead.get("diagnostic_message_contains") or {})
        # A claim may be spelled `reason` or `declaration/reason`; both graders
        # accept the scoped form and resolve it the same way, so the registry
        # lookup has to strip the scope before asking. Without this a fixture
        # that scopes its claim to one declaration — which is the PRECISE way to
        # write it — reads as claiming no token at all (agent-ix/quire-rs#304).
        owned = {r for r in claimed if forward.get(r.rsplit("/", 1)[-1]) == ticket}
        if not owned:
            raise CorpusError(
                f"{name}: expect-pending.yaml requires no token that {ticket} "
                f"introduces. A forward block that is merely FALSE stays false "
                f"after the fix lands — it has to be ABOUT the ticket, or "
                f"nothing ever tells you the fixture went stale.")

        check_findable(name, case, live, ahead, undetected, controlled)

    missing_positive = sorted(emitted - asserted_present)
    missing_negative = sorted(emitted - asserted_absent)
    if missing_positive or missing_negative:
        raise CorpusError(
            "diagnostic reason coverage is incomplete: "
            f"asserted present missing {missing_positive}; "
            f"asserted absent missing {missing_negative}")


def check_regression(name: str, case: dict, forward_path) -> None:
    """A regression case pins a LANDED fix, so it has no forward half.

    No control (there is no defect to be the healthy counterpart OF), not
    findable (nothing is expected to fire on it), and no `pending:` — the ticket
    it names has already shipped.
    """
    if case.get("kind") != "regression":
        return
    if case.get("findable"):
        raise CorpusError(
            f"{name}: a regression case pins behaviour that WORKS — `findable` "
            f"says a finding is expected on this input, and none is.")
    if case.get("control_for"):
        raise CorpusError(
            f"{name}: a regression case has no partner to be the control of.")
    if case.get("pending") or forward_path.is_file():
        raise CorpusError(
            f"{name}: a regression case pins a LANDED ticket; `pending:` and "
            f"expect-pending.yaml both say the opposite.")


def check_findable(
    name: str, case: dict, live: dict, ahead: dict, undetected: set, controlled: set
) -> None:
    """A `findable` case names something that finds it.

    The flag tells a recall-scoring consumer to expect a finding on that input.
    Measured: three `skeptic` fixtures ship BYTE-IDENTICAL live blocks —
    `backed: 1`, `total: 3`, one bound rust symbol — true of any healthy
    three-row corpus, with no diagnostic asserted anywhere. Replacing one's
    entire `input/` tree with another's left every gate green and the cell
    still `covered`, so the fixture was not about its own defect at all.

    Called LAST, from EVERY branch — there are three now: no forward file, a
    behaviour-change ticket, and a token ticket. Sitting inside the pending-only
    branch it ran for six cases out of twenty-nine, and the count of call sites
    is the thing that goes stale, so it is stated as "every branch" rather than
    as a number.
    """
    if case.get("kind") != "failure" or not case.get("findable"):
        return
    # A case with a CONTROL is held to FR-065-AC-42 instead, which is strictly
    # stronger: its assertions must separate its own input from healthy input,
    # whatever form they take. "names a diagnostic" is a proxy for that, and a
    # narrow one — `no-symbol-method-in-the-verification-column` discriminates
    # through `no_symbol_rows` and names no diagnostic at all.
    if (case["id"], case.get("language")) in controlled:
        return
    # `suspicions` counts as naming what detects it (agent-ix/quire-rs#358).
    # It is the channel the whole `skeptic` mode reports on, and leaving it out
    # meant a fixture asserting the exact suspicion the engine raises still read
    # as "requires no finding" — which is the accusation this function exists to
    # make, aimed at a case that had answered it.
    claims = any(
        block.get(key)
        for block in (live, ahead)
        for key in (
            "diagnostic_reasons", "validate_contains", "suspicions",
            "external_observations",
        )
    )
    if claims or (case.get("case") or case["id"]) in undetected:
        return
    raise CorpusError(
        f"{name}: is `findable` and requires no finding, in either block. A "
        f"case claiming its defect is DETECTABLE has to say what detects it, "
        f"or its cell counts as covered for a mode nothing measures. Declare "
        f"it under `known_gaps.findable_but_undetected` if the engine truly "
        f"finds nothing yet.")


class _DuplicateKeyLoader(yaml.SafeLoader):
    """A loader that REFUSES a duplicate mapping key.

    PyYAML silently takes the last value, so a block written twice loses one
    silently. Measured: an `expect.yaml` gained a second
    `diagnostic_message_contains.hollow-denominator:` and five newly-written L3
    fragments were discarded — the file parsed, both readers graded it, and the
    assertions were simply not there. That is precisely the shape this corpus
    exists to catch, arriving inside the corpus itself.
    """


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise CorpusError(
                f"duplicate key {key!r} at line {key_node.start_mark.line + 1} "
                f"of {key_node.start_mark.name} — YAML keeps the LAST and "
                f"discards the first silently, so half the block is asserted by "
                f"nothing")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def load_yaml(path: pathlib.Path):
    """Every YAML this corpus reads, with duplicate keys rejected."""
    return yaml.load(path.read_text(), Loader=_DuplicateKeyLoader)


def asserts_something(block: dict) -> bool:
    """Whether a block asserts anything at all, field by field.

    A block that grades zero assertions trivially passes, which for a forward
    block means every runner reports its ticket as landed.
    """
    # PRESENCE for the keys graded exactly, non-emptiness for the rest —
    # matching the Rust harness field for field. A blanket "not in (None, [],
    # {})" scored `unbacked_rows: []` as asserting nothing, while FR-065-AC-28
    # says an empty list IS an assertion and `grade()` grades it as one. So a
    # forward block of `unbacked_rows: []` was rejected at load by this reader
    # and accepted-and-graded by the other.
    return any(
        block.get(key) is not None if key in EXACTLY_GRADED
        else block.get(key) not in (None, [], {})
        for key in KNOWN_EXPECT_KEYS
    )


# Every key an expectation block may carry. Shared with `verify.py`, which
# grades them; declared here because the LOADER now rejects a typo rather than
# grading one.
# The keys graded EXACTLY — presence is an assertion and an empty list is a
# claim, so these are what a behaviour-change forward block must re-state.
EXACTLY_GRADED = ("backed", "total", "unbacked_rows", "groups", "no_symbol_rows",
                  "untracked_symbols", "external_observations")

KNOWN_EXPECT_KEYS = {
    "backed", "total", "diagnostic_reasons", "absent_diagnostic_reasons",
    "diagnostic_paths", "diagnostic_message_contains", "binding_census",
    "metrics", "no_symbol_rows", "unbacked_rows", "groups",
    "untracked_symbols",
    "validate_contains", "validate_absent",
    # THE SECOND FINDING CHANNEL (agent-ix/quire-rs#358). `coverage` emits on
    # `diagnostics[]` and on `suspicions[]`, and this set named only the first —
    # so the `skeptic` mode family, whose entire subject IS suspicions, could
    # not name its own subject. `vacuous-property-suite` was detected at
    # `src/lib.rs:7` while asserting `backed`/`total`/`binding_census`, true of
    # any healthy three-row tree and byte-identical to two other fixtures.
    "suspicions", "absent_suspicions",
    # Findings/observations produced by a validator other than Quire. The
    # Python verifier executes the named producer; the Quire-only Rust reader
    # parses and explicitly delegates this channel rather than pretending the
    # observation came from `coverage`.
    "external_observations",
}


def check_reasons(
    name: str, block: dict, where: str, case: dict, emitted: set, forward: dict
) -> None:
    """Every reason token a block names is declared, and declared for THIS case."""
    ticket = case.get("pending")
    # A key may be scoped to the declaration that raised it —
    # `declaration/reason`. The TOKEN is what the vocabulary declares, so the
    # prefix is stripped before checking. Scoping exists because two
    # declarations can raise the same reason on one payload and the graders
    # took the first (see `find_diagnostic` in verify.py).
    def token(key: str) -> str:
        return key.rpartition("/")[2]

    present = [token(k) for k in (block.get("diagnostic_reasons") or [])]
    present += [token(k) for k in (block.get("diagnostic_paths") or {})]
    present += [token(k) for k in (block.get("diagnostic_message_contains") or {})]
    absent = [token(k) for k in (block.get("absent_diagnostic_reasons") or [])]

    for reason in present + absent:
        if reason not in emitted and reason not in forward:
            raise CorpusError(
                f"{name}: {where} names `{reason}`, which `corpus.yaml` declares "
                f"neither emitted nor forward. A token in neither list is a typo "
                f"nothing can ever satisfy.")

    for reason in present:
        if reason not in forward:
            # FR-065: a forward block requires ONLY `forward` tokens. Both
            # readers implemented the weaker ticket-match rule and skipped
            # here, so a forward block could require `catch-all-universal` with
            # an unreachable message fragment — false today, false forever, and
            # exactly the shape a PARTIAL landing of a ticket takes.
            if where == "expect-pending.yaml":
                raise CorpusError(
                    f"{name}: expect-pending.yaml requires `{reason}`, which the "
                    f"engine already emits. A forward block states what the "
                    f"ticket ADDS; an already-emitted token there is satisfied "
                    f"or not for reasons that have nothing to do with it.")
            continue
        if where != "expect-pending.yaml":
            raise CorpusError(
                f"{name}: {where} requires `{reason}`, which no engine emits yet "
                f"({forward[reason]}). A live block must hold TODAY; this belongs "
                f"in expect-pending.yaml.")
        if forward[reason] != ticket:
            raise CorpusError(
                f"{name}: is pending on {ticket} and asserts `{reason}`, which "
                f"{forward[reason]} introduces. A fixture cannot wait on one "
                f"ticket while asserting another's behaviour.")

    for reason in absent:
        if reason not in forward:
            continue
        # A CONTROL asserting the absence of a not-yet-emitted token is vacuous
        # today and load-bearing the day the ticket lands — which is what a
        # control is for. A FAILURE case doing it asserts the absence of the
        # very thing it is waiting for, so its live block is guaranteed to
        # break on the fix instead of passing it.
        if case.get("kind") != "control":
            raise CorpusError(
                f"{name}: {where} asserts `{reason}` is ABSENT, but {forward[reason]} "
                f"adds it and this case is not a control. The day that ticket lands "
                f"this block fails — a live block must survive the fix it waits for.")
        if where != "expect.yaml":
            raise CorpusError(
                f"{name}: a control's forward absence claim belongs in expect.yaml; "
                f"a forward block must FAIL today, and this cannot.")


def build(declaration: dict, cases: list[dict]) -> dict:
    """The matrix, computed. `covered` iff a fixture exists for the cell."""
    declared_modes = set(declaration.get("mode_families") or []) | set(
        declaration.get("reporting_modes") or []
    )
    if not declared_modes:
        raise CorpusError("corpus.yaml declares no detection or reporting modes")
    unknown_case_modes = sorted(
        {str(case.get("mode")) for case in cases} - declared_modes
    )
    unknown_inventory_modes = sorted(
        {str(row.get("mode")) for row in declaration.get("inventory") or []}
        - declared_modes
    )
    if unknown_case_modes or unknown_inventory_modes:
        raise CorpusError(
            f"undeclared modes: cases {unknown_case_modes}; inventory "
            f"{unknown_inventory_modes}"
        )
    # A fixture covers a cell only when it binds the ECOSYSTEM declaration.
    # One binding a relaxation variant exercises no ecosystem mode — a corpus
    # whose manifest heading always matches cannot exhibit the section defect
    # at all (candidate census 3,514 TC ids; the section fix realised +83 rows,
    # CR-118) — so it is still a GAP, and the reason names the ticket that will
    # move it (FR-065 CON-3, #285).
    covered_by, on_variant = set(), {}
    for c in cases:
        # Only a FAILURE fixture covers a cell. A control asserts that healthy
        # input stays silent; it measures nothing about the mode. The first
        # version credited either, so deleting the only ecosystem failure
        # fixture and keeping its control left `gap_count` unmoved.
        # A REGRESSION case credits its cell too. It pins behaviour a landed
        # ticket established, and the mode is exercised whether or not the
        # behaviour is currently broken — a cell that reverted to GAP when its
        # defect was FIXED would make `gap_count` count unfixed defects rather
        # than unmeasured modes (FR-065-AC-44).
        if c.get("kind") not in ("failure", "regression"):
            continue
        # The inventory row this fixture claims, by `case:` — falling back to
        # the id only for a fixture whose id IS the inventory name. Both keys
        # were added before, so a control's id leaked into the namespace and
        # could collide with a future row.
        key = (c.get("mode"), c.get("case") or c.get("id"), c.get("language"))
        if c.get("module") == "ecosystem":
            covered_by.add(key)
        else:
            on_variant[key] = (
                c.get("id"), c.get("module"), c.get("relaxation_ticket"),
                c.get("declaration_under_test"),
            )
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
        relaxation = c.get("relaxation_ticket")
        subject = c.get("declaration_under_test")
        if module != "ecosystem" and bool(relaxation) == bool(subject):
            raise CorpusError(
                f"{c.get('id')}: binds variant `{module}` and must declare exactly one "
                f"of `relaxation_ticket` or `declaration_under_test`.")
        if module == "ecosystem" and (relaxation or subject):
            raise CorpusError(
                f"{c.get('id')}: binds the ecosystem module but declares variant metadata.")

    # A cell covered by a PENDING fixture is covered — a case exists and
    # exercises the mode — but the engine demonstrably fails it. Reported
    # separately so `covered` cannot be read as `working`, which is the exact
    # conflation this corpus exists to end.
    pending_cases = {
        (c.get("mode"), c.get("case") or c.get("id"), c.get("language"))
        for c in cases
        if c.get("pending")
    }
    # THE COUNTERS COME FROM THE DECLARATION (FR-065-AC-19). This was
    # `{"covered": 0, "GAP": 0, "out-of-scope": 0}` — a second, compiled-in copy
    # of `bounds_states`, so adding a state to `corpus.yaml` did not add a
    # counter and a cell in it would have raised `KeyError` from the middle of
    # the loop rather than being counted. Derived, a new state is counted, is
    # included in the sum invariant, and is reported, with no edit here.
    declared_states = list(declaration.get("bounds_states") or [])
    if not declared_states:
        raise CorpusError(
            "corpus.yaml declares no `bounds_states`, so there is no vocabulary "
            "to grade cells into (FR-065-AC-19)")
    matrix, counts = [], {state: 0 for state in declared_states}
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
                fixture, module, ticket, subject = on_variant[(
                    row["mode"], row["case"], language)]
                if subject:
                    cells[language] = {
                        "state": "out-of-scope",
                        "reason": f"`{fixture}` tests variant declaration `{module}`: {subject}",
                    }
                else:
                    cells[language] = {
                        "state": "GAP",
                        "reason": f"`{fixture}` ships but binds `{module}` rather than the "
                                  f"ecosystem declaration, so it exercises no ecosystem "
                                  f"mode ({ticket})",
                    }
            else:
                cells[language] = {"state": "GAP"}
            state = cells[language]["state"]
            if state not in counts:
                raise CorpusError(
                    f"{row['case']}/{language}: graded `{state}`, which "
                    f"`corpus.yaml`'s `bounds_states` does not declare "
                    f"{declared_states} (FR-065-AC-19)")
            counts[state] += 1
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
    # Summed over the DECLARED states, not over three names written here. A
    # state added to `corpus.yaml` and not to this sum would have made the
    # invariant fire on a corpus that was fine.
    graded = sum(counts[state] for state in declared_states)
    if graded != declared:
        breakdown = ", ".join(f"{state} {counts[state]}" for state in declared_states)
        raise CorpusError(
            f"the sum invariant does not hold: the inventory declares {declared} "
            f"cells and {graded} were graded ({breakdown}). A cell is in no "
            f"state, or in two."
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


def require_complete(bounds: dict) -> None:
    """Reject every applicable inventory cell that has no corpus case.

    The ordinary report keeps GAP as a useful authoring state. CI uses this
    stricter policy: a declared applicable language is either covered by a
    case or explicitly out of scope with a reason. Otherwise a newly added row
    can make the matrix honestly say GAP while the gate still passes.
    """
    gaps = [
        f"{row['mode']}/{row['case']}/{language}"
        for row in bounds["matrix"]
        for language, cell in row["cells"].items()
        if cell["state"] == "GAP"
    ]
    if gaps:
        raise CorpusError(
            f"{len(gaps)} applicable mode-language cell(s) have no case: "
            + ", ".join(gaps)
            + ". Add the case, or mark the cell out-of-scope with a non-empty "
              "reason when the mode genuinely cannot occur in that language."
        )


# A count published in prose, tagged so it can be checked against the tree.
#
# WHY THIS EXISTS. Six figures in `corpus.yaml`, `README.md` and a self-test
# docstring described a corpus they had drifted from: "all 77 fixtures" against
# 81, "14 of the 35 (case, control) pairs" against 13 of 39, "41 failure
# fixtures, of which 34 are controlled" against 42 of 38. Every one of them was
# true when written. None was under a gate, and the file that teaches a fixture
# author how the corpus works was teaching them from stale numbers.
#
# The rule this corpus already applies to its own cells — a stored count can go
# stale, a derived one cannot disagree with the tree it describes — applied to
# its prose. Tag the number, and the tag is checked:
#
#     # <derived:fixtures=81>
#
# Deliberately an explicit marker rather than a regex over prose. A regex
# guessing which "41" in a paragraph is a fixture count produces false failures
# on unrelated sentences, and a gate that cries wolf is a gate people delete.
DERIVED_MARKER = re.compile(r"<derived:([a-z_]+)=(\d+)>")

# Files whose prose carries tagged counts. Not a glob: a file added here is a
# deliberate claim that its numbers are checked, and a glob would silently start
# and stop covering files as the tree changed.
COUNTED_FILES = ("corpus.yaml", "README.md", "scripts/parity_selftest.py")


def derived_counts(cases: list[dict]) -> dict[str, int]:
    """The structural counts the tree supports, for `check_published_counts`.

    STRUCTURAL ONLY. `pairs differing in total` is not here and cannot be: it
    needs a payload from every control, which means running the engine, which
    this loader deliberately does not do. That figure stays prose and says so.
    """
    detection = [c for c in cases if c.get("mode") != "reporting"]
    failures = [c for c in detection if c.get("kind") == "failure"]
    controlled = controls_by_case(detection)
    return {
        "fixtures": len(cases),
        "failure_fixtures": len(failures),
        "controlled_failures": sum(
            1 for c in failures if (c["id"], c.get("language")) in controlled
        ),
        "pairs": sum(len(v) for v in controlled.values()),
    }


def check_published_counts(cases: list[dict]) -> None:
    """Every tagged count in the docs equals what the tree yields."""
    counts = derived_counts(cases)
    wrong = []
    for rel in COUNTED_FILES:
        path = ROOT / rel
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            for name, written in DERIVED_MARKER.findall(line):
                if name not in counts:
                    wrong.append(
                        f"{rel}:{number}: `{name}` is not a derived count; "
                        f"known: {', '.join(sorted(counts))}")
                elif int(written) != counts[name]:
                    wrong.append(
                        f"{rel}:{number}: publishes {name}={written}, tree has "
                        f"{counts[name]}")
    if wrong:
        raise CorpusError(
            "published counts disagree with the tree:\n  " + "\n  ".join(wrong))


def main() -> int:
    try:
        declaration = load_declaration()
        cases = discover()
        bounds = build(declaration, cases)
        check_published_counts(cases)
        if "--require-complete" in sys.argv:
            require_complete(bounds)
    except CorpusError as error:
        print(f"corpus: {error}", file=sys.stderr)
        return 1

    if "--json" in sys.argv:
        # `_declared` is loader scaffolding — the declaration as written, kept
        # so a check can ask whether the AUTHOR wrote a field rather than
        # whether it was derived. It is not part of the payload a runner reads,
        # and leaving it in duplicated every declared field in a nested copy.
        public = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cases]
        print(json.dumps({"bounds": bounds, "cases": public}, indent=1))
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
