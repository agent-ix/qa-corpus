//! The SAME function, two characters different: `TC-001` where its partner says
//! `TC-1`. The id matches the declared row, so it binds and backs it.

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn every_finding_defaults_to_warning() {
        assert_eq!(1 + 1, 2);
    }
}
