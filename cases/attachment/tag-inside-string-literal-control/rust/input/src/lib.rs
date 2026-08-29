#[cfg(test)]
mod tests {
    #[test]
    fn real() {
        // Trace: TC-001
        assert!(true);
    }

    #[test]
    fn carries_an_example() {
        // Trace: TC-002
        let example = "an ordinary fixture string";
        assert!(example.contains("ordinary"));
    }
}
