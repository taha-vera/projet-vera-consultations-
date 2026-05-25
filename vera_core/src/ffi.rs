#[no_mangle]
pub extern "C" fn vera_init() -> i32 {
    0
}

#[cfg(test)]
mod tests {
    #[test]
    fn ffi_init_returns_zero() {
        assert_eq!(crate::ffi::vera_init(), 0);
    }
}
