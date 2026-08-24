//! seeded

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn covers() {
        if let Some(v) = parse() {
            assert_eq!(v, 1);
        }
    }
}
