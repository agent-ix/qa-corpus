//! The SAME function, two characters different: `tc_001_` where its partner
//! says `tc_1_`. The id minted matches the declared row, so it binds and backs
//! it.
//!
//! This half also PINS CR-034 — the change that made the underscore spelling
//! bind at all — which nothing else in the corpus does.

#[cfg(test)]
mod tests {
    #[test]
    fn tc_001_every_finding_defaults_to_warning() {
        assert_eq!(1 + 1, 2);
    }
}
