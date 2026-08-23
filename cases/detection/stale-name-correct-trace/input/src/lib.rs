//! fixture

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn tc_999_renamed_but_still_correct() {
        let _ = 1;
    }
}
