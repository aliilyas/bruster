//! Workarounds restricted to affected WebKitGTK releases.
use std::ffi::{c_char, c_void, CStr};

use webkit2gtk::{glib::object::ObjectType, Settings};

pub fn configure(settings: &Settings) {
    // In 2.52.0–2.52.6 FetchBodySource::pull() sets the pending pull without
    // calling feedStream(). Already-buffered bytes then wait for more network
    // data or EOF. The older non-byte source does call feedStream().
    // https://github.com/WebKit/WebKit/blob/webkitgtk-2.52.6/Source/WebCore/Modules/fetch/FetchBodySource.cpp
    let affected = unsafe {
        webkit2gtk::ffi::webkit_get_major_version() == 2
            && webkit2gtk::ffi::webkit_get_minor_version() == 52
            && webkit2gtk::ffi::webkit_get_micro_version() <= 6
    };
    if !affected {
        return;
    }

    // The feature API arrived in 2.42. Resolve it at runtime so binaries retain
    // their existing 2.38 minimum; all pointers are checked before any call.
    unsafe {
        let names = [
            c"webkit_settings_get_all_features",
            c"webkit_feature_list_get_length",
            c"webkit_feature_list_get",
            c"webkit_feature_get_identifier",
            c"webkit_settings_set_feature_enabled",
            c"webkit_feature_list_unref",
        ];
        let symbols = names.map(|name| libc::dlsym(libc::RTLD_DEFAULT, name.as_ptr()));
        if symbols.iter().any(|symbol| symbol.is_null()) {
            return;
        }
        let all: unsafe extern "C" fn() -> *mut c_void = std::mem::transmute(symbols[0]);
        let len: unsafe extern "C" fn(*mut c_void) -> u32 = std::mem::transmute(symbols[1]);
        let get: unsafe extern "C" fn(*mut c_void, u32) -> *mut c_void =
            std::mem::transmute(symbols[2]);
        let identifier: unsafe extern "C" fn(*mut c_void) -> *const c_char =
            std::mem::transmute(symbols[3]);
        let set: unsafe extern "C" fn(*mut c_void, *mut c_void, i32) =
            std::mem::transmute(symbols[4]);
        let unref: unsafe extern "C" fn(*mut c_void) = std::mem::transmute(symbols[5]);
        let features = all();
        if features.is_null() {
            return;
        }
        for index in 0..len(features) {
            let feature = get(features, index);
            if feature.is_null() {
                continue;
            }
            let name = identifier(feature);
            if !name.is_null() && CStr::from_ptr(name) == c"ReadableByteStreamFetchSource" {
                set(settings.as_ptr().cast(), feature, 0);
                break;
            }
        }
        unref(features);
    }
}

#[cfg(test)]
mod tests {
    use gtk::glib::variant::ToVariant;

    // RUSTSEC-2024-0429: run in release mode, where the old GLib out-pointer
    // aliasing bug could turn these safe iterator calls into a segmentation fault.
    #[test]
    fn variant_string_iterator_handles_both_ends() {
        let values = ["first", "λ", "", "last"];
        let variant = values.to_variant();
        let mut iter = variant.array_iter_str().unwrap();
        assert_eq!(iter.len(), 4);
        assert_eq!(iter.next(), Some("first"));
        assert_eq!(iter.next_back(), Some("last"));
        assert_eq!(iter.next(), Some("λ"));
        assert_eq!(iter.next_back(), Some(""));
        assert_eq!(iter.next(), None);
        assert_eq!(iter.next_back(), None);

        assert_eq!(variant.array_iter_str().unwrap().nth(1), Some("λ"));
        assert_eq!(variant.array_iter_str().unwrap().nth_back(1), Some(""));
        assert_eq!(variant.array_iter_str().unwrap().last(), Some("last"));
        assert_eq!(
            variant.array_iter_str().unwrap().collect::<Vec<_>>(),
            values
        );
    }
}
