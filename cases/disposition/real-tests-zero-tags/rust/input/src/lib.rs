//! Two real `#[test]` functions and not one trace tag anywhere in the tree. The
//! shape is taken from build-chain/src/core/plugin.rs:50 — a `#[cfg(test)] mod
//! tests` of six tests, none of them tagged. That repository is one of 150 with
//! test files and no binding tag at all.
//!
//! NOT MIXED, deliberately. Every other attachment and join fixture in this
//! corpus pairs a defective tag with a correct one, because a degenerate
//! all-defective tree fires `no-symbol-bound` for a reason that holds in no real
//! repository. Here the degenerate tree IS the population: the authoring is
//! absent, that is the whole disposition, and `no-symbol-bound` firing is the
//! correct answer rather than an artefact of the fixture.
//!
//! No id is written anywhere in this file on purpose.

#[cfg(test)]
mod tests {
    #[test]
    fn defaults_every_finding_to_warning() {
        let severity = "warning";
        assert_eq!(severity, "warning");
    }

    #[test]
    fn names_the_declaration_on_every_finding() {
        let declaration = "traceability.trace_tags";
        assert!(!declaration.is_empty());
    }
}
