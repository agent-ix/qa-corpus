#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn real() {
        assert!(true);
    }

    #[trace("TC-002")]
    #[ignore = "an ordinary reason"]
    #[test]
    fn carries_an_example() {
        assert!(true);
    }
}
