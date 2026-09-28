//! The control for `range-differing-prefix-in-trace-tag`: each id tagged separately.

#[cfg(test)]
mod tests {
    #[trace("FR-001-AC-2")]
    #[test]
    fn covers_fr001_ac2() {
        let _ = 1;
    }

    #[trace("FR-002-AC-1")]
    #[test]
    fn covers_fr002_ac1() {
        let _ = 1;
    }
}
