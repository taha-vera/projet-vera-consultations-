pub struct Session {
    pub id: u64,
}

impl Session {
    pub fn new(id: u64) -> Self {
        Session { id }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn session_has_id() {
        let s = Session::new(42);
        assert_eq!(s.id, 42);
    }
}
