//! PRODUCTION code plus its one test. The shape is taken from
//! quire-rs/src/corpus/validate.rs:253 — a `//` comment carrying a requirement
//! id inside a `pub fn`, describing what the code below it does.
//!
//! `normalize_severity` is a plain function, so `SymbolKind::Function`. CR-061
//! made `binds_trace_ids()` false for that kind, so the tag on it is not even a
//! binding CANDIDATE — it is missing from the census denominator rather than
//! counted as a miss. The `implements` channel needs the literal `Implements:`
//! keyword, which this comment does not carry.
//!
//! No id is written anywhere in this header on purpose. A tag is the only thing
//! in this file that names one.

// TC-001: Warning default.
pub fn normalize_severity(severity: Option<&str>) -> &str {
    severity.unwrap_or("warning")
}

#[cfg(test)]
mod tests {
    use super::normalize_severity;

    // TC-002: on the test, which registers an evidence symbol. This is the
    // correct half of the MIXED pair, and it is what makes the census read a
    // clean 1 of 1.
    #[test]
    fn names_the_declaration_on_every_finding() {
        assert_eq!(normalize_severity(None), "warning");
    }
}
