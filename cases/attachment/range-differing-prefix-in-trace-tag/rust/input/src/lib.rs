//! A range across two requirements' ids binds no id at all (CR-187).

#[cfg(test)]
mod tests {
    #[trace("FR-001-AC-2..FR-002-AC-1")]
    #[test]
    fn covers_the_range() {
        let _ = 1;
    }
}
