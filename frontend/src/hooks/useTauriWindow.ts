import { useCallback } from "react";

const isTauri = "__TAURI__" in window;

export function useTauriWindow() {
  const showLauncher = useCallback(() => {
    if (isTauri) {
      // Tauri: invoke Rust command
    } else {
      window.open("/launcher.html", "gotit-launcher", "width=640,height=80");
    }
  }, []);

  const hideLauncherShowPanel = useCallback((_text: string) => {
    if (isTauri) {
      // Tauri: hide launcher, show main, emit query
    } else {
      window.close();
      window.open("/", "gotit-main", "width=720,height=520");
    }
  }, []);

  const hideAll = useCallback(() => {
    if (isTauri) {
      // Tauri: hide all windows
    } else {
      window.close();
    }
  }, []);

  return { showLauncher, hideLauncherShowPanel, hideAll, isTauri };
}
