//! The SAME file with FOUR CHARACTERS added to one tag: the bare requirement id
//! becomes the criterion id the declaration mints. Nothing else differs — same
//! two tests, same comment form, same position in the body, same sibling tag.
//!
//! That is the whole repair, and it is why the pair is worth having: the failure
//! case is not a missing tag, a misplaced tag or an unreadable tag. It is a tag
//! the engine reads perfectly and joins to nothing.

#[cfg(test)]
mod tests {
    #[test]
    fn defaults_every_finding_to_warning() {
        let severity = "warning";
        // FR-001-AC-1: every finding defaults to warning.
        assert_eq!(severity, "warning");
    }

    #[test]
    fn names_the_declaration_on_every_finding() {
        let declaration = "traceability.trace_tags";
        // TC-002: the row's own minted id, which the declaration can join.
        assert!(!declaration.is_empty());
    }
}
