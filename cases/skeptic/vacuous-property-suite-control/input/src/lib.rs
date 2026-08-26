//! seeded

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn covers() {
        let v = parse();
        assert_eq!(v, Some(1));
    }
}
