#[cfg(test)]
mod tests {
    #[test]
    fn real() {
        // Trace: TC-001
        assert!(true);
    }

    #[test]
    fn carries_an_example() {
        // Tag-shaped data must not bind this test to TC-002.
        let example = "Trace: TC-002";
        assert!(example.contains("Trace"));
    }
}
