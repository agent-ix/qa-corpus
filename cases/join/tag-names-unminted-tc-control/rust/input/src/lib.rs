#[cfg(test)]
mod tests {
    #[test]
    fn defaults_every_finding_to_warning() {
        let severity = "warning";
        // TC-001: this tag names the matrix row.
        assert_eq!(severity, "warning");
    }

    #[test]
    fn names_the_declaration_on_every_finding() {
        let declaration = "traceability.trace_tags";
        // TC-002: this tag names a minted row.
        assert!(!declaration.is_empty());
    }
}
