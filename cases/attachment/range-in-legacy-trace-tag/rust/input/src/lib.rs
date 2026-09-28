//! A range in a legacy `Trace:` line binds no id, not even its left endpoint (CR-187).

#[cfg(test)]
mod tests {
    // Trace: FR-001-AC-1..FR-001-AC-2
    #[test]
    fn covers_the_range() {
        let _ = 1;
    }
}
