//! The control for `range-in-trace-tag`: each id tagged separately.

#[cfg(test)]
mod tests {
    #[trace("FR-001-AC-1")]
    #[test]
    fn covers_ac1() {
        let _ = 1;
    }

    #[trace("FR-001-AC-2")]
    #[test]
    fn covers_ac2() {
        let _ = 1;
    }
}
