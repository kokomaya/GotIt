
# GotIt 详细实施任务清单（Task Breakdown）

> 基于 plan.md 的分阶段实施计划，拆解为可逐步执行、可追踪的具体任务。
> 每个任务用 `- [ ]` 标记未完成，`- [x]` 标记已完成。

---

## Phase 0: 项目脚手架（第1天）

> 目标：搭建项目骨架，跑通开发环境。

### 0.1 Python后端初始化

- [x] **0.1.1** 在项目根目录执行 `uv init`，生成 `pyproject.toml`
- [x] **0.1.2** 配置 `pyproject.toml`：
  - 项目名 `gotit`，Python `>=3.12`
  - 添加核心依赖：`fastapi`, `uvicorn[standard]`, `pydantic-settings`, `structlog`
  - 添加AI依赖：`anthropic`, `httpx`
  - 添加音频依赖：`sounddevice`, `numpy`（`pywhispercpp` 延迟到Phase 1安装，需C++编译工具链）
  - 添加开发依赖：`pytest`, `pytest-asyncio`, `ruff`
  - 配置 `[project.scripts]` 入口：`gotit = "gotit.main:main"`
- [x] **0.1.3** 执行 `uv sync` 安装所有依赖，确认无冲突
- [x] **0.1.4** 配置 `ruff` 规则（在 `pyproject.toml` 中添加 `[tool.ruff]` 段）

### 0.2 后端目录结构创建

- [x] **0.2.1** 创建 `gotit/` 包目录 + `__init__.py`
- [x] **0.2.2** 创建 `gotit/domain/` 目录 + `__init__.py`
  - 创建空文件：`models.py`, `ports.py`, `events.py`, `pipeline.py`
- [x] **0.2.3** 创建 `gotit/adapters/` 目录结构：
  - `adapters/__init__.py`
  - `adapters/stt/__init__.py`, `adapters/stt/whisper_cpp.py`
  - `adapters/llm/__init__.py`, `adapters/llm/claude.py`, `adapters/llm/ollama.py`
  - `adapters/search/__init__.py`, `adapters/search/everything.py`
  - `adapters/executor/__init__.py`, `adapters/executor/windows.py`
  - `adapters/audio/__init__.py`, `adapters/audio/sounddevice.py`
- [x] **0.2.4** 创建 `gotit/api/` 目录：`__init__.py`, `websocket.py`, `routes.py`
- [x] **0.2.5** 创建 `gotit/services/` 目录：`__init__.py`, `event_bus.py`, `container.py`, `session.py`
- [x] **0.2.6** 创建 `gotit/main.py`（FastAPI入口占位）
- [x] **0.2.7** 创建 `gotit/config.py`（Pydantic Settings占位）

### 0.3 Domain层骨架编写

- [x] **0.3.1** 编写 `gotit/domain/models.py`：
  - 定义 `AudioChunk` dataclass（data, sample_rate, timestamp）
  - 定义 `Transcript` dataclass（text, language, confidence）
  - 定义 `ActionType` 枚举（SEARCH, OPEN_FILE, OPEN_FOLDER, RUN_PROGRAM, SYSTEM_CONTROL）
  - 定义 `Intent` dataclass（action, query, target, filters, raw_text, confidence）
  - 定义 `SearchResult` dataclass（path, filename, size, modified, match_score）
  - 定义 `ExecutionResult` dataclass（success, action, message, data）
  - 额外定义 `AudioDevice` dataclass（index, name, is_default）
- [x] **0.3.2** 编写 `gotit/domain/ports.py`：
  - 定义 `STTPort` Protocol（transcribe, start_stream, stop_stream）
  - 定义 `LLMPort` Protocol（parse_intent）
  - 定义 `SearchPort` Protocol（search）
  - 定义 `ExecutorPort` Protocol（execute）
  - 定义 `AudioCapturePort` Protocol（start, stop, list_devices）
- [x] **0.3.3** 编写 `gotit/domain/events.py`：
  - 定义 `DomainEvent` 基类（timestamp, event_id）
  - 定义 `TranscriptEvent`, `IntentEvent`, `SearchEvent`, `ExecutionEvent`, `ErrorEvent`
- [x] **0.3.4** 编写 `gotit/domain/pipeline.py`：
  - `VoicePipeline` 类（构造函数接收所有Port + EventBus）
  - `run_once(audio)` 完整实现：STT → Intent → Search → Execute + 事件发布
  - `run_from_text(text)` 完整实现：跳过STT，直接从文本开始Pipeline
  - `_run_from_transcript()` 内部方法：共享的Intent→Search→Execute逻辑 + 错误处理
  - 额外实现 `gotit/services/event_bus.py`（EventBus: publish/subscribe/unsubscribe）

### 0.4 配置与日志

- [ ] **0.4.1** 编写 `gotit/config.py`：
  - `AppConfig(BaseSettings)` 含 env_prefix="GOTIT_"
  - `STTConfig`, `LLMConfig`, `SearchConfig`, `AudioConfig`, `UIConfig` 子配置
  - `UIConfig` 包含 `auto_close_delay: int = 3`（Main Panel自动收起秒数）
- [ ] **0.4.2** 创建 `.env.example` 文件，列出所有环境变量模板
- [ ] **0.4.3** 配置 structlog（在 `gotit/main.py` 中初始化）

### 0.5 测试骨架

- [ ] **0.5.1** 创建 `tests/conftest.py`（共享fixture：mock ports, test config）
- [ ] **0.5.2** 创建 `tests/unit/test_models.py`（验证模型创建和序列化）
- [ ] **0.5.3** 创建 `tests/unit/test_pipeline.py`（mock所有port，验证pipeline编排）
- [ ] **0.5.4** 创建 `tests/unit/test_intent_parsing.py`（占位）
- [ ] **0.5.5** 创建 `tests/integration/` 目录 + 占位文件
- [ ] **0.5.6** 执行 `uv run pytest`，确认全部通过

### 0.6 前端项目初始化

- [ ] **0.6.1** 在 `frontend/` 目录执行 `npm create vite@latest . -- --template react-ts`
- [ ] **0.6.2** 安装核心依赖：`npm install zustand`
- [ ] **0.6.3** 安装Tailwind CSS v4 + 配置
- [ ] **0.6.4** 创建前端目录结构：
  - `src/hooks/`, `src/components/launcher/`, `src/components/panel/`, `src/components/shared/`
  - `src/stores/`
- [ ] **0.6.5** 创建 `launcher.html` + `src/launcher.tsx` + `src/LauncherApp.tsx`（Vite多入口）
- [ ] **0.6.6** 配置 `vite.config.ts` 多入口（`index.html` + `launcher.html`）
- [ ] **0.6.7** 执行 `npm run dev`，确认两个入口均可访问

### 0.7 其他

- [x] **0.7.1** 创建 `models/.gitkeep` + 更新 `.gitignore`（添加 `models/*.bin`）
- [ ] **0.7.2** 创建初始 git commit：`chore: project scaffold`

### Phase 0 验收标准

- [ ] `uv run pytest` 全部通过（≥5个测试用例）
- [ ] `uv run gotit` 可启动（打印 "GotIt starting..." 即可）
- [ ] `npm run dev` 前端可访问 `localhost:5173`（index）和 `localhost:5173/launcher.html`（launcher）
- [ ] 目录结构完整，所有占位文件已创建

---

## Phase 1: MVP命令行版（第2-4天）

> 目标：在终端中实现完整的 语音→搜索→执行 流程。

### 1.1 音频采集模块

- [ ] **1.1.1** 编写 `gotit/adapters/audio/sounddevice.py`：
  - `SoundDeviceAdapter` 实现 `AudioCapturePort`
  - `start()` 方法：打开音频流，yield AudioChunk
  - `stop()` 方法：关闭音频流
  - `list_devices()` 方法：返回可用音频设备列表
- [ ] **1.1.2** 实现按键触发录音：
  - 空格键按住开始录音，松开停止
  - 使用 `keyboard` 或 `pynput` 库监听按键
- [ ] **1.1.3** 实现VAD（Voice Activity Detection）：
  - 基于音量阈值的简单VAD
  - 静音超过1.5秒自动停止录音
- [ ] **1.1.4** 编写集成测试：录制3秒音频 → 验证AudioChunk数据完整

### 1.2 STT模块（whisper.cpp）

- [ ] **1.2.1** 下载whisper.cpp ggml-base模型文件到 `models/` 目录
  - 编写下载脚本 `scripts/download_model.py`
- [ ] **1.2.2** 编写 `gotit/adapters/stt/whisper_cpp.py`：
  - `WhisperCppAdapter` 实现 `STTPort`
  - 构造函数：加载模型（model_path, language）
  - `transcribe(audio)` 方法：AudioChunk → Transcript
- [ ] **1.2.3** 支持中文 + 英文混合识别配置
- [ ] **1.2.4** 编写单元测试：
  - 准备测试用wav文件（中文短句、英文短句、中英混合）
  - 测试：wav文件 → transcribe() → 验证 Transcript.text 包含预期关键词
- [ ] **1.2.5** 性能基准测试：记录base模型在CPU上的推理延迟（目标 < 1s）

### 1.3 LLM意图解析

- [ ] **1.3.1** 编写 `gotit/adapters/llm/claude.py`：
  - `ClaudeAdapter` 实现 `LLMPort`
  - 构造函数：初始化 anthropic client（api_key, model）
  - `parse_intent(text, context)` 方法：文本 → Intent
- [ ] **1.3.2** 设计并编写意图解析System Prompt：
  - 存放在 `gotit/adapters/llm/prompts/intent_system.txt`
  - 包含：动作类型定义、JSON输出格式、Everything语法提示
- [ ] **1.3.3** 实现JSON响应解析：
  - 解析LLM返回的JSON → Intent对象
  - 错误处理：JSON解析失败时的回退策略
- [ ] **1.3.4** 支持多轮上下文：最近3条指令作为context传入
- [ ] **1.3.5** 编写单元测试（mock API响应）：
  - "打开昨天的设计文档" → Intent(action=OPEN_FILE, query="设计文档", filters={date_modified: "yesterday"})
  - "搜索所有PDF文件" → Intent(action=SEARCH, filters={ext: "pdf"})
  - "打开Visual Studio Code" → Intent(action=RUN_PROGRAM, target="code")
  - "打开D盘的项目文件夹" → Intent(action=OPEN_FOLDER, target="D:\\Projects")

### 1.4 Everything搜索

- [ ] **1.4.1** 确认 Everything 和 es.exe（命令行工具）已安装
  - 编写检测脚本：检查 Everything 服务是否运行 + es.exe 是否在PATH中
- [ ] **1.4.2** 编写 `gotit/adapters/search/everything.py`：
  - `EverythingAdapter` 实现 `SearchPort`
  - `search(query, filters)` 方法：构建 es.exe 命令 → subprocess调用 → 解析输出
- [ ] **1.4.3** 实现查询构建器：
  - 将 Intent.filters 转换为 Everything 搜索语法
  - 支持：文件名、扩展名（ext:）、路径（path:）、日期（dm:）、通配符
- [ ] **1.4.4** 实现结果解析器：
  - 解析 es.exe 输出（文件路径列表）→ 填充 SearchResult 对象
  - 获取文件元信息（大小、修改时间）
- [ ] **1.4.5** 编写集成测试：
  - 搜索已知存在的文件 → 验证返回结果包含该文件
  - 搜索带扩展名过滤 → 验证结果全部符合
  - 搜索不存在的文件 → 验证返回空列表

### 1.5 Windows执行器

- [ ] **1.5.1** 编写 `gotit/adapters/executor/windows.py`：
  - `WindowsExecutor` 实现 `ExecutorPort`
  - `execute(intent, targets)` 方法：根据ActionType执行不同操作
- [ ] **1.5.2** 实现各Action处理器：
  - `OPEN_FILE`：使用 `os.startfile()` 打开文件
  - `OPEN_FOLDER`：使用 `subprocess` 调用 `explorer.exe` 打开文件夹
  - `RUN_PROGRAM`：使用 `subprocess.Popen()` 启动程序
  - `SEARCH`：仅返回搜索结果，不执行操作
- [ ] **1.5.3** 实现安全校验：
  - 定义允许执行的操作白名单
  - 禁止执行任意Shell命令
  - 路径合法性检查（防止路径遍历）
- [ ] **1.5.4** 编写单元测试（mock subprocess）：
  - 测试打开文件调用了正确的系统API
  - 测试危险路径被拒绝

### 1.6 Pipeline集成

- [ ] **1.6.1** 实现 `gotit/services/event_bus.py`：
  - `EventBus` 类：publish/subscribe/unsubscribe
  - 支持异步handler
  - 支持多个handler订阅同一事件类型
- [ ] **1.6.2** 实现 `gotit/domain/pipeline.py` 完整逻辑：
  - `run_once(audio)` 方法：AudioChunk → Transcript → Intent → Search → Execute
  - `run_from_text(text)` 方法：跳过音频/STT步骤，直接从文本开始Pipeline
  - 每步发布对应事件到EventBus
  - 错误处理：每步失败时发布ErrorEvent并终止
- [ ] **1.6.3** 实现 `gotit/services/container.py`：
  - `Container` 类：根据AppConfig组装所有Adapter → 构建VoicePipeline
  - `_build_stt()`, `_build_llm()`, `_build_searcher()`, `_build_executor()` 工厂方法
- [ ] **1.6.4** 实现CLI入口 `gotit/main.py`：
  - 命令行模式：启动后监听键盘（空格键录音）
  - 打印每步结果到终端
  - 支持 `--text` 参数直接输入文本（跳过语音）
- [ ] **1.6.5** 端到端集成测试：
  - 文本模式：`--text "打开记事本"` → 验证记事本被启动
  - 文本模式：`--text "搜索所有py文件"` → 验证结果列表输出
- [ ] **1.6.6** 创建 git commit：`feat: MVP command-line version`

### Phase 1 验收标准

- [ ] `uv run gotit --text "打开记事本"` → 记事本成功打开
- [ ] `uv run gotit --text "搜索py文件"` → 终端打印出搜索结果列表
- [ ] `uv run gotit`（语音模式）→ 按空格说话 → 转写文本显示 → 搜索/执行
- [ ] 所有单元测试通过（≥15个测试用例）
- [ ] STT延迟 < 1s（base模型，CPU）

---

## Phase 2: WebSocket API层（第5-6天）

> 目标：将MVP包装为API服务，支持前端接入。

### 2.1 FastAPI应用搭建

- [ ] **2.1.1** 编写 `gotit/main.py` FastAPI应用：
  - 创建FastAPI实例
  - 集成structlog中间件
  - 生命周期管理：startup时初始化Container + Pipeline
  - 配置CORS（允许localhost来源）
- [ ] **2.1.2** 实现启动入口：
  - `main()` 函数：解析命令行参数
  - `--mode cli` 进入命令行模式
  - `--mode server`（默认）启动FastAPI服务
  - 默认监听 `localhost:8765`

### 2.2 REST端点

- [ ] **2.2.1** 编写 `gotit/api/routes.py`：
  - `GET /api/health` — 健康检查（返回版本、运行时间）
  - `GET /api/config` — 返回当前配置（脱敏，不返回api_key）
  - `PUT /api/config` — 更新运行时配置（部分字段）
  - `GET /api/devices` — 返回音频设备列表
  - `GET /api/history` — 返回最近操作历史（内存缓存，最近50条）
- [ ] **2.2.2** 编写API测试（httpx AsyncClient）：
  - 测试每个端点的正常响应
  - 测试配置更新

### 2.3 WebSocket端点

- [ ] **2.3.1** 定义WebSocket消息协议（JSON schema）：
  - 服务端→客户端消息类型：`transcript`, `intent`, `results`, `executed`, `error`, `state`
  - 客户端→服务端消息类型：`submit_text`, `start_voice`, `stop_voice`, `execute`, `cancel`
- [ ] **2.3.2** 编写 `gotit/api/websocket.py`：
  - `WebSocketManager` 类：管理连接、广播事件
  - `/ws/pipeline` 端点：
    - 接收 `submit_text` → 调用 `pipeline.run_from_text(text)`
    - 接收 `start_voice` → 开始音频采集
    - 接收 `stop_voice` → 停止采集，触发Pipeline
    - 接收 `execute` → 执行选中的搜索结果
    - 接收 `cancel` → 取消当前操作
  - 将EventBus事件转发为WebSocket消息
- [ ] **2.3.3** 实现连接生命周期管理：
  - 连接建立时注册EventBus订阅
  - 连接断开时取消订阅 + 清理资源
  - 心跳机制（30秒ping/pong）
- [ ] **2.3.4** 编写WebSocket集成测试：
  - 连接 → 发送 `submit_text` → 验证收到 transcript/intent/results 消息序列
  - 连接 → 发送 `cancel` → 验证Pipeline中止
  - 断开重连测试

### 2.4 会话管理

- [ ] **2.4.1** 编写 `gotit/services/session.py`：
  - `SessionManager` 类：管理操作历史
  - 记录每次Pipeline执行（输入文本、意图、结果、状态）
  - 内存存储，最近50条
- [ ] **2.4.2** 创建 git commit：`feat: WebSocket API layer`

### Phase 2 验收标准

- [ ] `uv run gotit` 启动后，`localhost:8765/api/health` 返回正常
- [ ] WebSocket客户端工具连接 `ws://localhost:8765/ws/pipeline`，发送 `{"type":"submit_text","data":{"text":"搜索py文件"}}` → 收到完整事件序列
- [ ] REST端点全部可用
- [ ] API测试全部通过

---

## Phase 3: 前端UI（第7-10天）

> 目标：构建双窗口交互界面（Launcher Bar + Main Panel）。

### 3.1 前端基础设施

- [ ] **3.1.1** 编写 `src/stores/appStore.ts`（Zustand）：
  - `appState`：当前阶段（dormant/launcher/processing/results/executed）
  - `voiceState`：录音状态（idle/recording/transcribing）
  - `inputText`：当前输入文本
  - `transcript`：实时转写文本（partial + final）
  - `intent`：解析后的意图
  - `results`：搜索结果列表
  - `selectedIndex`：选中的结果索引
  - `executionResult`：执行结果
  - `error`：错误信息
- [ ] **3.1.2** 编写 `src/hooks/useWebSocket.ts`：
  - 管理WebSocket连接（自动重连）
  - 接收服务端消息 → 更新Zustand store
  - 暴露发送方法：`submitText()`, `startVoice()`, `stopVoice()`, `executeResult()`, `cancel()`
- [ ] **3.1.3** 编写 `src/hooks/useVoice.ts`：
  - 语音状态管理
  - 联动WebSocket的start/stop voice
  - 暴露状态：isRecording, isTranscribing

### 3.2 Launcher Bar窗口

- [ ] **3.2.1** 编写 `src/LauncherApp.tsx`：
  - 根组件，渲染InputBar + ModeIndicator
  - 全局键盘事件监听（Enter提交、Esc关闭）
  - 窗口样式：透明背景、居中
- [ ] **3.2.2** 编写 `src/components/launcher/InputBar.tsx`：
  - 文本输入框组件
  - 自动聚焦（窗口显示时）
  - 显示语音转写实时文本
  - Enter键提交（调用submitText）
  - Esc键关闭窗口
- [ ] **3.2.3** 编写 `src/components/launcher/ModeIndicator.tsx`：
  - 麦克风/键盘图标切换
  - 点击切换输入模式
  - 录音中显示红色脉冲动画
- [ ] **3.2.4** Launcher Bar样式：
  - 宽600px，高52px，圆角16px
  - 毛玻璃背景效果（backdrop-filter: blur）
  - 深色主题配色
  - 输入框placeholder："输入指令或点击麦克风说话..."

### 3.3 Main Panel窗口

- [ ] **3.3.1** 编写 `src/App.tsx`（Main Panel根组件）：
  - 接收输入文本（从Zustand或URL参数）
  - 自动触发Pipeline
  - 根据状态渲染不同组件
- [ ] **3.3.2** 编写 `src/components/panel/PipelineProgress.tsx`：
  - 水平步骤指示器：意图解析 → 搜索 → 执行
  - 当前步骤高亮 + 加载动画
  - 已完成步骤打勾
  - 失败步骤标红
- [ ] **3.3.3** 编写 `src/components/panel/ResultList.tsx`：
  - 文件结果列表组件
  - 每行显示：文件图标、文件名、路径、大小、修改时间、打开按钮
  - 键盘导航：↑/↓ 切换选中，Enter 执行
  - 鼠标：hover高亮，单击选中，双击执行
  - 空结果状态："未找到匹配文件"
- [ ] **3.3.4** 编写 `src/components/panel/ActionFeedback.tsx`：
  - 执行成功：绿色勾 + 消息
  - 执行失败：红色叉 + 错误信息
  - 显示3秒后淡出
- [ ] **3.3.5** 编写 `src/components/shared/WaveformVisualizer.tsx`：
  - 简单的音频波形动画（CSS动画或Canvas）
  - 录音时显示在Launcher Bar中

### 3.4 窗口切换逻辑

- [ ] **3.4.1** 编写 `src/hooks/useTauriWindow.ts`：
  - `showLauncher()` → 调用Tauri API显示launcher窗口
  - `hideLauncherShowPanel(text)` → 隐藏launcher、显示main、传递输入
  - `hideAll()` → 全部隐藏
  - 开发模式降级：无Tauri时用浏览器路由模拟
- [ ] **3.4.2** Launcher提交 → Panel展示 的数据流：
  - Launcher: Enter → WebSocket `submit_text` → 隐藏Launcher → 显示Panel
  - Panel: 订阅WebSocket事件 → 更新UI → 执行完成 → 延迟隐藏

### 3.5 样式与动画

- [ ] **3.5.1** 全局深色主题配色：
  - 背景：`#1a1a2e` / `#16213e`
  - 前景文字：`#e0e0e0`
  - 强调色：`#4fc3f7`（蓝色）
  - 成功色：`#66bb6a`，失败色：`#ef5350`
- [ ] **3.5.2** 过渡动画：
  - Launcher出现/消失：scale + opacity
  - Panel展开/收起：slide + opacity
  - 结果列表项出现：stagger fade-in
- [ ] **3.5.3** 创建 git commit：`feat: dual-window frontend UI`

### Phase 3 验收标准

- [ ] Launcher Bar可显示，输入文本后按Enter
- [ ] Main Panel接收输入并显示Pipeline进度
- [ ] 搜索结果可用键盘/鼠标选择和执行
- [ ] 深色主题视觉效果良好
- [ ] 开发模式下（无Tauri）两个窗口间数据流通正常

---

## Phase 4: Tauri桌面应用（第11-13天）

> 目标：打包为独立桌面应用，实现双窗口常驻后台体验。

### 4.1 Tauri项目初始化

- [ ] **4.1.1** 安装Tauri CLI：`cargo install tauri-cli`
- [ ] **4.1.2** 在项目根目录执行 `cargo tauri init`，生成 `src-tauri/`
- [ ] **4.1.3** 配置 `tauri.conf.json`：
  - 定义 `launcher` 窗口：
    - `label: "launcher"`, `url: "/launcher.html"`
    - `width: 600`, `height: 56`, `decorations: false`, `transparent: true`
    - `alwaysOnTop: true`, `visible: false`, `skipTaskbar: true`
    - `center: true`, `resizable: false`
  - 定义 `main` 窗口：
    - `label: "main"`, `url: "/index.html"`
    - `width: 700`, `height: 500`, `decorations: false`
    - `visible: false`, `center: true`
  - 配置权限：shell, global-shortcut, tray

### 4.2 窗口管理（Rust）

- [ ] **4.2.1** 编写 `src-tauri/src/windows.rs`：
  - `show_launcher()` → 获取launcher窗口 → show + focus
  - `hide_launcher()` → 获取launcher窗口 → hide
  - `show_main(query: String)` → 获取main窗口 → emit事件(query) → show + focus
  - `hide_main()` → 获取main窗口 → hide
  - `hide_all()` → 隐藏所有窗口
- [ ] **4.2.2** 注册Tauri命令（invoke handler）：
  - 前端可通过 `invoke('show_launcher')` 等调用Rust函数
- [ ] **4.2.3** 处理窗口失焦事件：
  - Launcher失焦 → 自动隐藏
  - Main Panel失焦 → 不自动隐藏（用户可能在操作其他窗口）

### 4.3 全局快捷键

- [ ] **4.3.1** 编写全局快捷键注册：
  - `Ctrl+Shift+G` → 调用 `show_launcher()`
  - 如果Launcher已显示 → 隐藏（toggle行为）
- [ ] **4.3.2** 处理快捷键冲突检测

### 4.4 系统托盘

- [ ] **4.4.1** 编写 `src-tauri/src/tray.rs`：
  - 创建系统托盘图标
  - 左键单击 → 唤醒Launcher
  - 右键菜单：
    - "唤醒 GotIt"（Ctrl+Shift+G）
    - "设置"
    - 分隔线
    - "退出"
- [ ] **4.4.2** 托盘图标设计（或使用临时图标）

### 4.5 Python后端进程管理

- [ ] **4.5.1** 编写 `src-tauri/src/main.rs` 后端进程管理：
  - Tauri启动时 → spawn Python后端进程（`uv run gotit --mode server`）
  - 捕获Python进程stdout/stderr → 写入日志文件
- [ ] **4.5.2** 实现健康检查：
  - 每5秒ping `http://localhost:8765/api/health`
  - 连续3次失败 → 重启Python进程
  - 最多重启3次 → 显示错误通知
- [ ] **4.5.3** 实现优雅退出：
  - Tauri退出事件 → 发送SIGTERM给Python进程 → 等待3秒 → 强制kill

### 4.6 打包配置

- [ ] **4.6.1** 配置 Tauri 打包：
  - 应用名称：GotIt
  - 应用图标（多尺寸 .ico）
  - Windows安装包格式：NSIS
- [ ] **4.6.2** 配置开机自启（可选，默认关闭）：
  - Windows注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- [ ] **4.6.3** 执行 `cargo tauri build`，验证安装包生成
- [ ] **4.6.4** 安装并测试完整流程
- [ ] **4.6.5** 创建 git commit：`feat: Tauri desktop app with dual windows`

### Phase 4 验收标准

- [ ] 双击 `GotIt.exe` 启动 → 无可见窗口，托盘图标出现
- [ ] `Ctrl+Shift+G` → Launcher Bar在屏幕中央上方弹出
- [ ] Launcher输入文本 → Enter → Launcher消失 → Main Panel展开 → 显示结果
- [ ] Main Panel中选择结果 → 执行成功 → 3秒后Panel自动收起
- [ ] Esc → 当前窗口关闭
- [ ] 右键托盘 → 菜单正常显示 → "退出"可正常退出
- [ ] Python后端崩溃 → 自动重启

---

## Phase 5: 体验优化（第14-16天）

> 目标：打磨细节，提升可用性。

### 5.1 流式语音转写

- [ ] **5.1.1** 升级 `WhisperCppAdapter`：支持流式音频输入
  - 实现 `start_stream()` → 边录边转
  - 输出 partial transcript（中间结果）
- [ ] **5.1.2** Launcher Bar实时显示partial transcript
  - 灰色显示中间结果，白色显示最终结果
- [ ] **5.1.3** 测试流式转写延迟和准确率

### 5.2 音频质量优化

- [ ] **5.2.1** 实现音频预处理管道：
  - 降噪处理（spectral gating 或 noisereduce库）
  - 自动增益控制（AGC）
  - 人声频率范围滤波（300Hz-3400Hz）
- [ ] **5.2.2** A/B测试：预处理前后的转写准确率对比

### 5.3 操作历史

- [ ] **5.3.1** Main Panel增加"历史"标签页
  - 显示最近操作列表（时间、输入、动作、结果）
  - 点击可重做
- [ ] **5.3.2** Launcher Bar支持历史补全：
  - ↑/↓ 键浏览历史输入
  - 输入时自动补全匹配历史

### 5.4 错误恢复

- [ ] **5.4.1** LLM调用失败 → 自动重试（最多2次，指数退避）
- [ ] **5.4.2** Everything搜索失败 → 检查Everything服务是否运行 → 提示用户
- [ ] **5.4.3** 网络断开 → 自动切换到离线LLM（如已配置Ollama）

### 5.5 离线LLM支持

- [ ] **5.5.1** 编写 `gotit/adapters/llm/ollama.py`：
  - `OllamaAdapter` 实现 `LLMPort`
  - 支持 qwen2.5 / llama3 等模型
  - API调用 `http://localhost:11434/api/generate`
- [ ] **5.5.2** 配置中支持LLM provider切换
- [ ] **5.5.3** 测试离线场景下的意图解析质量

### 5.6 性能优化

- [ ] **5.6.1** Launcher唤醒延迟优化（目标 < 200ms）
  - 窗口预创建，show/hide而非create/destroy
- [ ] **5.6.2** Pipeline并行化：
  - 文件元信息获取（大小、修改时间）并行执行
- [ ] **5.6.3** whisper.cpp模型预加载：
  - 应用启动时加载模型到内存
  - 避免每次录音时的模型加载延迟
- [ ] **5.6.4** 创建 git commit：`feat: UX polish and performance optimization`

### Phase 5 验收标准

- [ ] 语音输入时Launcher Bar实时显示转写文本
- [ ] 操作历史可查看和重做
- [ ] 离线模式（Ollama）可正常工作
- [ ] Launcher唤醒 < 200ms
- [ ] 端到端延迟（语音停止→结果显示）< 4s

---

## Phase 6: 扩展能力（未来）

> 目标：向AI Agent方向演进。标记为未来任务，不设固定时间。

### 6.1 插件系统

- [ ] **6.1.1** 设计Plugin API接口
- [ ] **6.1.2** 实现插件加载器（从指定目录动态加载）
- [ ] **6.1.3** 编写示例插件：剪贴板搜索

### 6.2 多步骤任务链

- [ ] **6.2.1** 设计TaskChain模型（多个Intent串联执行）
- [ ] **6.2.2** LLM支持多步骤任务解析
- [ ] **6.2.3** UI支持任务链进度展示

### 6.3 上下文记忆

- [ ] **6.3.1** 实现对话历史持久化（SQLite）
- [ ] **6.3.2** 用户偏好学习（常用操作、常用路径）
- [ ] **6.3.3** 基于历史的智能建议

### 6.4 更多扩展

- [ ] **6.4.1** 自定义动作注册（用户定义新的Action类型）
- [ ] **6.4.2** 剪贴板集成（搜索剪贴板内容）
- [ ] **6.4.3** 屏幕内容感知（OCR + 截图理解）
- [ ] **6.4.4** TTS语音回复（播报执行结果）

---

## 进度总览

| 阶段 | 任务总数 | 已完成 | 进度 | 状态 |
|------|---------|--------|------|------|
| Phase 0: 项目脚手架 | 27 | 16 | 59% | 进行中 |
| Phase 1: MVP命令行版 | 25 | 0 | 0% | 未开始 |
| Phase 2: WebSocket API | 11 | 0 | 0% | 未开始 |
| Phase 3: 前端UI | 17 | 0 | 0% | 未开始 |
| Phase 4: Tauri桌面应用 | 18 | 0 | 0% | 未开始 |
| Phase 5: 体验优化 | 14 | 0 | 0% | 未开始 |
| Phase 6: 扩展能力 | 10 | 0 | 0% | 未来规划 |
| **总计** | **122** | **16** | **13%** | — |

---

## 变更日志

| 日期 | 变更内容 |
|------|---------|
| 2026-04-24 | 初始任务清单创建 |
| 2026-04-24 | 完成 0.1（Python后端初始化）+ 0.2（目录结构创建）+ 0.7.1（models/.gitkeep） |
| 2026-04-24 | 完成 0.3（Domain层骨架）：models/ports/events/pipeline + EventBus，全部实现非占位 |
