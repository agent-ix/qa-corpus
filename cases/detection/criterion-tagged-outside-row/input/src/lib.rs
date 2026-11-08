#[cfg(test)]
mod tests {
    #[trace("TC-002", "FR-001-AC-1")]
    #[test]
    fn incorrectly_pairs_the_second_test_case_with_the_first_criterion() {}

    #[trace("TC-003", "FR-001-AC-3")]
    #[test]
    fn backs_only_one_criterion_on_a_shared_matrix_row() {}
}
