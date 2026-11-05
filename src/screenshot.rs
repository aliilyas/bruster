//! Screenshot as PNG bytes, via each platform's native snapshot API.
//! Both calls are async on the UI thread; the result arrives through `cb`.

use wry::WebView;

pub enum Output {
    Bytes(Vec<u8>),
    File { path: String, bytes: u64 },
}
pub type Done = Box<dyn FnOnce(Result<Output, String>)>;
pub const MAX_PIXELS: f64 = 24.0 * 1024.0 * 1024.0;
#[cfg(target_os = "linux")]
const MAX_RGB_PIXELS: i64 = 1024 * 1024;

static CAPTURES: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
pub struct Slot;
impl Slot {
    #[allow(deprecated, reason = "try_update is newer than the Rust 1.85 MSRV")]
    pub fn acquire() -> Option<std::sync::Arc<Self>> {
        use std::sync::atomic::Ordering;
        CAPTURES
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |n| {
                (n < 2).then_some(n + 1)
            })
            .ok()
            .map(|_| std::sync::Arc::new(Self))
    }
}
impl Drop for Slot {
    fn drop(&mut self) {
        CAPTURES.fetch_sub(1, std::sync::atomic::Ordering::Relaxed);
    }
}

#[derive(Clone, Default)]
pub struct Cancellation {
    stopped: std::rc::Rc<std::cell::Cell<bool>>,
    #[cfg(target_os = "linux")]
    native: webkit2gtk::gio::Cancellable,
}

impl Cancellation {
    pub fn cancel(&self) {
        self.stopped.set(true);
        #[cfg(target_os = "linux")]
        {
            use webkit2gtk::gio::prelude::CancellableExt;
            self.native.cancel();
        }
    }
    fn check(&self) -> Result<(), String> {
        if self.stopped.get() {
            Err("screenshot cancelled".into())
        } else {
            Ok(())
        }
    }
}

pub fn validate_size(width: f64, height: f64, scale: f64) -> Result<(), String> {
    if ![width, height, scale]
        .iter()
        .all(|v| v.is_finite() && *v > 0.0)
        || (width * scale).ceil() * (height * scale).ceil() > MAX_PIXELS
        || width * scale > 32767.0
        || height * scale > 32767.0
    {
        Err(
            "screenshot: exceeds the 24-megapixel physical pixel budget or native size limit"
                .into(),
        )
    } else {
        Ok(())
    }
}

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
#[derive(Clone, Copy)]
pub enum Region {
    Viewport,
    /// Whole document. On macOS the caller must first resize the window to
    /// the document height; WKWebView only renders what is on screen.
    Full,
    Clip(Clip),
}

#[cfg(target_os = "linux")]
pub fn capture(wv: &WebView, region: Region, path: Option<String>, cancel: Cancellation, cb: Done) {
    use webkit2gtk::{SnapshotOptions, SnapshotRegion, WebViewExt};
    use wry::WebViewExtUnix;

    let gtk_region = match region {
        Region::Full => SnapshotRegion::FullDocument,
        _ => SnapshotRegion::Visible,
    };
    let clip = match region {
        Region::Clip(c) => Some(c),
        _ => None,
    };

    let capture = crate::timing::Span::new("screenshot_capture");
    let native_cancel = cancel.native.clone();
    wv.webview().snapshot(
        gtk_region,
        SnapshotOptions::NONE,
        Some(&native_cancel),
        move |res| {
            drop(capture);
            let png = res.map_err(|e| e.to_string()).and_then(|surface| {
                cancel.check()?;
                if let Ok(image) = cairo::ImageSurface::try_from(surface.clone()) {
                    validate_size(image.width() as f64, image.height() as f64, 1.0)?;
                }
                let cropped;
                let surface = if let Some(c) = clip {
                    cropped = crop(&surface, c)?;
                    cropped.as_ref()
                } else {
                    &surface
                };
                if let Some(path) = path {
                    // File output needs no PNG Vec or additional full RGB surface.
                    let file = std::fs::File::create(&path).map_err(|e| e.to_string())?;
                    let mut writer = std::io::BufWriter::new(file);
                    surface
                        .write_to_png(&mut writer)
                        .map_err(|e| e.to_string())?;
                    use std::io::Write;
                    writer.flush().map_err(|e| e.to_string())?;
                    let bytes = writer
                        .get_ref()
                        .metadata()
                        .map_err(|e| e.to_string())?
                        .len();
                    Ok(Output::File { path, bytes })
                } else {
                    to_png(surface).map(Output::Bytes)
                }
            });
            cb(png);
        },
    );
}

#[cfg(target_os = "linux")]
fn to_png(surface: &cairo::Surface) -> Result<Vec<u8>, String> {
    let _encoding = crate::timing::Span::new("screenshot_png");
    if let Ok(image) = cairo::ImageSurface::try_from(surface.clone()) {
        // Most pages are opaque. Strip only a proven-opaque alpha channel;
        // encoding RGBA needlessly increases both compression and pipe work.
        let conversion = crate::timing::Span::new("screenshot_pixel_conversion");
        let mut rgb = None;
        if matches!(image.format(), cairo::Format::ARgb32 | cairo::Format::Rgb24)
            && image.width() > 0
            && image.height() > 0
            && i64::from(image.width()) * i64::from(image.height()) <= MAX_RGB_PIXELS
        {
            image
                .with_data(|data| {
                    let rows = || {
                        data.chunks(image.stride() as usize)
                            .map(|row| &row[..image.width() as usize * 4])
                    };
                    let opaque = image.format() == cairo::Format::Rgb24
                        || rows().all(|row| {
                            row.as_chunks::<4>()
                                .0
                                .iter()
                                .all(|p| u32::from_ne_bytes(*p) >> 24 == 255)
                        });
                    if opaque {
                        let mut pixels = Vec::with_capacity(
                            image.width() as usize * image.height() as usize * 3,
                        );
                        for row in rows() {
                            for p in row.as_chunks::<4>().0 {
                                let pixel = u32::from_ne_bytes(*p);
                                pixels.extend_from_slice(&[
                                    (pixel >> 16) as u8,
                                    (pixel >> 8) as u8,
                                    pixel as u8,
                                ]);
                            }
                        }
                        rgb = Some(pixels);
                    }
                })
                .map_err(|e| e.to_string())?;
        }
        drop(conversion);
        if let Some(rgb) = rgb {
            let pixels = gtk::gdk_pixbuf::Pixbuf::from_mut_slice(
                rgb,
                gtk::gdk_pixbuf::Colorspace::Rgb,
                false,
                8,
                image.width(),
                image.height(),
                image.width() * 3,
            );
            return pixels
                .save_to_bufferv("png", &[("compression", "3")])
                .map_err(|e| e.to_string());
        }
    }
    // Cairo preserves alpha/premultiplication for transparent captures and also
    // supports non-image surfaces returned by other WebKit versions.
    let mut buf = Vec::new();
    surface.write_to_png(&mut buf).map_err(|e| e.to_string())?;
    Ok(buf)
}

#[cfg(target_os = "linux")]
fn crop(src: &cairo::Surface, c: Clip) -> Result<cairo::ImageSurface, String> {
    use cairo::{Context, Format, ImageSurface};

    let (sx, sy) = src.device_scale();
    validate_size(c.width, c.height, sx.max(sy))?;
    let out = ImageSurface::create(
        Format::ARgb32,
        (c.width * sx).ceil() as i32,
        (c.height * sy).ceil() as i32,
    )
    .map_err(|e| e.to_string())?;
    out.set_device_scale(sx, sy);
    let cr = Context::new(&out).map_err(|e| e.to_string())?;
    cr.set_source_surface(src, -c.x, -c.y)
        .map_err(|e| e.to_string())?;
    cr.paint().map_err(|e| e.to_string())?;
    drop(cr);
    Ok(out)
}

#[cfg(target_os = "macos")]
pub fn capture(wv: &WebView, region: Region, path: Option<String>, cancel: Cancellation, cb: Done) {
    use std::cell::RefCell;

    use block2::RcBlock;
    use objc2::AnyThread;
    use objc2_app_kit::{NSBitmapImageFileType, NSBitmapImageRep, NSImage};
    use objc2_foundation::{NSDictionary, NSError, NSPoint, NSRect, NSSize};
    use objc2_web_kit::WKSnapshotConfiguration;
    use wry::WebViewExtMacOS;

    fn png_from(
        img: *mut NSImage,
        err: *mut NSError,
        path: Option<String>,
    ) -> Result<Output, String> {
        let _encoding = crate::timing::Span::new("screenshot_png");
        if img.is_null() {
            let msg = unsafe { err.as_ref() }
                .map(|e| e.localizedDescription().to_string())
                .unwrap_or_else(|| "snapshot failed".into());
            return Err(msg);
        }

        let img = unsafe { &*img };
        // Preserve the native backing resolution without encoding and decoding
        // an intermediate TIFF. WKWebView's snapshot already owns the pixels.
        let pixels =
            unsafe { img.CGImageForProposedRect_context_hints(std::ptr::null_mut(), None, None) }
                .ok_or("no snapshot bitmap")?;
        let rep = NSBitmapImageRep::initWithCGImage(NSBitmapImageRep::alloc(), &pixels);
        let png = unsafe {
            rep.representationUsingType_properties(NSBitmapImageFileType::PNG, &NSDictionary::new())
        }
        .ok_or("png encode failed")?;
        if let Some(path) = path {
            // The freshly encoded NSData is kept alive and never mutated while
            // this synchronous write borrows its bytes.
            std::fs::write(&path, unsafe { png.as_bytes_unchecked() })
                .map_err(|e| e.to_string())?;
            Ok(Output::File {
                path,
                bytes: png.len() as u64,
            })
        } else {
            Ok(Output::Bytes(png.to_vec()))
        }
    }

    let mtm = objc2::MainThreadMarker::new().expect("screenshot must run on the main thread");
    let config = unsafe { WKSnapshotConfiguration::new(mtm) };
    unsafe { config.setAfterScreenUpdates(true) };
    if let Region::Clip(c) = region {
        let rect = NSRect::new(NSPoint::new(c.x, c.y), NSSize::new(c.width, c.height));
        unsafe { config.setRect(rect) };
    }

    // ObjC blocks are Fn; the completion fires once, so hand the FnOnce over through a cell.
    let cb = RefCell::new(Some((
        crate::timing::Span::new("screenshot_capture"),
        cb,
        path,
    )));
    let block = RcBlock::new(move |img: *mut NSImage, err: *mut NSError| {
        if let Some((capture, cb, path)) = cb.borrow_mut().take() {
            drop(capture);
            cb(cancel.check().and_then(|_| png_from(img, err, path)));
        }
    });

    unsafe {
        wv.webview()
            .takeSnapshotWithConfiguration_completionHandler(Some(&config), &block)
    };
}

/// WebView2 captures the visible viewport as PNG into a COM stream. Clips are
/// not supported here (no image library to crop with).
#[cfg(target_os = "windows")]
pub fn capture(wv: &WebView, region: Region, path: Option<String>, cancel: Cancellation, cb: Done) {
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
    let completion = std::rc::Rc::new(std::cell::RefCell::new(Some(cb)));
    let done = completion.clone();
    let handler = CapturePreviewCompletedHandler::create(Box::new(
        move |result: windows::core::Result<()>| {
            let png = result
                .map_err(|e| e.to_string())
                .and_then(|_| cancel.check())
                .and_then(|_| read_stream(&done_stream, path));
            if let Some(cb) = done.borrow_mut().take() {
                cb(png);
            }
            Ok(())
        },
    ));
    if let Err(e) = unsafe {
        core.CapturePreview(
            COREWEBVIEW2_CAPTURE_PREVIEW_IMAGE_FORMAT_PNG,
            &stream,
            &handler,
        )
    } {
        if let Some(cb) = completion.borrow_mut().take() {
            cb(Err(e.to_string()));
        }
    }
}

#[cfg(target_os = "windows")]
fn read_stream(
    stream: &windows::Win32::System::Com::IStream,
    path: Option<String>,
) -> Result<Output, String> {
    use windows::Win32::System::Com::STREAM_SEEK_SET;

    unsafe { stream.Seek(0, STREAM_SEEK_SET, None) }.map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    let mut file = path
        .as_ref()
        .map(std::fs::File::create)
        .transpose()
        .map_err(|e| e.to_string())?;
    let mut bytes = 0;
    let mut buf = [0u8; 64 * 1024];
    loop {
        let mut read = 0u32;
        let hr = unsafe {
            stream.Read(
                buf.as_mut_ptr() as *mut _,
                buf.len() as u32,
                Some(&mut read),
            )
        };
        if hr.is_err() {
            return Err(hr.to_string());
        }
        if read == 0 {
            return match path {
                Some(path) => Ok(Output::File { path, bytes }),
                None => Ok(Output::Bytes(out)),
            };
        }
        if let Some(file) = file.as_mut() {
            use std::io::Write;
            file.write_all(&buf[..read as usize])
                .map_err(|e| e.to_string())?;
        } else {
            out.extend_from_slice(&buf[..read as usize]);
        }
        bytes += u64::from(read);
    }
}

#[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
pub fn capture(
    _wv: &WebView,
    _region: Region,
    _path: Option<String>,
    _cancel: Cancellation,
    cb: Done,
) {
    cb(Err("screenshot not supported on this platform".into()));
}

const B64: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/// Standard base64 with padding. Small enough to not warrant a crate.
pub fn base64(data: &[u8]) -> String {
    let mut out = String::with_capacity(data.len().div_ceil(3) * 4);
    base64_append(data, &mut out);
    out
}

pub fn base64_append(data: &[u8], out: &mut String) {
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
}

#[cfg(test)]
mod tests {
    #[test]
    fn native_capture_slots_outlive_closed_owners() {
        let owner = super::Slot::acquire().unwrap();
        let callback = owner.clone();
        let other = super::Slot::acquire().unwrap();
        drop(owner);
        assert!(super::Slot::acquire().is_none());
        drop(callback);
        let replacement = super::Slot::acquire().unwrap();
        assert!(super::Slot::acquire().is_none());
        drop((other, replacement));
    }

    #[test]
    fn physical_pixel_budget_includes_backing_scale_and_rejects_overflow() {
        assert!(super::validate_size(1280.0, 16000.0, 1.0).is_ok());
        assert!(super::validate_size(1280.0, 16000.0, 2.0).is_err());
        assert!(super::validate_size(16000.0, 16000.0, 1.0).is_err());
        for value in [0.0, -1.0, f64::NAN, f64::INFINITY, f64::MAX] {
            assert!(super::validate_size(value, 800.0, 1.0).is_err());
        }
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn clips_use_physical_pixels_at_native_scale() {
        let image = cairo::ImageSurface::create(cairo::Format::ARgb32, 100, 80).unwrap();
        image.set_device_scale(2.0, 2.0);
        let clipped = super::crop(
            &image,
            super::Clip {
                x: 1.0,
                y: 2.0,
                width: 7.0,
                height: 5.0,
            },
        )
        .unwrap();
        assert_eq!((clipped.width(), clipped.height()), (14, 10));
        assert_eq!(clipped.device_scale(), (2.0, 2.0));
    }
    #[cfg(target_os = "linux")]
    #[test]
    fn png_preserves_pixels_alpha_stride_and_backing_scale() {
        use cairo::{Context, Format, ImageSurface};
        for transparent in [false, true] {
            for scale in [1.0, 2.0] {
                let surface = ImageSurface::create(Format::ARgb32, 37, 19).unwrap();
                let context = Context::new(&surface).unwrap();
                for x in 0..37 {
                    context.set_source_rgba(
                        x as f64 / 37.0,
                        0.4,
                        0.7,
                        if transparent { x as f64 / 37.0 } else { 1.0 },
                    );
                    context.rectangle(x as f64, 0.0, 1.0, 19.0);
                    context.fill().unwrap();
                }
                surface.set_device_scale(scale, scale);
                let mut original = Vec::new();
                surface.write_to_png(&mut original).unwrap();
                let optimized = super::to_png(&surface).unwrap();
                let decode = |png: &[u8]| {
                    let image =
                        ImageSurface::create_from_png(&mut std::io::Cursor::new(png)).unwrap();
                    assert_eq!((image.width(), image.height()), (37, 19));
                    let mut pixels = Vec::new();
                    image
                        .with_data(|data| pixels.extend_from_slice(data))
                        .unwrap();
                    pixels
                };
                assert_eq!(decode(&optimized), decode(&original));
            }
        }
    }

    #[test]
    fn base64_matches_rfc() {
        assert_eq!(super::base64(b""), "");
        assert_eq!(super::base64(b"f"), "Zg==");
        assert_eq!(super::base64(b"fo"), "Zm8=");
        assert_eq!(super::base64(b"foo"), "Zm9v");
        assert_eq!(super::base64(b"foobar"), "Zm9vYmFy");
    }
}
