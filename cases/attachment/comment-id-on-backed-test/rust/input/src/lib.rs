#[cfg(test)]
mod tests {
    // TC-001: still a comment, though the marker below names the same id.
    #[trace("TC-001")]
    #[test]
    fn backed_and_commented() {
        assert_eq!(1 + 1, 2);
    }
}
