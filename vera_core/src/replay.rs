use std::collections::HashSet;

pub struct ReplayProtector {
    seen: HashSet<Vec<u8>>,
}

impl ReplayProtector {
    pub fn new() -> Self {
        Self { seen: HashSet::new() }
    }

    pub fn check(&mut self, tag: Vec<u8>) -> bool {
        if self.seen.contains(&tag) {
            false
        } else {
            self.seen.insert(tag);
            true
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn replay_accepts_first_time() {
        let mut r = ReplayProtector::new();
        assert!(r.check(vec![1,2,3]));
    }

    #[test]
    fn replay_rejects_duplicate() {
        let mut r = ReplayProtector::new();
        r.check(vec![9,9,9]);
        assert!(!r.check(vec![9,9,9]));
    }
}
