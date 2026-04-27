use std::process::Command;
use std::sync::Mutex;
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::TrayIconBuilder,
    AppHandle, Manager, WindowEvent,
};

struct BackendProcess {
    child: Mutex<Option<std::process::Child>>,
    #[cfg(windows)]
    job: Mutex<Option<windows_job::JobObject>>,
}

#[cfg(windows)]
mod windows_job {
    use std::os::windows::io::AsRawHandle;

    #[link(name = "kernel32")]
    extern "system" {
        fn CreateJobObjectW(
            lpJobAttributes: *mut std::ffi::c_void,
            lpName: *const u16,
        ) -> *mut std::ffi::c_void;
        fn SetInformationJobObject(
            hJob: *mut std::ffi::c_void,
            JobObjectInformationClass: u32,
            lpJobObjectInformation: *const std::ffi::c_void,
            cbJobObjectInformationLength: u32,
        ) -> i32;
        fn AssignProcessToJobObject(
            hJob: *mut std::ffi::c_void,
            hProcess: *mut std::ffi::c_void,
        ) -> i32;
        fn CloseHandle(hObject: *mut std::ffi::c_void) -> i32;
    }

    const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x2000;
    const JOB_OBJECT_EXTENDED_LIMIT_INFORMATION: u32 = 9;

    #[repr(C)]
    #[derive(Default)]
    struct IoCounters {
        _data: [u64; 6],
    }

    #[repr(C)]
    #[derive(Default)]
    struct BasicLimitInformation {
        _per_process_user_time_limit: i64,
        _per_job_user_time_limit: i64,
        limit_flags: u32,
        _minimum_working_set_size: usize,
        _maximum_working_set_size: usize,
        _active_process_limit: u32,
        _affinity: usize,
        _priority_class: u32,
        _scheduling_class: u32,
    }

    #[repr(C)]
    #[derive(Default)]
    struct ExtendedLimitInformation {
        basic: BasicLimitInformation,
        _io_info: IoCounters,
        _process_memory_limit: usize,
        _job_memory_limit: usize,
        _peak_process_memory_used: usize,
        _peak_job_memory_used: usize,
    }

    pub struct JobObject {
        handle: *mut std::ffi::c_void,
    }

    unsafe impl Send for JobObject {}
    unsafe impl Sync for JobObject {}

    impl JobObject {
        pub fn new() -> Option<Self> {
            unsafe {
                let handle = CreateJobObjectW(std::ptr::null_mut(), std::ptr::null());
                if handle.is_null() {
                    return None;
                }

                let mut info = ExtendedLimitInformation::default();
                info.basic.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

                let ok = SetInformationJobObject(
                    handle,
                    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                    &info as *const _ as *const std::ffi::c_void,
                    std::mem::size_of::<ExtendedLimitInformation>() as u32,
                );
                if ok == 0 {
                    CloseHandle(handle);
                    return None;
                }

                Some(Self { handle })
            }
        }

        pub fn assign(&self, child: &std::process::Child) -> bool {
            unsafe {
                let process_handle = child.as_raw_handle() as *mut std::ffi::c_void;
                AssignProcessToJobObject(self.handle, process_handle) != 0
            }
        }
    }

    impl Drop for JobObject {
        fn drop(&mut self) {
            unsafe {
                CloseHandle(self.handle);
            }
        }
    }
}

#[tauri::command]
fn show_launcher(app: AppHandle) {
    if let Some(w) = app.get_webview_window("launcher") {
        let _ = w.show();
        let _ = w.set_focus();
        let _ = w.center();
    }
}

#[tauri::command]
fn hide_launcher(app: AppHandle) {
    if let Some(w) = app.get_webview_window("launcher") {
        let _ = w.hide();
    }
}

#[tauri::command]
fn show_main(app: AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.set_focus();
        let _ = w.center();
    }
}

#[tauri::command]
fn hide_main(app: AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.hide();
    }
}

#[tauri::command]
fn hide_all(app: AppHandle) {
    hide_launcher(app.clone());
    hide_main(app);
}

fn toggle_launcher(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("launcher") {
        if w.is_visible().unwrap_or(false) {
            let _ = w.hide();
        } else {
            let _ = w.show();
            let _ = w.set_focus();
            let _ = w.center();
        }
    }
}

fn kill_backend(app: &AppHandle) {
    if let Some(state) = app.try_state::<BackendProcess>() {
        if let Ok(mut guard) = state.child.lock() {
            if let Some(ref mut child) = *guard {
                let _ = child.kill();
                let _ = child.wait();
            }
            *guard = None;
        }
    }
}

fn start_python_backend() -> (Option<std::process::Child>, Option<windows_job::JobObject>) {
    let mut cmd = Command::new("uv");
    cmd.args(["run", "gotit", "--mode", "server"])
        .current_dir(
            std::env::current_exe()
                .ok()
                .and_then(|p| p.parent()?.parent()?.parent().map(|p| p.to_path_buf()))
                .unwrap_or_else(|| std::env::current_dir().unwrap_or_default()),
        );

    if !cfg!(debug_assertions) {
        cmd.env("GOTIT_RELEASE", "1");
    }

    let child = cmd.spawn();

    match child {
        Ok(child) => {
            log::info!("Python backend started (pid: {})", child.id());

            let job = windows_job::JobObject::new();
            if let Some(ref j) = job {
                if j.assign(&child) {
                    log::info!("Backend process assigned to job object (auto-kill on exit)");
                } else {
                    log::warn!("Failed to assign backend to job object");
                }
            }

            (Some(child), job)
        }
        Err(e) => {
            log::error!("Failed to start Python backend: {}", e);
            (None, None)
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().level(
            if cfg!(debug_assertions) { log::LevelFilter::Info } else { log::LevelFilter::Error }
        ).build())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .manage(BackendProcess {
            child: Mutex::new(None),
            #[cfg(windows)]
            job: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            show_launcher,
            hide_launcher,
            show_main,
            hide_main,
            hide_all,
        ])
        .setup(|app| {
            // --- Tray icon ---
            let show = MenuItemBuilder::with_id("show", "Show GotIt (Ctrl+Shift+G)").build(app)?;
            let quit = MenuItemBuilder::with_id("quit", "Quit").build(app)?;
            let menu = MenuBuilder::new(app).items(&[&show, &quit]).build()?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().cloned().unwrap())
                .menu(&menu)
                .tooltip("GotIt")
                .on_menu_event(move |app, event| match event.id().as_ref() {
                    "show" => toggle_launcher(app),
                    "quit" => {
                        kill_backend(app);
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { button, .. } = event {
                        if button == tauri::tray::MouseButton::Left {
                            toggle_launcher(tray.app_handle());
                        }
                    }
                })
                .build(app)?;

            // --- Global shortcut ---
            use tauri_plugin_global_shortcut::GlobalShortcutExt;
            let handle = app.handle().clone();
            app.global_shortcut().on_shortcut("ctrl+shift+g", move |_app, _shortcut, event| {
                if event.state == tauri_plugin_global_shortcut::ShortcutState::Pressed {
                    toggle_launcher(&handle);
                }
            })?;

            // --- Launcher blur → auto-hide ---
            if let Some(launcher) = app.get_webview_window("launcher") {
                let app_handle = app.handle().clone();
                launcher.on_window_event(move |event| {
                    if let WindowEvent::Focused(false) = event {
                        if let Some(w) = app_handle.get_webview_window("launcher") {
                            let _ = w.hide();
                        }
                    }
                });
            }

            // --- Start Python backend ---
            let (child, job) = start_python_backend();
            if let Some(state) = app.try_state::<BackendProcess>() {
                if let Ok(mut guard) = state.child.lock() {
                    *guard = child;
                }
                #[cfg(windows)]
                if let Ok(mut guard) = state.job.lock() {
                    *guard = job;
                }
            }

            Ok(())
        })
        .on_window_event(|_window, event| {
            // Prevent app from quitting when windows are closed — keep in tray
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = _window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running GotIt");
}
