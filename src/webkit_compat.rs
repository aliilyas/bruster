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
