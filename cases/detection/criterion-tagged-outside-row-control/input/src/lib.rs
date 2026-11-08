#[cfg(test)]
mod tests {
    #[trace("TC-001", "FR-001-AC-1")]
    #[test]
    fn pairs_the_test_case_with_its_criterion() {}

    #[trace("TC-002", "FR-001-AC-2")]
    #[test]
    fn backs_the_second_criterion_on_its_row() {}

    #[trace("TC-003", "FR-001-AC-2", "FR-001-AC-3")]
    #[test]
    fn backs_both_criteria_on_the_shared_row() {}
}
