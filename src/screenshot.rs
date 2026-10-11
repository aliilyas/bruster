//! Screenshot as PNG bytes, via each platform's native snapshot API.
//! Both calls are async on the UI thread; the result arrives through `cb`.

use wry::WebView;

pub type Done = Box<dyn FnOnce(Result<Vec<u8>, String>)>;

/// Viewport-relative rectangle in CSS pixels.
#[derive(Clone, Copy)]
#[cfg_attr(target_os = "windows", allow(dead_code))] // WebView2 cannot crop
pub struct Clip {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

#[cfg_attr(target_os = "windows", allow(dead_code))]
pub enum Region {
    Viewport,
    /// Whole document. On macOS the caller must first resize the window to
    /// the document height; WKWebView only renders what is on screen.
    Full,
    Clip(Clip),
}

#[cfg(target_os = "linux")]
pub fn capture(wv: &WebView, region: Region, cb: Done) {
    use webkit2gtk::{gio, SnapshotOptions, SnapshotRegion, WebViewExt};
    use wry::WebViewExtUnix;

    let gtk_region = match region {
        Region::Full => SnapshotRegion::FullDocument,
        _ => SnapshotRegion::Visible,
    };
    let clip = match region {
        Region::Clip(c) => Some(c),
        _ => None,
    };

    wv.webview().snapshot(gtk_region, SnapshotOptions::NONE, None::<&gio::Cancellable>, move |res| {
        let png = res.map_err(|e| e.to_string()).and_then(|surface| match clip {
            Some(c) => crop(&surface, c).and_then(|s| to_png(&s)),
            None => to_png(&surface),
        });
        cb(png);
    });
}

#[cfg(target_os = "linux")]
fn to_png(surface: &cairo::Surface) -> Result<Vec<u8>, String> {
    let mut buf = Vec::new();
    surface.write_to_png(&mut buf).map_err(|e| e.to_string())?;
    Ok(buf)
}

#[cfg(target_os = "linux")]
fn crop(src: &cairo::Surface, c: Clip) -> Result<cairo::ImageSurface, String> {
    use cairo::{Context, Format, ImageSurface};

    let out = ImageSurface::create(Format::ARgb32, c.width as i32, c.height as i32).map_err(|e| e.to_string())?;
    let cr = Context::new(&out).map_err(|e| e.to_string())?;
    cr.set_source_surface(src, -c.x, -c.y).map_err(|e| e.to_string())?;
    cr.paint().map_err(|e| e.to_string())?;
    drop(cr);
    Ok(out)
}

#[cfg(target_os = "macos")]
pub fn capture(wv: &WebView, region: Region, cb: Done) {
    use std::cell::RefCell;

    use block2::RcBlock;
    use objc2_app_kit::{NSBitmapImageFileType, NSBitmapImageRep, NSImage};
    use objc2_foundation::{NSDictionary, NSError, NSPoint, NSRect, NSSize};
    use objc2_web_kit::WKSnapshotConfiguration;
    use wry::WebViewExtMacOS;

    fn png_from(img: *mut NSImage, err: *mut NSError) -> Result<Vec<u8>, String> {
        if img.is_null() {
            let msg = unsafe { err.as_ref() }
                .map(|e| e.localizedDescription().to_string())
                .unwrap_or_else(|| "snapshot failed".into());
            return Err(msg);
        }

        let img = unsafe { &*img };
        let tiff = img.TIFFRepresentation().ok_or("no TIFF representation")?;
        let rep = NSBitmapImageRep::imageRepWithData(&tiff).ok_or("bitmap decode failed")?;
        let png = unsafe { rep.representationUsingType_properties(NSBitmapImageFileType::PNG, &NSDictionary::new()) }
            .ok_or("png encode failed")?;
        Ok(png.to_vec())
    }

    let mtm = objc2::MainThreadMarker::new().expect("screenshot must run on the main thread");
    let config = unsafe { WKSnapshotConfiguration::new(mtm) };
    unsafe { config.setAfterScreenUpdates(true) };
    if let Region::Clip(c) = region {
        let rect = NSRect::new(NSPoint::new(c.x, c.y), NSSize::new(c.width, c.height));
        unsafe { config.setRect(rect) };
    }

    // ObjC blocks are Fn; the completion fires once, so hand the FnOnce over through a cell.
    let cb = RefCell::new(Some(cb));
    let block = RcBlock::new(move |img: *mut NSImage, err: *mut NSError| {
        if let Some(cb) = cb.borrow_mut().take() {
            cb(png_from(img, err));
        }
    });

    unsafe { wv.webview().takeSnapshotWithConfiguration_completionHandler(Some(&config), &block) };
}

/// WebView2 captures the visible viewport as PNG into a COM stream. Clips are
/// not supported here (no image library to crop with).
#[cfg(target_os = "windows")]
pub fn capture(wv: &WebView, region: Region, cb: Done) {
    use webview2_com::CapturePreviewCompletedHandler;
    use webview2_com::Microsoft::Web::WebView2::Win32::COREWEBVIEW2_CAPTURE_PREVIEW_IMAGE_FORMAT_PNG;
    use windows::Win32::System::Com::StructuredStorage::CreateStreamOnHGlobal;
    use wry::WebViewExtWindows;

    if matches!(region, Region::Clip(_)) {
        return cb(Err("screenshot clip is not supported on Windows".into()));
    }
    let stream = match unsafe { CreateStreamOnHGlobal(Default::default(), true) } {
        Ok(s) => s,
        Err(e) => return cb(Err(e.to_string())),
    };
    let core = match unsafe { wv.controller().CoreWebView2() } {
        Ok(c) => c,
        Err(e) => return cb(Err(e.to_string())),
    };

    let done_stream = stream.clone();
    let handler = CapturePreviewCompletedHandler::create(Box::new(move |result: windows::core::Result<()>| {
        let png = result.map_err(|e| e.to_string()).and_then(|_| read_stream(&done_stream));
        cb(png);
        Ok(())
    }));
    if let Err(e) = unsafe { core.CapturePreview(COREWEBVIEW2_CAPTURE_PREVIEW_IMAGE_FORMAT_PNG, &stream, &handler) } {
        // The handler owns `cb` now; report through the webview error path instead.
        eprintln!("screenshot: {e}");
    }
}

#[cfg(target_os = "windows")]
fn read_stream(stream: &windows::Win32::System::Com::IStream) -> Result<Vec<u8>, String> {
    use windows::Win32::System::Com::STREAM_SEEK_SET;

    unsafe { stream.Seek(0, STREAM_SEEK_SET, None) }.map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    let mut buf = [0u8; 64 * 1024];
    loop {
        let mut read = 0u32;
        let hr = unsafe { stream.Read(buf.as_mut_ptr() as *mut _, buf.len() as u32, Some(&mut read)) };
        if hr.is_err() {
            return Err(hr.to_string());
        }
        if read == 0 {
            return Ok(out);
        }
        out.extend_from_slice(&buf[..read as usize]);
    }
}

#[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
pub fn capture(_wv: &WebView, _region: Region, cb: Done) {
    cb(Err("screenshot not supported on this platform".into()));
}

const B64: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/// Standard base64 with padding. Small enough to not warrant a crate.
pub fn base64(data: &[u8]) -> String {
    let mut out = String::with_capacity(data.len().div_ceil(3) * 4);

    for chunk in data.chunks(3) {
        let n = chunk.iter().fold(0u32, |acc, &b| (acc << 8) | b as u32) << (8 * (3 - chunk.len()));
        for i in 0..4 {
            if i <= chunk.len() {
                out.push(B64[((n >> (18 - 6 * i)) & 63) as usize] as char);
            } else {
                out.push('=');
            }
        }
    }

    out
}

#[cfg(test)]
mod tests {
    #[test]
    fn base64_matches_rfc() {
        assert_eq!(super::base64(b""), "");
        assert_eq!(super::base64(b"f"), "Zg==");
        assert_eq!(super::base64(b"fo"), "Zm8=");
        assert_eq!(super::base64(b"foo"), "Zm9v");
        assert_eq!(super::base64(b"foobar"), "Zm9vYmFy");
    }
}
