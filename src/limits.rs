//! Admission covers stdin events as well as work retained by the browser.
//! A permit survives cancellation until its queued event/native callback drops.
use std::collections::HashMap;
use std::io::{self, BufRead};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock};

pub const LINE_BYTES: usize = 8 * 1024 * 1024;
const REQUESTS: usize = 128;
const REQUEST_BYTES: usize = 64 * 1024 * 1024;
pub const UPLOAD_BYTES: u64 = 16 * 1024 * 1024;

static USAGE: Mutex<(usize, usize)> = Mutex::new((0, 0));
static ACTIVE: OnceLock<Mutex<HashMap<u64, Arc<Permit>>>> = OnceLock::new();
fn active() -> &'static Mutex<HashMap<u64, Arc<Permit>>> {
    ACTIVE.get_or_init(Default::default)
}

#[derive(Debug)]
pub struct Permit {
    bytes: AtomicUsize,
    cancelled: AtomicBool,
}

impl Drop for Permit {
    fn drop(&mut self) {
        let mut usage = USAGE.lock().unwrap();
        usage.0 -= 1;
        usage.1 -= self.bytes.load(Ordering::Relaxed);
    }
}

pub fn admit(id: u64, bytes: usize) -> Result<Arc<Permit>, &'static str> {
    let mut requests = active().lock().unwrap();
    if requests.contains_key(&id) {
        return Err("request id is already in flight");
    }
    let mut usage = USAGE.lock().unwrap();
    if usage.0 >= REQUESTS || bytes > REQUEST_BYTES.saturating_sub(usage.1) {
        return Err("request capacity exceeded; wait for outstanding requests to finish");
    }
    let permit = Arc::new(Permit {
        bytes: AtomicUsize::new(bytes),
        cancelled: AtomicBool::new(false),
    });
    usage.0 += 1;
    usage.1 += bytes;
    requests.insert(id, permit.clone());
    Ok(permit)
}

pub fn reserve(id: u64, extra: usize) -> Result<(), &'static str> {
    let requests = active().lock().unwrap();
    let Some(permit) = requests.get(&id) else {
        return Err("request is no longer active");
    };
    let mut usage = USAGE.lock().unwrap();
    if extra > REQUEST_BYTES.saturating_sub(usage.1) {
        return Err("request byte capacity exceeded");
    }
    usage.1 += extra;
    permit.bytes.fetch_add(extra, Ordering::Relaxed);
    Ok(())
}

pub fn cancelled(id: u64) -> bool {
    active()
        .lock()
        .unwrap()
        .get(&id)
        .is_some_and(|p| p.cancelled.load(Ordering::Relaxed))
}

pub fn cancel(id: u64) {
    if let Some(p) = active().lock().unwrap().get(&id) {
        p.cancelled.store(true, Ordering::Relaxed);
    }
}

pub fn permit(id: u64) -> Option<Arc<Permit>> {
    active().lock().unwrap().get(&id).cloned()
}

pub fn complete(id: u64) {
    active().lock().unwrap().remove(&id);
}

/// Consume an oversized record through its newline, without growing a String
/// or losing framing for the next request. `None` means clean EOF.
pub fn read_line(
    reader: &mut impl BufRead,
    max: usize,
) -> io::Result<Option<Result<String, &'static str>>> {
    let mut line = Vec::new();
    let mut oversized = false;
    loop {
        let chunk = reader.fill_buf()?;
        if chunk.is_empty() {
            if line.is_empty() && !oversized {
                return Ok(None);
            }
            break;
        }
        let end = chunk.iter().position(|b| *b == b'\n').map(|n| n + 1);
        let n = end.unwrap_or(chunk.len());
        if !oversized {
            if n > max.saturating_sub(line.len()) {
                oversized = true;
                line.clear();
            } else {
                line.extend_from_slice(&chunk[..n]);
            }
        }
        reader.consume(n);
        if end.is_some() {
            break;
        }
    }
    Ok(Some(if oversized {
        Err("request line exceeds 8 MiB")
    } else {
        String::from_utf8(line).map_err(|_| "request line is not UTF-8")
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn oversized_and_invalid_lines_preserve_framing() {
        let mut input = io::BufReader::with_capacity(3, &b"abcdefghij\nok\n\xff\nlast"[..]);
        assert!(read_line(&mut input, 5).unwrap().unwrap().is_err());
        assert_eq!(read_line(&mut input, 5).unwrap().unwrap().unwrap(), "ok\n");
        assert!(read_line(&mut input, 5).unwrap().unwrap().is_err());
        assert_eq!(read_line(&mut input, 5).unwrap().unwrap().unwrap(), "last");
        assert!(read_line(&mut input, 5).unwrap().is_none());
    }

    #[test]
    fn cancelled_events_keep_their_memory_reservation_until_dropped() {
        let permit = admit(u64::MAX, REQUEST_BYTES).unwrap();
        cancel(u64::MAX);
        assert!(cancelled(u64::MAX));
        complete(u64::MAX);
        assert!(admit(u64::MAX - 1, 1).is_err());
        drop(permit);
        let next = admit(u64::MAX - 1, 1).unwrap();
        assert!(reserve(u64::MAX - 1, REQUEST_BYTES).is_err());
        complete(u64::MAX - 1);
        drop(next);
        let permits: Vec<_> = (0..REQUESTS as u64)
            .map(|id| admit(id, 1024).unwrap())
            .collect();
        assert!(admit(REQUESTS as u64, 1).is_err());
        for id in 0..REQUESTS as u64 {
            complete(id);
        }
        assert!(admit(REQUESTS as u64, 1).is_err());
        drop(permits);
        let last = admit(REQUESTS as u64, 1).unwrap();
        complete(REQUESTS as u64);
        drop(last);
    }
}
