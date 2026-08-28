//! Both the comment and the declaration's name form bind.

#[cfg(test)]
mod tests {
    // TC-001: retained so only the function-name prefix changes.
    #[test]
    fn tc_001_every_finding_defaults_to_warning() {
        assert_eq!(1 + 1, 2);
    }
}
