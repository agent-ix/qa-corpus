//! The id is unpadded in a canonical marker and the matrix row declares it
//! padded: `TC-1` against `TC-001`.

#[cfg(test)]
mod tests {
    #[trace("TC-1")]
    #[test]
    fn every_finding_defaults_to_warning() {
        assert_eq!(1 + 1, 2);
    }
}
