//! Opt-in stage timings on stderr; the protocol and normal runs stay untouched.
use std::sync::OnceLock;
use std::time::Instant;

pub struct Span {
    name: &'static str,
    start: Option<Instant>,
}

impl Span {
    pub fn new(name: &'static str) -> Self {
        static ENABLED: OnceLock<bool> = OnceLock::new();
        let enabled =
            *ENABLED.get_or_init(|| std::env::var("BRUSTER_TRACE_PERF").as_deref() == Ok("1"));
        Self {
            name,
            start: enabled.then(Instant::now),
        }
    }
}

impl Drop for Span {
    fn drop(&mut self) {
        if let Some(start) = self.start {
            eprintln!(
                "bruster timing: {} {:.3} ms",
                self.name,
                start.elapsed().as_secs_f64() * 1000.0
            );
        }
    }
}
