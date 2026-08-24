//! The trace id is in the FUNCTION NAME and nowhere else — no `#[trace]`
//! attribute, no `Trace:` line, no comment marker.
//!
//! `rust-test-name-id` reads it: `\bfn (?i:tc)_?(\d+)_` with `id_format:
//! 'TC-{1}'`. This fixture PINS that, because CR-034 is the change that made
//! the underscore spelling bind and nothing else in the corpus would notice it
//! regressing.

#[cfg(test)]
mod tests {
    #[test]
    fn tc_1_every_finding_defaults_to_warning() {
        assert_eq!(1 + 1, 2);
    }
}
