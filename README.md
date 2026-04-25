# GotIt

Voice-driven local AI assistant for Windows. Speak or type a command, GotIt understands your intent, searches local files via Everything, and executes actions.

## Architecture

```
Ctrl+Shift+G → [Launcher Bar] → Enter → [Main Panel]
                    │                         │
                    └── WebSocket ──→ Python Backend (FastAPI)
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                   whisper.cpp     LLM (OpenAI)    Everything
                   (speech→text)   (intent parse)  (file search)
                                                       │
                                                       ▼
                                                  Windows Shell
                                                  (open/run)
```

## Prerequisites

- **Python 3.12+** and **uv** (package manager)
- **Node.js 20+** and **npm**
- **Rust** toolchain (for Tauri desktop build)
- **Everything** — must be running (service or user mode)
- **es.exe** — Everything command-line tool, placed in PATH or configured via `GOTIT_SEARCH__EVERYTHING_PATH`

## Quick Start (Development)

### 1. Clone and install

```bash
git clone <repo-url>
cd GotIt

# Python backend
uv sync

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env — at minimum set GOTIT_LLM__API_KEY and GOTIT_LLM__BASE_URL
```

### 3. Download whisper model (optional, for voice input)

Download `ggml-base.bin` (~142MB) from [huggingface](https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin) and place it in `models/`.

### 4. Start Everything

Make sure Everything is running. If using service mode, also launch a user-mode instance:

```bash
"D:\03_Tools\Everything\Everything.exe" -startup
```

### 5. Run

**Text mode (quick test, no voice):**

```bash
uv run gotit --text "搜索py文件"
uv run gotit --text "打开记事本"
```

**Server mode (for frontend):**

```bash
# Terminal 1: Python backend
uv run gotit --mode server

# Terminal 2: Frontend dev server
cd frontend && npm run dev
```

Then open `http://localhost:5173` (Main Panel) or `http://localhost:5173/launcher.html` (Launcher Bar).

## Build & Package (Tauri Desktop App)

### Prerequisites for building

1. **Rust toolchain** — `rustc --version` should work
2. **Tauri CLI** — install if not already:
   ```bash
   cargo install tauri-cli --version "^2"
   ```
3. **Node.js + npm** — for frontend build
4. **uv** — for Python backend

### Development mode (Tauri)

Run the full Tauri app in dev mode (auto-reloads on code changes):

```bash
cd frontend
npx tauri dev
```

This will:
- Start the Vite dev server (frontend)
- Compile and launch the Tauri Rust shell
- Show the system tray icon
- Register `Ctrl+Shift+G` global shortcut

> **Note:** The Python backend needs to be started separately in another terminal:
> ```bash
> uv run gotit --mode server
> ```

### Production build

Build a distributable installer:

```bash
cd frontend
npx tauri build
```

This will:
1. Run `npm run build` (compile TypeScript + bundle frontend)
2. Compile the Rust binary in release mode
3. Generate an NSIS installer at:
   ```
   frontend/src-tauri/target/release/bundle/nsis/GotIt_0.1.0_x64-setup.exe
   ```

### Verify the build

1. **Run the installer** — double-click `GotIt_0.1.0_x64-setup.exe`
2. **Check tray icon** — GotIt icon should appear in the system tray (no visible window)
3. **Test shortcut** — press `Ctrl+Shift+G`, the Launcher Bar should appear at screen center
4. **Test input** — type a command (e.g. "搜索py文件") and press Enter
5. **Check Main Panel** — should show pipeline progress and search results
6. **Test execution** — click "Open" on a result, the file should open
7. **Test tray menu** — right-click tray icon → "Show GotIt" / "Quit"
8. **Test Esc** — press Escape in any window to hide it
9. **Test persistence** — close windows, app stays in tray; `Ctrl+Shift+G` brings it back

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Launcher doesn't appear | Check if `Ctrl+Shift+G` conflicts with another app |
| "Connection error" on submit | Ensure Python backend is running (`uv run gotit --mode server`) |
| Everything search returns 0 results | Ensure Everything is running in user mode, not just as service |
| whisper model not found | Download `ggml-base.bin` to `models/` directory |
| SSL errors with LLM API | The adapter uses `verify=False` — check your `.env` base URL |

## Project Structure

```
GotIt/
├── gotit/              # Python backend (FastAPI)
│   ├── domain/         # Models, ports, events, pipeline
│   ├── adapters/       # STT, LLM, search, executor, audio
│   ├── api/            # REST routes + WebSocket
│   └── services/       # EventBus, Container DI, session
├── frontend/           # React + TypeScript + Vite
│   ├── src/            # Components, hooks, stores
│   └── src-tauri/      # Tauri Rust shell
├── models/             # whisper.cpp model files (gitignored)
├── tests/              # pytest test suite
└── prompt/plan/        # Design docs
```

## Tests

```bash
# Run all tests (52 tests)
uv run pytest -v

# Frontend type check
cd frontend && npx tsc --noEmit

# Rust check
cd frontend/src-tauri && cargo check
```

## Configuration

All settings can be set via environment variables (prefix `GOTIT_`) or `.env` file. See `.env.example` for the full list.

Key settings:

| Variable | Description |
|----------|-------------|
| `GOTIT_LLM__API_KEY` | API token for LLM service |
| `GOTIT_LLM__BASE_URL` | OpenAI-compatible API endpoint |
| `GOTIT_LLM__MODEL` | Model name |
| `GOTIT_SEARCH__EVERYTHING_PATH` | Path to `es.exe` |
| `GOTIT_STT__MODEL_PATH` | Path to whisper model file |
| `GOTIT_DEBUG` | Enable debug logging |
