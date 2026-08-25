# The corpus is data. These targets read it; none of them write a case.

QUIRE ?= ../quire-cli/target/debug/quire
CASES := $(shell find cases -mindepth 2 -maxdepth 2 -type d 2>/dev/null | sort)

.PHONY: help
help:
	@echo "make verify              run every case by its own recorded invocation"
	@echo "make bounds              the derived matrix, gap_count, and pending list"
	@echo "make new-case MODE=.. CASE=.. LANG=..  scaffold a runnable skeleton"
	@echo "make schema-selftest     prove the case-metadata gate can fail"
	@echo "make ci                  schema-selftest + bounds + verify"

# Every case, by the exact string in its own case.yaml. A documented command
# that does not work fails the corpus rather than misleading a reader.
.PHONY: verify
verify:
	@QUIRE="$(QUIRE)" python3 verify.py

# Derived, never stored: a count that cannot disagree with the tree.
.PHONY: bounds
bounds:
	@python3 bounds.py

# A gate never observed to reject anything is indistinguishable from one that
# cannot. Six mutations, each requiring `bounds.py` to fail NAMING the defect,
# plus an unmutated control so the suite cannot pass vacuously (#336).
.PHONY: schema-selftest
schema-selftest:
	@python3 scripts/schema_selftest.py

.PHONY: ci
ci: schema-selftest bounds verify

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
