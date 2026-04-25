use std::process::Command;
use std::sync::Mutex;
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::TrayIconBuilder,
    AppHandle, Manager, WindowEvent,
};

struct BackendProcess(Mutex<Option<std::process::Child>>);

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

fn start_python_backend() -> Option<std::process::Child> {
    let child = Command::new("uv")
        .args(["run", "gotit", "--mode", "server"])
        .current_dir(
            std::env::current_exe()
                .ok()?
                .parent()?
                .parent()?
                .parent()?,
        )
        .spawn();

    match child {
        Ok(c) => {
            log::info!("Python backend started (pid: {})", c.id());
            Some(c)
        }
        Err(e) => {
            log::error!("Failed to start Python backend: {}", e);
            None
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().level(log::LevelFilter::Info).build())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .manage(BackendProcess(Mutex::new(None)))
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
                .menu(&menu)
                .tooltip("GotIt")
                .on_menu_event(move |app, event| match event.id().as_ref() {
                    "show" => toggle_launcher(app),
                    "quit" => {
                        // Kill backend before exit
                        if let Some(state) = app.try_state::<BackendProcess>() {
                            if let Ok(mut guard) = state.0.lock() {
                                if let Some(ref mut child) = *guard {
                                    let _ = child.kill();
                                }
                            }
                        }
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
            if let Some(child) = start_python_backend() {
                if let Some(state) = app.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        *guard = Some(child);
                    }
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
