#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn real() {
        assert!(true);
    }

    #[trace("TC-002")]
    #[test]
    fn carries_an_example() {
        let example = "an ordinary fixture string";
        assert!(example.contains("ordinary"));
    }
}
