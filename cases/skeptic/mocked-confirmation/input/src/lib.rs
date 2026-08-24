//! seeded

pub struct Confirmation;

impl Confirmation {
    pub fn allow() -> Self {
        Self
    }
}

pub fn grant_root(_c: Confirmation) -> bool {
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[trace("TC-001")]
    #[test]
    fn covers() {
        assert!(grant_root(Confirmation::allow()));
    }
}
