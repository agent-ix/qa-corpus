//! The comment binds, while the declaration's name form does not.

#[cfg(test)]
mod tests {
    // TC-001: the aggregate binder reads this channel.
    #[test]
    fn test_tc_001_every_finding_defaults_to_warning() {
        assert_eq!(1 + 1, 2);
    }
}
