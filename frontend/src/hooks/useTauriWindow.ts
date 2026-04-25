import { useCallback } from "react";

const isTauri = typeof window !== "undefined" && "__TAURI__" in window;

async function invoke(cmd: string) {
  if (isTauri) {
    const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
    return tauriInvoke(cmd);
  }
}

export function useTauriWindow() {
  const showLauncher = useCallback(async () => {
    if (isTauri) {
      await invoke("show_launcher");
    }
  }, []);

  const hideLauncher = useCallback(async () => {
    if (isTauri) {
      await invoke("hide_launcher");
    }
  }, []);

  const showMain = useCallback(async () => {
    if (isTauri) {
      await invoke("show_main");
    }
  }, []);

  const hideMain = useCallback(async () => {
    if (isTauri) {
      await invoke("hide_main");
    }
  }, []);

  const hideAll = useCallback(async () => {
    if (isTauri) {
      await invoke("hide_all");
    }
  }, []);

  return { showLauncher, hideLauncher, showMain, hideMain, hideAll, isTauri };
}
