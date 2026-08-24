//! The shape is taken from identity/tests/test_tenant_auth_policy.py:195, in
//! Rust: a doc comment carrying an id an `## Invariants` table declares.
//!
//! The tag BINDS. `rust-doc-comment-id` admits the sub-id segment, the
//! enclosing symbol is a test function, and the census counts it as bound. What
//! it binds to is an id no target mints, because `## Invariants` is a heading
//! NEITHER module declares: not in the ISO `FR` skeleton, not in either
//! manifest. 15 repositories author it anyway, 129 rows, and its table is the
//! `Constraints` table under a different name.
//!
//! MIXED on purpose — one undeclared-section id beside one minted test-case id.

#[cfg(test)]
mod tests {
    /// FR-001-INV-1: the declared severity is the one carried.
    #[test]
    fn carries_the_declared_severity() {
        let severity = "warning";
        assert_eq!(severity, "warning");
    }

    /// TC-002: the row's own minted id, which the declaration can join.
    #[test]
    fn names_the_declaration_on_every_finding() {
        let declaration = "traceability.trace_tags";
        assert!(!declaration.is_empty());
    }
}
