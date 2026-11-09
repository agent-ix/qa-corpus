#[cfg(test)]
mod tests {
    #[trace("TC-002")]
    #[test]
    fn marked() {
        assert_eq!(2 + 2, 4);
    }

    // TC-001: this comment names the row, but only a marker binds.
    #[test]
    fn commented() {
        assert_eq!(1 + 1, 2);
    }
}
