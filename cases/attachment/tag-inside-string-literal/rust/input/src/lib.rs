#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn real() {
        assert!(true);
    }

    #[ignore = "// TC-002: not a tag"]
    #[test]
    fn carries_an_example() {
        assert!(true);
    }
}
