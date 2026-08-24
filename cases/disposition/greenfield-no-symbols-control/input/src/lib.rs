//! One evidence symbol, so the denominator is read rather than empty.

#[cfg(test)]
mod tests {
    #[trace("TC-001")]
    #[test]
    fn covers_the_criterion() {
        let _ = 1;
    }
}
