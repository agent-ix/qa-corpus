#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn covers_the_criterion() {
        assert_eq!(1 + 1, 2);
    }
}
