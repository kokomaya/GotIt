
# GotIt 实施计划（Implementation Plan）

> 基于 idea.md 的系统设计，制定可落地的分阶段实施方案。

---

## 1. 技术栈确认

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| 语言 | Python 3.12+ | 生态丰富，AI/LLM集成方便 |
| 包管理 | uv | 速度快，现代化，替代pip/poetry |
| STT引擎 | whisper.cpp (pywhispercpp绑定) | 低资源、离线、高准确率 |
| LLM | Claude API (主) / Ollama本地 (备) | Claude理解力强；Ollama离线备选 |
| 文件搜索 | Everything SDK / CLI (es.exe) | 毫秒级Windows文件索引 |
| 后端框架 | FastAPI + uvicorn | 异步高性能，WebSocket支持 |
| 前端 | React + TypeScript + Vite | 现代化UI，组件生态丰富 |
| 桌面容器 | Tauri v2 | 轻量(~5MB)，原生系统调用，Rust安全性 |
| 进程通信 | WebSocket | 实时双向通信，前后端解耦 |
| 音频采集 | sounddevice (PortAudio) | 跨平台，低延迟实时音频流 |
| 配置管理 | Pydantic Settings | 类型安全，环境变量/文件双支持 |
| 日志 | structlog | 结构化日志，便于调试和监控 |
| 测试 | pytest + pytest-asyncio | 异步测试支持 |

---

## 2. 架构设计

### 2.1 整体架构（Clean Architecture）

```
┌─────────────────────────────────────────────────────┐
│                   Tauri Desktop Shell                │
│  ┌───────────────────────────────────────────────┐   │
│  │           React Frontend (WebView)            │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │VoiceBtn │ │ResultList│ │SettingsPanel │   │   │
│  │  └────┬────┘ └─────▲────┘ └──────────────┘   │   │
│  └───────┼────────────┼──────────────────────────┘   │
│          │ WebSocket  │                              │
└──────────┼────────────┼──────────────────────────────┘
           │            │
┌──────────▼────────────┼──────────────────────────────┐
│              Python Backend (FastAPI)                  │
│                                                       │
│  ┌─────────────── Application Layer ──────────────┐   │
│  │                                                │   │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  │   │
│  │  │ Pipeline │  │ EventBus  │  │  Session    │  │   │
│  │  │ Manager  │  │           │  │  Manager    │  │   │
│  │  └────┬─────┘  └─────┬─────┘  └────────────┘  │   │
│  └───────┼──────────────┼─────────────────────────┘   │
│          │              │                             │
│  ┌───────▼──────────────▼─────────────────────────┐   │
│  │              Domain Layer (Core)               │   │
│  │                                                │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │           Interfaces (Ports)             │  │   │
│  │  │  ┌─────────┐ ┌────────┐ ┌────────────┐  │  │   │
│  │  │  │ STT     │ │ LLM    │ │ Searcher   │  │  │   │
│  │  │  │ Port    │ │ Port   │ │ Port       │  │  │   │
│  │  │  └─────────┘ └────────┘ └────────────┘  │  │   │
│  │  │  ┌─────────┐ ┌────────────────────────┐  │  │   │
│  │  │  │Executor │ │ AudioCapture           │  │  │   │
│  │  │  │Port     │ │ Port                   │  │  │   │
│  │  │  └─────────┘ └────────────────────────┘  │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  │                                                │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │           Domain Models                  │  │   │
│  │  │  VoiceCommand, Intent, SearchResult,     │  │   │
│  │  │  Action, ExecutionResult                 │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
│                                                       │
│  ┌─────────────── Infrastructure Layer ───────────┐   │
│  │          (Adapters / Implementations)          │   │
│  │                                                │   │
│  │  ┌───────────┐ ┌──────────┐ ┌──────────────┐  │   │
│  │  │WhisperCpp │ │ClaudeAPI │ │ Everything   │  │   │
│  │  │Adapter    │ │Adapter   │ │ Adapter      │  │   │
│  │  └───────────┘ └──────────┘ └──────────────┘  │   │
│  │  ┌───────────┐ ┌──────────┐ ┌──────────────┐  │   │
│  │  │Ollama     │ │WinShell  │ │ SoundDevice  │  │   │
│  │  │Adapter    │ │Adapter   │ │ Adapter      │  │   │
│  │  └───────────┘ └──────────┘ └──────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

### 2.2 SOLID原则映射

| 原则 | 实现方式 |
|------|---------|
| **S** — 单一职责 | 每个Adapter只做一件事：WhisperCppAdapter只负责语音转文字，ClaudeAdapter只负责意图解析 |
| **O** — 开闭原则 | 通过Port接口扩展新实现（如新增Azure STT），无需修改Pipeline |
| **L** — 里氏替换 | 所有Adapter实现对应Port接口，可自由替换（如Claude↔Ollama） |
| **I** — 接口隔离 | STTPort只定义transcribe()，不混入搜索或执行方法 |
| **D** — 依赖反转 | Pipeline依赖抽象Port，不依赖具体Adapter；通过DI容器注入 |

### 2.3 核心Pipeline流程

```
AudioCapture → STT → LLM Intent → Search → Execute → Response
     │           │        │           │         │          │
  音频流      文本转写   意图解析    文件搜索   系统操作   结果反馈
```

每个步骤通过EventBus发布事件，前端实时订阅展示进度。

---

## 3. 项目目录结构

```
GotIt/
├── pyproject.toml                 # uv项目配置
├── gotit/                         # Python后端包
│   ├── __init__.py
│   ├── main.py                    # FastAPI入口 + 启动逻辑
│   ├── config.py                  # Pydantic Settings 配置
│   │
│   ├── domain/                    # 领域层（纯Python，零外部依赖）
│   │   ├── __init__.py
│   │   ├── models.py              # 领域模型：Intent, Action, SearchResult等
│   │   ├── ports.py               # 抽象接口：STTPort, LLMPort, SearchPort等
│   │   ├── events.py              # 领域事件定义
│   │   └── pipeline.py            # 核心Pipeline编排（依赖Port抽象）
│   │
│   ├── adapters/                  # 基础设施层（具体实现）
│   │   ├── __init__.py
│   │   ├── stt/
│   │   │   ├── __init__.py
│   │   │   ├── whisper_cpp.py     # whisper.cpp适配器
│   │   │   └── windows_stt.py     # Windows语音API适配器（MVP备选）
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── claude.py          # Claude API适配器
│   │   │   └── ollama.py          # Ollama本地LLM适配器
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   └── everything.py      # Everything CLI适配器
│   │   ├── executor/
│   │   │   ├── __init__.py
│   │   │   └── windows.py         # Windows Shell执行器
│   │   └── audio/
│   │       ├── __init__.py
│   │       └── sounddevice.py     # 音频采集适配器
│   │
│   ├── api/                       # API层
│   │   ├── __init__.py
│   │   ├── websocket.py           # WebSocket端点
│   │   └── routes.py              # REST端点（配置、历史等）
│   │
│   └── services/                  # 应用服务层
│       ├── __init__.py
│       ├── event_bus.py           # 事件总线
│       ├── container.py           # DI容器（依赖注入组装）
│       └── session.py             # 会话管理
│
├── frontend/                      # React前端
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html                 # Main Panel入口
│   ├── launcher.html              # Launcher Bar入口（独立窗口）
│   └── src/
│       ├── main.tsx               # Main Panel入口
│       ├── launcher.tsx           # Launcher Bar入口
│       ├── App.tsx                # Main Panel根组件
│       ├── LauncherApp.tsx        # Launcher Bar根组件
│       ├── hooks/
│       │   ├── useWebSocket.ts    # WebSocket连接管理
│       │   ├── useVoice.ts        # 语音状态管理
│       │   └── useTauriWindow.ts  # Tauri窗口切换控制
│       ├── components/
│       │   ├── launcher/
│       │   │   ├── InputBar.tsx       # 输入框（键盘+语音共用）
│       │   │   └── ModeIndicator.tsx  # 输入模式切换（麦克风/键盘）
│       │   ├── panel/
│       │   │   ├── ResultList.tsx      # 搜索结果列表
│       │   │   ├── PipelineProgress.tsx # Pipeline阶段进度
│       │   │   ├── ActionFeedback.tsx  # 执行结果反馈
│       │   │   └── SettingsPanel.tsx   # 设置面板
│       │   └── shared/
│       │       └── WaveformVisualizer.tsx # 语音波形动画
│       ├── stores/
│       │   └── appStore.ts        # Zustand状态管理
│       └── styles/
│           └── globals.css        # Tailwind CSS
│
├── src-tauri/                     # Tauri桌面壳（Rust）
│   ├── Cargo.toml
│   ├── tauri.conf.json            # 双窗口配置（launcher + main）
│   └── src/
│       ├── main.rs                # Tauri入口 + 双窗口管理
│       ├── tray.rs                # 系统托盘
│       └── windows.rs             # 窗口创建/切换/隐藏逻辑
│
├── models/                        # whisper.cpp模型文件（gitignore）
│   └── .gitkeep
│
├── tests/                         # 测试
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_pipeline.py
│   │   ├── test_models.py
│   │   └── test_intent_parsing.py
│   └── integration/
│       ├── test_stt.py
│       └── test_everything.py
│
└── prompt/                        # 设计文档
    └── plan/
        ├── idea.md
        └── plan.md
```

---

## 4. 核心模块设计

### 4.1 Domain Models（领域模型）

```python
# gotit/domain/models.py

class AudioChunk:
    data: bytes
    sample_rate: int
    timestamp: float

class Transcript:
    text: str
    language: str
    confidence: float

class Intent:
    action: ActionType          # search, open, run, navigate, system_control
    query: str | None           # 搜索关键词
    target: str | None          # 目标路径/程序
    filters: dict               # 额外过滤条件（文件类型、日期等）
    raw_text: str               # 原始语音文本

class ActionType(str, Enum):
    SEARCH = "search"
    OPEN_FILE = "open_file"
    OPEN_FOLDER = "open_folder"
    RUN_PROGRAM = "run_program"
    SYSTEM_CONTROL = "system_control"

class SearchResult:
    path: str
    filename: str
    size: int
    modified: datetime
    match_score: float

class ExecutionResult:
    success: bool
    action: ActionType
    message: str
    data: dict | None
```

### 4.2 Port接口（抽象层）

```python
# gotit/domain/ports.py

class STTPort(Protocol):
    async def transcribe(self, audio: AudioChunk) -> Transcript: ...
    async def start_stream(self) -> AsyncIterator[Transcript]: ...
    async def stop_stream(self) -> None: ...

class LLMPort(Protocol):
    async def parse_intent(self, text: str, context: list[str] | None = None) -> Intent: ...

class SearchPort(Protocol):
    async def search(self, query: str, filters: dict | None = None) -> list[SearchResult]: ...

class ExecutorPort(Protocol):
    async def execute(self, intent: Intent, targets: list[SearchResult]) -> ExecutionResult: ...

class AudioCapturePort(Protocol):
    async def start(self) -> AsyncIterator[AudioChunk]: ...
    async def stop(self) -> None: ...
    def list_devices(self) -> list[AudioDevice]: ...
```

### 4.3 Pipeline（核心编排）

```python
# gotit/domain/pipeline.py

class VoicePipeline:
    def __init__(
        self,
        audio: AudioCapturePort,
        stt: STTPort,
        llm: LLMPort,
        searcher: SearchPort,
        executor: ExecutorPort,
        event_bus: EventBus,
    ): ...

    async def run_once(self, audio: AudioChunk) -> ExecutionResult:
        # 1. 语音转文字
        transcript = await self.stt.transcribe(audio)
        await self.event_bus.publish(TranscriptEvent(transcript))

        # 2. 意图解析
        intent = await self.llm.parse_intent(transcript.text)
        await self.event_bus.publish(IntentEvent(intent))

        # 3. 搜索（如果需要）
        results = []
        if intent.action in (ActionType.SEARCH, ActionType.OPEN_FILE):
            results = await self.searcher.search(intent.query, intent.filters)
            await self.event_bus.publish(SearchEvent(results))

        # 4. 执行
        result = await self.executor.execute(intent, results)
        await self.event_bus.publish(ExecutionEvent(result))

        return result
```

### 4.4 EventBus（事件总线）

```python
# gotit/services/event_bus.py

class EventBus:
    async def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: type, handler: Callable) -> None: ...
    def unsubscribe(self, event_type: type, handler: Callable) -> None: ...
```

WebSocket处理器订阅EventBus，将事件实时推送到前端。

### 4.5 DI容器

```python
# gotit/services/container.py

class Container:
    def __init__(self, config: AppConfig):
        self.config = config

    def build(self) -> VoicePipeline:
        audio = SoundDeviceAdapter(self.config.audio)
        stt = WhisperCppAdapter(self.config.stt)
        llm = self._build_llm()
        searcher = EverythingAdapter(self.config.search)
        executor = WindowsExecutor(self.config.executor)
        event_bus = EventBus()
        return VoicePipeline(audio, stt, llm, searcher, executor, event_bus)

    def _build_llm(self) -> LLMPort:
        if self.config.llm.provider == "claude":
            return ClaudeAdapter(self.config.llm)
        elif self.config.llm.provider == "ollama":
            return OllamaAdapter(self.config.llm)
```

---

## 5. 前端UI设计

### 5.1 双窗口交互模型

采用 **Launcher Bar + Main Panel** 双窗口设计，类似 Spotlight / Raycast 的交互范式。
程序常驻后台（系统托盘），用户通过全局快捷键唤醒极简输入条，输入确认后再展开主面板处理结果。

#### 交互流程

```
[后台常驻] ──快捷键──▶ [Launcher Bar] ──确认──▶ [Main Panel] ──完成/Esc──▶ [后台常驻]
                         (输入阶段)              (处理+结果阶段)
```

#### 阶段说明

| 阶段 | 窗口 | 行为 |
|------|------|------|
| 待机 | 无窗口，仅托盘图标 | 监听全局快捷键，资源占用极低 |
| 输入 | Launcher Bar | 极简浮动条，屏幕居中偏上，获取用户指令 |
| 处理 | Main Panel | Launcher Bar消失，主面板展开显示进度和结果 |
| 完成 | Main Panel自动收起 | 执行完毕后延迟收起，或用户按Esc关闭 |

---

### 5.2 Launcher Bar（输入条）

极简浮动窗口，仅负责**采集用户输入**。无边框、半透明、屏幕居中上方。

```
  ┌─────────────────────────────────────────────────┐
  │  🎤  │  打开昨天的设计文档_                  ⏎  │
  └─────────────────────────────────────────────────┘
```

**设计要点：**

- 尺寸固定：宽600px，高48-56px，圆角，毛玻璃背景
- 左侧：输入模式指示器（麦克风/键盘图标，点击切换）
- 中间：文本输入框（支持键盘直接打字 或 语音实时转写）
- 右侧：确认按钮（Enter提交）
- 焦点外点击 或 Esc → 关闭Launcher，回到待机

**输入模式：**

| 模式 | 触发方式 | 行为 |
|------|---------|------|
| 键盘输入 | 唤醒后直接打字 | 打字 → Enter确认 |
| 语音输入 | 点击麦克风图标 / 按住快捷键 | 录音 → 实时转写显示在输入框 → 松手或停顿自动停止 → Enter确认 |

**语音转写在Launcher Bar中的表现：**

```
  录音中：
  ┌─────────────────────────────────────────────────┐
  │  🔴  │  打开昨天的...  ░░░░░░░░░░░░░░░░░░░  ⏎  │
  └─────────────────────────────────────────────────┘

  转写完成，等待确认：
  ┌─────────────────────────────────────────────────┐
  │  🎤  │  打开昨天的设计文档                    ⏎  │
  └─────────────────────────────────────────────────┘
```

用户可以在转写完成后**编辑文字**修正识别错误，再按Enter确认。这给了用户最大的自由度。

---

### 5.3 Main Panel（主面板）

用户在Launcher Bar按下Enter后，Launcher Bar关闭，Main Panel在屏幕中央展开。

```
  ┌────────────────────────────────────────────────────┐
  │  GotIt                                          x  │
  ├────────────────────────────────────────────────────┤
  │                                                    │
  │  "打开昨天的设计文档"                    正在搜索... │
  │                                                    │
  │  ┌────────────────────────────────────────────┐    │
  │  │  📄 design_v2.docx                  [打开] │    │
  │  │     D:\Docs\2026-04\   ·  128KB  ·  昨天   │    │
  │  ├────────────────────────────────────────────┤    │
  │  │  📄 design_notes.md                 [打开] │    │
  │  │     D:\Projects\doc\   ·  32KB   ·  昨天   │    │
  │  └────────────────────────────────────────────┘    │
  │                                                    │
  │  ✅ 已打开 design_v2.docx                          │
  └────────────────────────────────────────────────────┘
```

**Main Panel职责：**

- 显示原始输入文本
- Pipeline各阶段进度（意图解析 → 搜索 → 执行）
- 搜索结果列表（可点击/键盘选择）
- 执行结果反馈
- 执行完成后3秒自动收起（可配置），或用户手动关闭

**Main Panel状态流转：**

```
[展开] → [解析中...] → [搜索中...] → [结果列表] → [执行反馈] → [自动收起]
```

---

### 5.4 完整UI状态机

```
                    ┌──────────┐
          ┌────────│  Dormant  │◄──────────────────┐
          │        │ (后台待机) │                    │
          │        └──────────┘                    │
          │ 快捷键                          Esc/完成 │
          ▼                                        │
   ┌──────────────┐                                │
   │ Launcher Bar  │───── Enter ────▶ ┌──────────┐ │
   │ (输入阶段)     │                  │Main Panel│──┘
   └──────┬───────┘                  │(处理阶段) │
          │                          └──────────┘
          │ Esc/失焦
          ▼
   ┌──────────┐
   │  Dormant  │
   └──────────┘
```

### 5.5 快捷键

| 快捷键 | 作用域 | 功能 |
|--------|--------|------|
| `Ctrl+Shift+G` | 全局 | 唤醒Launcher Bar |
| `Enter` | Launcher Bar | 确认输入，展开Main Panel |
| `Escape` | Launcher Bar / Main Panel | 关闭当前窗口，回到待机 |
| `↑/↓` | Main Panel | 导航搜索结果 |
| `Enter` | Main Panel | 打开选中的搜索结果 |
| `Ctrl+Shift+G` | Main Panel | 回到Launcher Bar重新输入 |

---

## 6. 配置管理

```python
# gotit/config.py

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GOTIT_",
        env_file=".env",
        env_nested_delimiter="__",
    )

    stt: STTConfig = STTConfig()
    llm: LLMConfig = LLMConfig()
    search: SearchConfig = SearchConfig()
    audio: AudioConfig = AudioConfig()

class STTConfig(BaseModel):
    engine: str = "whisper_cpp"     # whisper_cpp | windows
    model_path: str = "models/ggml-base.bin"
    language: str = "zh"

class LLMConfig(BaseModel):
    provider: str = "claude"        # claude | ollama
    model: str = "claude-sonnet-4-6"
    api_key: str = ""               # 从环境变量读取
    system_prompt: str = ""         # 自定义系统提示

class SearchConfig(BaseModel):
    everything_path: str = "es.exe"  # Everything CLI路径
    max_results: int = 20

class AudioConfig(BaseModel):
    device_index: int | None = None  # None=默认设备
    sample_rate: int = 16000
    channels: int = 1
```

---

## 7. LLM Prompt设计

### 7.1 意图解析System Prompt

```
你是GotIt语音助手的意图解析引擎。
用户通过语音输入指令，你需要将其解析为结构化的JSON指令。

支持的动作类型：
- search: 搜索文件（返回结果列表）
- open_file: 搜索并打开特定文件
- open_folder: 打开文件夹
- run_program: 启动程序
- system_control: 系统操作（如调节音量）

你必须输出以下JSON格式：
{
  "action": "动作类型",
  "query": "搜索关键词（Everything语法）",
  "target": "目标路径或程序名（如果明确指定）",
  "filters": {
    "ext": "文件扩展名",
    "path": "路径过滤",
    "date_modified": "日期范围"
  },
  "confidence": 0.0-1.0
}

Everything搜索语法提示：
- 文件名搜索：直接输入关键词
- 扩展名过滤：ext:pdf
- 路径过滤：path:D:\Projects
- 日期过滤：dm:today, dm:thisweek
- 通配符：*.ts
```

---

## 8. 分阶段实施计划

### Phase 0: 项目脚手架（第1天）

**目标：** 搭建项目骨架，跑通开发环境。

- [ ] 初始化uv项目，配置pyproject.toml
- [ ] 创建目录结构（domain/adapters/api/services）
- [ ] 定义领域模型和Port接口
- [ ] 配置pytest + structlog
- [ ] 创建前端项目（React + Vite + TypeScript）
- [ ] 配置Tailwind CSS + Zustand
- [ ] 编写domain层单元测试骨架

**产出：** 可运行的空项目骨架，`uv run pytest` 通过。

---

### Phase 1: MVP命令行版（第2-4天）

**目标：** 在终端中实现完整的 语音→搜索→执行 流程。

#### 1.1 音频采集模块
- [ ] 实现SoundDeviceAdapter（AudioCapturePort）
- [ ] 支持按键触发录音（空格键按住说话）
- [ ] VAD（Voice Activity Detection）自动停止

#### 1.2 STT模块
- [ ] 下载whisper.cpp ggml-base模型
- [ ] 实现WhisperCppAdapter（STTPort）
- [ ] 支持中文+英文混合识别
- [ ] 单元测试：给定wav文件 → 验证转写文本

#### 1.3 LLM意图解析
- [ ] 实现ClaudeAdapter（LLMPort）
- [ ] 设计意图解析prompt（见第7节）
- [ ] 支持多轮上下文（最近3条指令）
- [ ] 单元测试：给定文本 → 验证Intent结构

#### 1.4 Everything搜索
- [ ] 实现EverythingAdapter（SearchPort）
- [ ] 封装es.exe CLI调用
- [ ] 支持文件名、扩展名、路径、日期过滤
- [ ] 集成测试：搜索已知文件 → 验证结果

#### 1.5 Windows执行器
- [ ] 实现WindowsExecutor（ExecutorPort）
- [ ] 支持：打开文件、打开文件夹、启动程序
- [ ] 安全校验：白名单路径/程序

#### 1.6 Pipeline集成
- [ ] 实现VoicePipeline编排
- [ ] 实现EventBus
- [ ] 实现DI Container
- [ ] 端到端测试：录音→转写→搜索→打开

**产出：** 终端运行 `uv run gotit`，说"打开昨天的设计文档"，系统搜索并打开文件。

---

### Phase 2: WebSocket API层（第5-6天）

**目标：** 将MVP包装为API服务，支持前端接入。

- [ ] FastAPI应用初始化
- [ ] WebSocket端点：`/ws/voice`
  - 接收音频流（binary frames）
  - 推送事件（transcript/intent/results/execution）
- [ ] REST端点：
  - `GET /api/config` — 获取配置
  - `PUT /api/config` — 更新配置
  - `GET /api/devices` — 列出音频设备
  - `GET /api/history` — 操作历史
- [ ] WebSocket消息协议定义（JSON）
- [ ] CORS配置

**WebSocket消息格式：**

```json
// 服务端 → 客户端
{"type": "transcript", "data": {"text": "打开设计文档", "partial": false}}
{"type": "intent",     "data": {"action": "open_file", "query": "设计文档"}}
{"type": "results",    "data": [{"path": "D:\\Docs\\design.md", "name": "design.md"}]}
{"type": "executed",   "data": {"success": true, "message": "已打开 design.md"}}
{"type": "error",      "data": {"message": "搜索失败", "code": "SEARCH_ERROR"}}

// 客户端 → 服务端
{"type": "start_voice"}
{"type": "stop_voice"}
{"type": "audio_chunk", "data": "<base64>"}
{"type": "execute",     "data": {"index": 0}}  // 选择第N个结果执行
{"type": "cancel"}
```

**产出：** 后端API服务运行在 `localhost:8765`，可通过WebSocket调试工具验证。

---

### Phase 3: 前端UI（第7-10天）

**目标：** 构建双窗口交互界面（Launcher Bar + Main Panel）。

#### 3.1 Launcher Bar窗口
- [ ] InputBar组件 — 文本输入框
  - 自动聚焦，唤醒即可打字
  - Enter提交，Esc关闭
  - 支持显示语音转写的实时文字
- [ ] ModeIndicator组件 — 输入模式切换
  - 麦克风图标 ↔ 键盘图标
  - 点击切换，录音时显示红点+波形
- [ ] 窗口样式：无边框、圆角、半透明毛玻璃背景、居中偏上

#### 3.2 Main Panel窗口
- [ ] PipelineProgress — 各阶段进度指示
  - 意图解析 → 搜索 → 执行，依次点亮
- [ ] ResultList — 搜索结果列表
  - 文件图标、名称、路径、大小、修改时间
  - 键盘导航（↑/↓）+ 鼠标点击
  - Enter或双击打开
- [ ] ActionFeedback — 执行结果反馈
  - 成功/失败动画
  - 完成后3秒自动收起窗口（可配置）

#### 3.3 窗口切换逻辑
- [ ] useTauriWindow hook — 封装Launcher↔Panel切换
  - Launcher确认 → 隐藏Launcher、显示Panel
  - Panel关闭/完成 → 隐藏Panel、回到待机
  - Panel中按快捷键 → 隐藏Panel、重新显示Launcher

#### 3.4 状态管理与样式
- [ ] Zustand store：appState, voiceState, settingsState
- [ ] WebSocket连接管理hook（两个窗口共享同一连接）
- [ ] Tailwind CSS + 深色主题
- [ ] 窗口展开/收起过渡动画

**产出：** 浏览器访问可看到双窗口UI，Launcher输入→Panel展示结果。

---

### Phase 4: Tauri桌面应用（第11-13天）

**目标：** 打包为独立桌面应用，实现双窗口常驻后台体验。

#### 4.1 Tauri双窗口配置
- [ ] Tauri v2项目初始化
- [ ] tauri.conf.json配置两个窗口：
  - `launcher` — 无边框、透明、置顶、初始隐藏、不显示在任务栏、宽600x高56
  - `main` — 无边框、初始隐藏、居中、宽700x高500
- [ ] windows.rs — 窗口生命周期管理：
  - `show_launcher()` → 显示launcher窗口并聚焦
  - `hide_launcher_show_main(query)` → 隐藏launcher、显示main、传递输入内容
  - `hide_all()` → 全部隐藏回到待机

#### 4.2 全局快捷键 + 系统托盘
- [ ] 全局快捷键注册（Ctrl+Shift+G）→ 调用show_launcher()
- [ ] 系统托盘：
  - 左键点击 → 唤醒Launcher
  - 右键菜单 → 设置 / 历史 / 退出

#### 4.3 后端进程管理
- [ ] Tauri启动时spawn Python后端进程
- [ ] 健康检查（HTTP ping）+ 崩溃自动重启
- [ ] Tauri退出时优雅关闭Python进程

#### 4.4 打包
- [ ] 开机自启配置（可选）
- [ ] 应用图标
- [ ] MSI/NSIS安装包构建

**产出：** 双击GotIt.exe启动，托盘常驻，Ctrl+Shift+G唤出输入条，确认后展开主面板。

---

### Phase 5: 体验优化（第14-16天）

**目标：** 打磨细节，提升可用性。

- [ ] 流式STT（实时字幕效果）
- [ ] LLM流式输出（intent解析中间态）
- [ ] 音频预处理（降噪、自动增益）
- [ ] 自定义唤醒词（可选）
- [ ] 操作历史记录 + 快速重做
- [ ] 常用指令收藏
- [ ] 错误恢复策略（重试/fallback）
- [ ] 离线LLM集成（Ollama + qwen2.5）
- [ ] 性能监控面板（延迟、资源占用）

---

### Phase 6: 扩展能力（未来）

**目标：** 向AI Agent方向演进。

- [ ] 插件系统（Plugin API）
- [ ] 多步骤任务链（Task Chain）
- [ ] 上下文记忆（对话历史 + 用户偏好）
- [ ] 自定义动作注册
- [ ] 剪贴板集成
- [ ] 屏幕内容感知（OCR + 截图理解）
- [ ] 多语言TTS回复

---

## 9. 关键技术决策

### 9.1 前后端分离 vs 纯Python

**选择：前后端分离（Python后端 + React前端 + Tauri壳）**

理由：
- UI定制灵活度高，React生态组件丰富
- 前后端可独立迭代
- Tauri体积小（vs Electron ~150MB，Tauri ~5MB）
- 后端可独立运行（支持纯API模式、CLI模式）

### 9.2 双窗口（Launcher + Panel）vs 单窗口

**选择：双窗口**

理由：
- Launcher Bar极简轻量，唤醒成本极低（类似Spotlight），不打断用户当前工作
- 用户可以在Launcher中**编辑和修正**语音转写文字，再确认提交，拥有最大控制权
- 输入阶段和处理阶段职责分离，UI复杂度各自可控
- Main Panel仅在需要时展开，避免不必要的视觉干扰
- Tauri v2原生支持多窗口管理，实现成本低

### 9.4 音频采集在前端 vs 后端

**选择：后端采集**

理由：
- Python sounddevice直接访问系统音频设备，延迟更低
- 避免WebView音频API的兼容性问题
- 音频数据不需要经过WebSocket传输（本地到本地）

### 9.5 实时流式 vs 录完再传

**选择：Phase 1用录完再传（简单），Phase 5升级为流式**

理由：
- 录完再传实现简单，MVP够用
- 流式需要处理VAD、partial results，复杂度高
- 分阶段渐进式实现

### 9.6 Everything SDK vs CLI

**选择：CLI（es.exe）优先，SDK作为后续优化**

理由：
- CLI集成简单，subprocess调用即可
- SDK需要处理DLL加载、ctypes绑定，复杂度高
- CLI性能已足够（毫秒级）
- 后续可迁移到SDK以获得更好的性能和功能

---

## 10. 性能目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| Launcher唤醒延迟 | < 200ms | 快捷键到窗口可见+可输入 |
| 语音转文字延迟 | < 1s (base模型) | whisper.cpp CPU推理 |
| 意图解析延迟 | < 2s | Claude API (网络延迟为主) |
| Everything搜索 | < 100ms | 本地索引 |
| 端到端延迟 | < 4s | 语音停止 → 结果显示 |
| 内存占用 | < 300MB | 后端常驻进程 |
| CPU占用（待机） | < 1% | 无语音输入时 |
| 启动时间 | < 3s | 应用启动到可用 |

---

## 11. 安全设计

- 执行层白名单：只允许打开文件/文件夹/预定义程序，不允许任意命令执行
- API Key通过环境变量管理，不硬编码
- WebSocket仅监听localhost
- 日志脱敏：不记录完整文件路径到外部
- Tauri CSP策略：限制WebView的网络访问

---

## 12. 测试策略

| 层级 | 工具 | 覆盖范围 |
|------|------|---------|
| 单元测试 | pytest | Domain层（models, pipeline逻辑） |
| 集成测试 | pytest + fixtures | Adapter层（实际调用whisper/everything） |
| API测试 | httpx + websockets | WebSocket协议验证 |
| E2E测试 | 手动 | 完整语音→执行流程 |
| 前端测试 | Vitest + Testing Library | 组件渲染 + 状态管理 |

---

## 13. 立即可执行的第一步

```bash
# 1. 初始化项目
uv init gotit
cd gotit

# 2. 添加核心依赖
uv add fastapi uvicorn[standard] pydantic-settings structlog
uv add pywhispercpp sounddevice numpy
uv add anthropic httpx
uv add --dev pytest pytest-asyncio ruff

# 3. 创建目录结构
mkdir -p gotit/{domain,adapters/{stt,llm,search,executor,audio},api,services}
mkdir -p tests/{unit,integration}
mkdir -p models

# 4. 开始编码（从domain层开始 → 自底向上）
```

> 从 `gotit/domain/models.py` 和 `gotit/domain/ports.py` 开始编写，确保核心抽象正确后再实现Adapter。
