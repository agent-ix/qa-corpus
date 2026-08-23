//! An integration test, in `tests/` — not `src/`.
//!
//! The old harness materialised every case under a hardcoded `src/`, so a
//! repository whose evidence lives in `tests/` could not be expressed at all.
//! This file is the proof that limit is retired: the tag below is bound from a
//! directory the previous corpus had no way to create.

#[trace("TC-001")]
#[test]
fn covers_the_criterion_from_a_tests_directory() {
    assert_eq!(1 + 1, 2);
}
