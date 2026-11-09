//! PRODUCTION code plus its one test. The production function carries a
//! requirement citation as a comment: a production function binds no trace id
//! and the comment is prose, so the advisory names the function and its kind.

// TC-001: Warning default.
pub fn normalize_severity(severity: Option<&str>) -> &str {
    severity.unwrap_or("warning")
}

#[cfg(test)]
mod tests {
    use super::normalize_severity;

    #[trace("TC-002")]
    #[test]
    fn names_the_declaration_on_every_finding() {
        assert_eq!(normalize_severity(None), "warning");
    }
}
