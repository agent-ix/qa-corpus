//! seeded

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn covers() {
        assert_eq!(parse(), 1);
    }
}
