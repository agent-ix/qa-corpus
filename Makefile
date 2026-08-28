# The corpus is data. These targets read it; none of them write a case.

# CARGO_TARGET_DIR MOVES THE ARTIFACT AND THIS DEFAULT DID NOT FOLLOW IT. With
# it set, `cargo build` in quire-cli writes to `$CARGO_TARGET_DIR/debug/quire`
# and `../quire-cli/target/` keeps whatever was there before the variable was
# set. Measured: the in-repo path held a four-day-old binary reporting
# `quire 0.23.0` while the real build reported `quire 0.30.2 (engine 00644b7)` —
# one engine apart, and the default pointed at the stale one. Caught by
# quire-cli#68's provenance guard refusing a binary that cannot name its engine,
# which is the case for refusing rather than warning. Same defect and same fix
# as `agent-ix/quoin`'s `bench-tier1` default.
CORPUS_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
QUIRE ?= $(shell command -v quire 2>/dev/null)
QUOIN ?= $(shell command -v quoin 2>/dev/null)
CASES := $(shell find cases -mindepth 2 -maxdepth 2 -type d 2>/dev/null | sort)

.PHONY: help
help:
	@echo "make verify              run every case by its own recorded invocation"
	@echo "make verify-reporting    run the reporter cases over static records"
	@echo "make bounds              derive the matrix and reject every applicable GAP"
	@echo "make new-case MODE=.. CASE=.. LANG=..  scaffold a runnable skeleton"
	@echo "make schema-selftest     prove the case-metadata gate can fail"
	@echo "make parity-selftest     prove the AC-42 differential can fail"
	@echo "make measurement-selftest prove both active plans have derived output"
	@echo "make measurement-collection OUTPUT=... export a governed collection"
	@echo "make duplicate-census    reject unexplained fixture-copy drift"
	@echo "make external-channel    validate exact non-Quire witness contract"
	@echo "make ci                  schema-selftest + bounds + verify + parity-selftest"

# Every case, by the exact string in its own case.yaml. A documented command
# that does not work fails the corpus rather than misleading a reader.
.PHONY: verify
verify:
	@QUIRE="$(QUIRE)" QUOIN="$(QUOIN)" python3 verify.py

.PHONY: verify-reporting
verify-reporting:
	@QUOIN="$(QUOIN)" python3 scripts/verify_reporting.py

# Derived, never stored: a count that cannot disagree with the tree.
.PHONY: bounds
bounds:
	@python3 bounds.py --require-complete

# A gate never observed to reject anything is indistinguishable from one that
# cannot. Six mutations, each requiring `bounds.py` to fail NAMING the defect,
# plus an unmutated control so the suite cannot pass vacuously (#336).
.PHONY: schema-selftest
schema-selftest:
	@python3 scripts/schema_selftest.py

# The same argument for the AC-42 differential, which until #337 existed only in
# the Rust harness: blind a fixture down to one incidental scalar and `verify.py`
# reported `mismatches: 0`, exit 0, on a corpus `cargo test` rejected. Runs LAST
# because it copies the corpus four times and runs the whole of `verify.py` over
# each, and a plain `verify` failure should be read before this one.
.PHONY: parity-selftest
parity-selftest:
	@QUIRE="$(QUIRE)" QUOIN="$(QUOIN)" python3 scripts/parity_selftest.py

.PHONY: measurement-selftest
measurement-selftest:
	@python3 scripts/measurement_selftest.py

.PHONY: measurement-collection
measurement-collection:
	@python3 scripts/export_measurements.py $(if $(OUTPUT),--output "$(OUTPUT)",)

.PHONY: duplicate-census
duplicate-census:
	@python3 scripts/duplicate_census.py

.PHONY: external-channel
external-channel:
	@python3 scripts/external_channel_selftest.py

.PHONY: ci
ci: schema-selftest duplicate-census external-channel bounds verify verify-reporting measurement-selftest parity-selftest

# Scaffold. The first thing an author sees is a skeleton that runs, not a
# schema document — which is the difference between a corpus that grows and one
# that stays the size somebody seeded it at.
MODE ?=
CASE ?=
LANG ?= rust
KIND ?= failure
MODULE ?= ecosystem

.PHONY: new-case
new-case:
	@test -n "$(MODE)" || { echo "MODE= is required (see mode_families in corpus.yaml)"; exit 1; }
	@test -n "$(CASE)" || { echo "CASE= is required"; exit 1; }
	@python3 scripts/new_case.py \
		--mode "$(MODE)" --case "$(CASE)" --language "$(LANG)" \
		--kind "$(KIND)" --module "$(MODULE)"
