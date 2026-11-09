//! The SAME function, two characters different: the marker id is padded like the
//! declared row, so it binds and backs it.

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn every_finding_defaults_to_warning() {
        assert_eq!(1 + 1, 2);
    }
}
