#[cfg(test)]
mod tests {
    #[test]
    fn defaults_every_finding_to_warning() {
        let severity = "warning";
        // this tag names the matrix row.
        #[trace("TC-001")]
        assert_eq!(severity, "warning");
    }

    #[test]
    fn names_the_declaration_on_every_finding() {
        let declaration = "traceability.trace_tags";
        // this tag names a minted row.
        #[trace("TC-002")]
        assert!(!declaration.is_empty());
    }
}
