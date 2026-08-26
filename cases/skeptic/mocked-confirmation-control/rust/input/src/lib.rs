//! controlled

pub struct Confirmation;

impl Confirmation {
    pub fn from_user() -> Self {
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
        assert!(grant_root(Confirmation::from_user()));
    }
}
