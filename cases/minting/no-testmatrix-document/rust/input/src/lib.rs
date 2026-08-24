//! Three real, correctly-tagged tests, one per matrix row. The tags are not
//! the defect: all three bind. Two of the rows they answer for are invisible
//! to the declaration, so two of these symbols back nothing at all.

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn covers_the_first_criterion() {
        assert_eq!(1 + 1, 2);
    }

    #[trace("TC-002")]
    #[test]
    fn covers_the_second_criterion() {
        assert_eq!(2 + 2, 4);
    }

    #[trace("TC-003")]
    #[test]
    fn covers_the_third_criterion() {
        assert_eq!(3 + 3, 6);
    }
}
