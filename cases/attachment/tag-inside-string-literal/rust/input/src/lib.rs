#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn real() {
        assert!(true);
    }

    #[test]
    fn carries_an_example() {
        // Tag-shaped data is not a tag and not a misplaced citation.
        let example = "Trace: TC-002";
        assert!(example.contains("Trace"));
    }
}
