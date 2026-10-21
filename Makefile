# The corpus is data. These targets read it; none of them write a case.

# CARGO_TARGET_DIR MOVES THE ARTIFACT AND THIS DEFAULT DID NOT FOLLOW IT. With
# it set, `cargo build` in quire-cli writes to `$CARGO_TARGET_DIR/debug/quire`
# and `../quire-cli/target/` keeps whatever was there before the variable was
# set, so a default pointing at the in-repo path can name a stale binary. Caught by
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
	@echo "make compatibility-corpus-selftest prove checks select the recorded producer revisions"
	@echo "make measurement-collection OUTPUT=... VERIFICATION_STACK=... export a governed collection"
	@echo "make external-channel    validate exact non-Quire witness contract"
	@echo "make ci                  run the corpus and all verification selftests"

# Every case, by the exact string in its own case.yaml. A documented command
# that does not work fails the corpus rather than misleading a reader.
.PHONY: verify
verify:
	@QUIRE="$(QUIRE)" QUOIN="$(QUOIN)" cargo run --quiet -- verify

.PHONY: verify-reporting
verify-reporting:
	@QUOIN="$(QUOIN)" cargo run --quiet -- verify-reporting

# Derived, never stored: a count that cannot disagree with the tree.
.PHONY: bounds
bounds:
	@cargo run --quiet -- bounds --require-complete

# Exercise metadata admission, derived bounds, and the case scaffolder.
.PHONY: schema-selftest
schema-selftest:
	@cargo test --quiet --lib corpus::tests
	@cargo test --quiet --lib bounds::tests
	@cargo test --quiet --lib scaffold::tests

# Exercise differential grading, witness-channel restrictions, and input shapes.
.PHONY: parity-selftest
parity-selftest:
	@cargo test --quiet --lib verify::tests

.PHONY: measurement-selftest
measurement-selftest:
	@cargo test --quiet --lib measurements::tests

.PHONY: measurement-collection
measurement-collection:
	@test -n "$(VERIFICATION_STACK)" || { echo "VERIFICATION_STACK= is required"; exit 1; }
	@cargo run --quiet -- measurement-collection $(if $(OUTPUT),--output "$(OUTPUT)",) --verification-stack "$(VERIFICATION_STACK)"

.PHONY: external-channel
external-channel:
	@cargo run --quiet -- external-channel

.PHONY: compatibility-corpus-selftest
compatibility-corpus-selftest:
	@python3 scripts/compatibility_corpus_selftest.py

.PHONY: ci
ci: schema-selftest external-channel compatibility-corpus-selftest bounds verify verify-reporting measurement-selftest parity-selftest

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
	@cargo run --quiet -- new-case \
		--mode "$(MODE)" --case "$(CASE)" --language "$(LANG)" \
		--kind "$(KIND)" --module "$(MODULE)"
