#[cfg(test)]
mod tests {
    #[trace("TC-002")]
    #[test]
    fn marked() {
        assert_eq!(2 + 2, 4);
    }

    #[trace("TC-001")]
    #[test]
    fn commented() {
        assert_eq!(1 + 1, 2);
    }
}
