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

---

## Configuration

GotIt loads configuration from three sources (later overrides earlier):

1. **`~/.gotit/.env`** — user home config (recommended for release)
2. **`.env`** in project directory — for development
3. **System environment variables** — highest priority

### First-time Setup (Release)

Run the setup script to create `~/.gotit/.env` interactively:

```bash
scripts\setup.bat
```

Or create `%USERPROFILE%\.gotit\.env` manually with the following content:

```env
# --- LLM (required) ---
GOTIT_LLM__PROVIDER=openai
GOTIT_LLM__API_KEY=your-api-key-here
GOTIT_LLM__MODEL=gpt-4o
GOTIT_LLM__BASE_URL=https://your-api-endpoint/v1

# --- Search (required) ---
GOTIT_SEARCH__EVERYTHING_PATH=D:\03_Tools\Everything\es.exe

# --- Optional ---
GOTIT_LLM__FALLBACK_MODELS=[]
GOTIT_SEARCH__MAX_RESULTS=20
GOTIT_SERVER__HOST=127.0.0.1
GOTIT_SERVER__PORT=8765
GOTIT_DEBUG=false
```

### All Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOTIT_LLM__PROVIDER` | LLM provider | `openai` |
| `GOTIT_LLM__API_KEY` | API token for LLM service | (required) |
| `GOTIT_LLM__MODEL` | Primary model name | (required) |
| `GOTIT_LLM__BASE_URL` | OpenAI-compatible API endpoint | |
| `GOTIT_LLM__FALLBACK_MODELS` | Fallback models (JSON array) | `[]` |
| `GOTIT_LLM__EXTRA_HEADERS` | Custom HTTP headers (JSON object) | `{}` |
| `GOTIT_SEARCH__EVERYTHING_PATH` | Path to `es.exe` | `es.exe` |
| `GOTIT_SEARCH__MAX_RESULTS` | Max search results per query | `20` |
| `GOTIT_SEARCH__FILTER_RULES_PATH` | Path to filter rules YAML | `~/.gotit/filters.yaml` |
| `GOTIT_STT__ENGINE` | Speech-to-text engine | `whisper_cpp` |
| `GOTIT_STT__MODEL_PATH` | Path to whisper model file | `models/ggml-base.bin` |
| `GOTIT_STT__LANGUAGE` | STT language | `zh` |
| `GOTIT_AUDIO__DEVICE_INDEX` | Audio device index (empty=default) | |
| `GOTIT_AUDIO__SAMPLE_RATE` | Audio sample rate | `16000` |
| `GOTIT_UI__AUTO_CLOSE_DELAY` | Main Panel auto-close seconds | `3` |
| `GOTIT_UI__GLOBAL_HOTKEY` | Global hotkey | `Ctrl+Shift+G` |
| `GOTIT_SERVER__HOST` | Server bind address | `127.0.0.1` |
| `GOTIT_SERVER__PORT` | Server port | `8765` |
| `GOTIT_ACTIVITY__ENABLED` | Enable activity tracking | `true` |
| `GOTIT_ACTIVITY__RETENTION_DAYS` | Activity data retention | `14` |
| `GOTIT_ACTIVITY__DB_PATH` | Activity database path | `~/.gotit/activity.db` |
| `GOTIT_DEBUG` | Enable debug logging | `false` |

---

## User Data Files

All user data is stored in `~/.gotit/` (`%USERPROFILE%\.gotit\`):

| File | Description | Editable |
|------|-------------|----------|
| `.env` | Configuration (API keys, paths) | Yes |
| `intent_prompt.md` | Custom LLM intent prompt (overrides built-in) | Yes |
| `filters.yaml` | Search result filter rules | Yes |
| `learned_mappings.yaml` | Learned command-to-file mappings (auto-generated) | Yes |
| `activity.db` | Activity history database (auto-generated) | No |

### Custom Intent Prompt

GotIt uses an LLM prompt to parse user commands into structured intents. To customize it:

1. Copy the built-in prompt to your user directory:
   ```bash
   copy gotit\adapters\llm\prompts\intent_system.md %USERPROFILE%\.gotit\intent_prompt.md
   ```
2. Edit `~/.gotit/intent_prompt.md` to add your own examples, tools, or project context.
3. Restart GotIt — it will use your custom prompt automatically.

If `~/.gotit/intent_prompt.md` exists, it takes priority over the built-in prompt.

### Search Result Filters

Manage filter rules via CLI:

```bash
gotit filter list                    # Show all filter rules
gotit filter add path .cache         # Exclude paths containing .cache
gotit filter add filename "*.log"    # Exclude log files
gotit filter add ext dll             # Exclude .dll files
gotit filter remove path .cache      # Remove a rule
gotit filter path                    # Show filters.yaml location
```

Or edit `~/.gotit/filters.yaml` directly.

---

## Build & Package

### Development mode (Tauri)

```bash
cd frontend
npx tauri dev
```

> The Python backend starts automatically via Tauri.

### Production build

Use the build scripts in `scripts/`:

```bash
scripts\build-release.bat    # Release build (ERROR-only logs, NSIS installer)
scripts\build-debug.bat      # Debug build (full logging)
scripts\build-all.bat        # Both versions
```

Output:
- **Installer**: `frontend\src-tauri\target\release\bundle\nsis\GotIt_0.1.0_x64-setup.exe` (~2.6MB)
- **Executable**: `frontend\src-tauri\target\release\gotit-app.exe` (~12MB)

### Log Levels

| Build | Python backend | Tauri/Rust |
|-------|---------------|------------|
| Debug (`build-debug.bat`) | INFO | INFO |
| Release (`build-release.bat`) | ERROR only | ERROR only |
| Dev (`npx tauri dev`) | INFO | INFO |
| CLI `--debug` flag | DEBUG | — |

---

## Project Structure

```
GotIt/
├── gotit/                  # Python backend (FastAPI)
│   ├── domain/             # Models, ports, events, pipeline
│   ├── adapters/           # STT, LLM, search, executor, activity
│   ├── api/                # REST routes + WebSocket
│   └── services/           # EventBus, Container, session, filters, mappings
├── frontend/               # React + TypeScript + Vite
│   ├── src/                # Components, hooks, stores
│   └── src-tauri/          # Tauri Rust shell
├── models/                 # whisper.cpp model files (gitignored)
├── tests/                  # pytest test suite
├── scripts/                # Build and setup scripts
└── prompt/                 # Design docs and feature specs
```

## Tests

```bash
# Run all tests
uv run pytest -v

# Frontend type check
cd frontend && npx tsc --noEmit

# Rust check
cd frontend/src-tauri && cargo check
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Launcher doesn't appear | Check if `Ctrl+Shift+G` conflicts with another app |
| "Connection error" on submit | Ensure Python backend is running |
| Everything search returns 0 results | Ensure Everything is running in user mode |
| whisper model not found | Download `ggml-base.bin` to `models/` directory |
| SSL errors with LLM API | Check your `.env` base URL |
| `gotit.exe` locked during `uv sync` | Kill orphan processes: `taskkill /F /IM gotit.exe` |
| Custom prompt not loading | Ensure file is at `~/.gotit/intent_prompt.md` (not `.txt`) |
