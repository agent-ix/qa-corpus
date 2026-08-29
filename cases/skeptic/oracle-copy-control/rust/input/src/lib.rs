pub fn is_contained(path: &str) -> bool {
    !path.starts_with('/') && !path.contains("..") && !path.contains('\0')
}

#[cfg(test)]
mod tests {
    use super::*;

    #[trace("TC-001")]
    #[test]
    fn covers() {
        let path = "a/b";
        let expected = true;
        assert_eq!(is_contained(path), expected);
    }
}
