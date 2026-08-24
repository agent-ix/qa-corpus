//! The SAME file with ONE line changed: the tag above `normalize_severity` is
//! written in the form the production channel accepts.
//!
//! This is the harder control on purpose. The id-shaped annotation is still
//! sitting above production code — what changed is that it now names the
//! relation the symbol kind can carry. A detector written as "any declared
//! trace-id form inside a symbol that does not bind trace ids" would fire here
//! too, and be wrong.

/// Implements: FR-001-AC-1
pub fn normalize_severity(severity: Option<&str>) -> &str {
    severity.unwrap_or("warning")
}

#[cfg(test)]
mod tests {
    use super::normalize_severity;

    // TC-002: on the test, which registers an evidence symbol. Unchanged.
    #[test]
    fn names_the_declaration_on_every_finding() {
        assert_eq!(normalize_severity(None), "warning");
    }
}
