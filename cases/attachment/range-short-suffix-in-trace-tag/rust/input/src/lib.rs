//! A short-suffix range inside a trace tag binds no id at all (CR-187).

#[cfg(test)]
mod tests {
    #[trace("FR-001-AC-1..2")]
    #[test]
    fn covers_the_range() {
        let _ = 1;
    }
}
