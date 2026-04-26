# Feature: Activity Tracker + Fuzzy Resolution — 活动记录与模糊查找

> 记录用户日常程序/文档打开活动，当用户发出模糊指令时通过多策略解析链智能匹配。

---

## 1. 问题与动机

当前系统对所有查询一视同仁 — 拿到关键词就丢给 Everything 精确搜索。
这对精确查询没问题（"搜索 *.py"、"打开记事本"），但对模糊查询（人类日常更自然的表达方式）力不从心：

| 用户说的 | 实际文件/程序 | 当前系统能否找到 |
|---------|-------------|--------------|
| "打开记事本" | `notepad.exe` | 能（PATH 中） |
| "打开上周的出差申请表" | `travel_request_0420.xlsx` | 不能 — 文件名与关键词不匹配 |
| "打开画图" | `mspaint.exe` | 不能 — 中文名 ≠ 英文进程名 |
| "打开之前那个auto什么的配置" | `autosar_config.xml` | 不能 — 只有部分名称 |
| "打开我刚才在用的Excel" | `Q1_report.xlsx` | 不能 — 描述的是类型和时间，不是文件名 |
| "打开PS" | `Photoshop.exe` | 不能 — 缩写 ≠ 文件名 |

**核心问题**：精确查询和模糊查询需要走不同的解析路径。

---

## 2. 核心设计：查询精度分级

### 2.1 让 LLM 判断查询精度

在 LLM 意图解析阶段，新增 `match_mode` 字段，由 LLM 判断用户查询的精确程度：

```json
{
  "action": "open_file",
  "query": "出差申请表",
  "target": null,
  "filters": { "dm": "thisweek" },
  "match_mode": "fuzzy",
  "fuzzy_hints": {
    "time_ref": "last_week",
    "partial_name": null,
    "description": "出差申请表",
    "synonyms": ["travel request", "差旅申请"]
  },
  "confidence": 0.85
}
```

#### `match_mode` 取值

| 值 | 含义 | 触发条件 | 示例 |
|----|------|---------|------|
| `exact` | 精确查询 | 用户给出了明确的文件名、程序名或搜索模式 | "搜索 *.py"、"打开 notepad"、"打开 D:\doc.pdf" |
| `fuzzy` | 模糊查询 | 名称残缺/跨语言/描述性/时间限定等任一条件 | "上周的申请表"、"打开画图"、"那个auto什么的" |

#### `fuzzy_hints`（仅 `match_mode=fuzzy` 时存在）

LLM 在判定为 fuzzy 时，同时提供尽可能多的解析线索：

| 字段 | 类型 | 说明 |
|------|------|------|
| `time_ref` | `string?` | 用户提到的时间：`today/yesterday/this_week/last_week/this_month/last_month/recent` |
| `partial_name` | `string?` | 用户记得的部分名称片段（如 "auto"） |
| `description` | `string?` | 用户对文件/程序的功能性描述（如 "出差申请表"、"画图"） |
| `synonyms` | `list[str]` | LLM 推断的同义词/翻译/别名（如 "画图" → `["mspaint", "paint"]`） |
| `likely_ext` | `list[str]?` | LLM 根据语义猜测的文件类型（如 "申请表" → `["xlsx","docx","pdf"]`） |

### 2.2 分流路径

```
用户指令
  ↓
LLM 意图解析 → Intent { action, query, match_mode, fuzzy_hints }
  ↓
match_mode == "exact"?
  ├─ YES → 现有流程（Everything 精确搜索 / shutil.which / PATH）
  │         不查历史，不做扩展
  │
  └─ NO (fuzzy) → 模糊解析链（Fuzzy Resolution Chain）
                    多策略并行/级联匹配
                    ↓
              结果处理（0/1/多个）
```

**核心原则**：精确查询走快路径（现有逻辑零改动），模糊查询走智能路径。

---

## 3. 模糊解析链（Fuzzy Resolution Chain）

当 `match_mode=fuzzy` 时，按以下策略依次尝试，每个策略返回候选结果列表，有结果即进入结果处理：

```
┌──────────────────────────────────────────────────────────────┐
│                   Fuzzy Resolution Chain                      │
│                                                              │
│  Strategy 1: 活动历史查找                                     │
│    输入: query + time_ref + partial_name                     │
│    在 SQLite 中模糊匹配 filename / window_title              │
│    按 (打开时间匹配度 × 名称相似度 × 打开频次) 排序           │
│    ↓ 有结果 → 进入结果处理                                    │
│    ↓ 无结果                                                  │
│                                                              │
│  Strategy 2: Everything + LLM synonyms 搜索                  │
│    将 query + fuzzy_hints.synonyms 逐一丢给 Everything        │
│    附加 fuzzy_hints.likely_ext 作为扩展名过滤                 │
│    合并去重，按 match_score 排序                              │
│    ↓ 有结果 → 进入结果处理                                    │
│    ↓ 无结果                                                  │
│                                                              │
│  Strategy 3: Everything 通配符/放宽搜索                       │
│    用 partial_name 构造通配符查询 (*auto*)                    │
│    去掉 dm / ext 等限制条件重试                               │
│    ↓ 有结果 → 进入结果处理                                    │
│    ↓ 无结果                                                  │
│                                                              │
│  Strategy 4: LLM 二次理解（可选，高成本）                     │
│    把前几轮无结果的事实 + 原始query 反馈给 LLM                 │
│    让 LLM 换一种方式生成搜索关键词                            │
│    最后一搏                                                   │
│    ↓ 有结果 → 进入结果处理                                    │
│    ↓ 无结果 → 告知用户未找到                                  │
└──────────────────────────────────────────────────────────────┘
```

### 3.1 Strategy 1 — 活动历史查找

**何时有效**：用户说的是"之前用过的"、"上周的"、"刚才那个"，或者用中文/缩写指代程序名。

查询逻辑：
```sql
-- 文件查找示例（模糊 + 时间范围）
SELECT filepath, filename, opened_at, COUNT(*) as open_count
FROM file_activity
WHERE filename LIKE '%申请%'                    -- 模糊匹配 query
  AND opened_at BETWEEN '2026-04-19' AND '2026-04-26'  -- time_ref 映射
GROUP BY filepath
ORDER BY MAX(opened_at) DESC, open_count DESC
LIMIT 10;

-- 程序查找示例（跨语言别名）
-- 用户说 "画图" → synonyms = ["mspaint", "paint"]
SELECT exe_path, exe_name, window_title
FROM program_activity
WHERE exe_name LIKE '%mspaint%' OR exe_name LIKE '%paint%'
   OR window_title LIKE '%画图%'
ORDER BY last_seen DESC
LIMIT 5;
```

**关键**：活动历史的价值不是"搜索"，而是**缩小范围** — 从全盘数十万文件缩小到用户实际接触过的几百个。在这个小范围内做模糊匹配，精度高得多。

### 3.2 Strategy 2 — Everything + synonyms

**何时有效**：用户要找的东西没在历史记录中（新文件、别人发来的、很久没打开过的）。

利用 LLM 在意图解析阶段已生成的 `synonyms` 列表，逐一搜索：

```python
async def _search_with_synonyms(self, intent: Intent) -> list[SearchResult]:
    queries = [intent.query] + (intent.fuzzy_hints.get("synonyms") or [])
    ext_filter = intent.fuzzy_hints.get("likely_ext")
    
    all_results = []
    seen_paths = set()
    for q in queries:
        filters = dict(intent.filters)
        if ext_filter and "ext" not in filters:
            # 逐个扩展名尝试
            for ext in ext_filter:
                filters["ext"] = ext
                results = await self._searcher.search(q, filters)
                for r in results:
                    if r.path not in seen_paths:
                        seen_paths.add(r.path)
                        all_results.append(r)
        else:
            results = await self._searcher.search(q, filters)
            for r in results:
                if r.path not in seen_paths:
                    seen_paths.add(r.path)
                    all_results.append(r)
    return all_results
```

### 3.3 Strategy 3 — 放宽搜索

**何时有效**：前两轮的过滤条件太严了。

```python
async def _relaxed_search(self, intent: Intent) -> list[SearchResult]:
    # 3a: 用 partial_name 构造通配符
    partial = intent.fuzzy_hints.get("partial_name")
    if partial:
        results = await self._searcher.search(f"*{partial}*", None)
        if results:
            return results

    # 3b: 去掉所有 filters 重试 query
    if intent.filters:
        results = await self._searcher.search(intent.query, None)
        if results:
            return results

    return []
```

### 3.4 Strategy 4 — LLM 二次理解（可选）

仅在前三轮全部失败时触发。把失败信息反馈给 LLM，请求换一种搜索关键词：

```python
async def _llm_retry(self, intent: Intent) -> list[SearchResult]:
    prompt = (
        f"用户想找: '{intent.raw_text}'\n"
        f"我尝试了以下关键词但没找到: {intent.query}, {intent.fuzzy_hints.get('synonyms')}\n"
        f"请给出 3 个替代搜索关键词（简短、适合文件名匹配），用 JSON 数组返回。"
    )
    alt_queries = await self._llm.generate_alternatives(prompt)
    for q in alt_queries:
        results = await self._searcher.search(q, None)
        if results:
            return results
    return []
```

**注意**：这一步有额外 LLM 调用成本，默认可关闭，通过配置启用。

---

## 4. 活动历史系统（为 Strategy 1 服务）

活动历史的唯一目的是支撑模糊查找 Strategy 1。设计上要求轻量、低侵入。

### 4.1 监控方案

**推荐：A + D 组合**

| 方案 | 目的 | 原理 | 权限要求 |
|------|------|------|---------|
| **A. Recent 目录扫描** | 捕获文件打开 | 定时扫描 `%APPDATA%\Microsoft\Windows\Recent\` 新增 `.lnk` 文件，解析目标路径 | 无需特殊权限 |
| **D. 前台窗口轮询** | 捕获程序使用 | 每 N 秒调用 Win32 API `GetForegroundWindow` → 获取进程路径 + 窗口标题 | 无需特殊权限 |

其他方案（ETW、Shell Hook、COM）复杂度高或需管理员权限，暂不采用。

**补充来源**：GotIt 自身操作 — 每次通过 GotIt 成功打开文件/程序时，自动写入历史（`source="gotit"`）。

### 4.2 数据存储

SQLite，路径 `~/.gotit/activity.db`。

```sql
CREATE TABLE file_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath    TEXT NOT NULL,
    filename    TEXT NOT NULL,
    extension   TEXT,
    opened_at   TIMESTAMP NOT NULL,
    source      TEXT DEFAULT 'recent',      -- recent / gotit
    UNIQUE(filepath, opened_at)
);

CREATE INDEX idx_file_filename ON file_activity(filename);
CREATE INDEX idx_file_opened_at ON file_activity(opened_at);

CREATE TABLE program_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exe_path    TEXT NOT NULL,
    exe_name    TEXT NOT NULL,
    window_title TEXT,
    started_at  TIMESTAMP NOT NULL,
    last_seen   TIMESTAMP NOT NULL,
    source      TEXT DEFAULT 'poll',         -- poll / gotit
    UNIQUE(exe_path, started_at)
);

CREATE INDEX idx_prog_exe_name ON program_activity(exe_name);
CREATE INDEX idx_prog_last_seen ON program_activity(last_seen);
```

保留策略：默认 14 天，可配置。启动时 + 每 24 小时清理过期数据。

### 4.3 程序别名表（静态 + 动态）

模糊查找程序时，仅靠进程名和窗口标题不够。需要一张别名映射表，解决跨语言/缩写/俗称的匹配：

```python
# 静态别名（内置常见程序）
PROGRAM_ALIASES = {
    "记事本":   ["notepad.exe"],
    "画图":     ["mspaint.exe"],
    "计算器":   ["calc.exe", "calculator.exe"],
    "浏览器":   ["chrome.exe", "msedge.exe", "firefox.exe"],
    "PS":       ["photoshop.exe"],
    "VS Code":  ["code.exe"],
    "微信":     ["wechat.exe"],
    "QQ":       ["qq.exe"],
    "钉钉":     ["dingtalk.exe"],
    "Word":     ["winword.exe"],
    "Excel":    ["excel.exe"],
    "PPT":      ["powerpnt.exe"],
    # ...更多
}
```

**动态补充**：程序别名也可由 LLM 在 `fuzzy_hints.synonyms` 中实时生成（LLM 知道 "画图" = "mspaint"）。静态表覆盖高频场景避免 LLM 调用，LLM 处理长尾。

查找时合并使用：
1. 查静态别名 → 得到候选 exe 名
2. 加上 LLM synonyms → 扩展候选
3. 在 `program_activity` 中匹配

---

## 5. LLM Prompt 修改

### 5.1 新增字段说明

在 `intent_system.txt` 中增加：

```
## match_mode field

Classify how precise the user's query is:
- "exact": User gives a clear filename, program name, search pattern, or path.
  Examples: "打开 notepad", "搜索 *.py", "打开 D:\\docs\\report.pdf"
- "fuzzy": User's description is vague — partial names, time references,
  descriptions, Chinese names for English programs, abbreviations, etc.
  Examples: "上周的出差申请表", "打开画图", "那个叫auto什么的配置文件",
  "刚才用的Excel", "打开PS"

## fuzzy_hints field (only when match_mode is "fuzzy")

Provide as many clues as possible to help resolve the fuzzy query:
- "time_ref": When the user last used/opened it.
  Values: "today" / "yesterday" / "this_week" / "last_week" / "this_month" / "last_month" / "recent"
  null if no time context.
- "partial_name": Fragment of the filename the user remembers. e.g. "auto" from "那个auto什么的"
- "description": Functional description of the file/program. e.g. "出差申请表", "画图工具"
- "synonyms": Your best guess at alternative names, translations, or aliases.
  e.g. for "画图" → ["mspaint", "paint"],
  for "出差申请表" → ["travel request", "差旅申请", "出差申请"]
- "likely_ext": Likely file extensions based on context.
  e.g. "申请表" → ["xlsx", "docx", "pdf"]

For match_mode "exact", omit fuzzy_hints entirely.

## Examples

User: "打开记事本"
{"action":"run_program","query":null,"target":"notepad","filters":{},"match_mode":"exact","confidence":0.95}

User: "搜索所有PDF文件"
{"action":"search","query":"*","target":null,"filters":{"ext":"pdf"},"match_mode":"exact","confidence":0.95}

User: "打开上周的出差申请表"
{"action":"open_file","query":"出差申请表","target":null,"filters":{},"match_mode":"fuzzy","fuzzy_hints":{"time_ref":"last_week","partial_name":null,"description":"出差申请表","synonyms":["travel request","差旅申请"],"likely_ext":["xlsx","docx","pdf"]},"confidence":0.85}

User: "打开画图"
{"action":"run_program","query":null,"target":"画图","filters":{},"match_mode":"fuzzy","fuzzy_hints":{"time_ref":null,"partial_name":null,"description":"画图工具","synonyms":["mspaint","paint","mspaint.exe"],"likely_ext":null},"confidence":0.9}

User: "打开那个叫auto什么的配置文件"
{"action":"open_file","query":"auto","target":null,"filters":{},"match_mode":"fuzzy","fuzzy_hints":{"time_ref":null,"partial_name":"auto","description":"配置文件","synonyms":["autosar","autoconfig","auto.conf"],"likely_ext":["xml","json","yaml","ini","conf"]},"confidence":0.7}

User: "打开我刚才在用的Excel"
{"action":"open_file","query":"*","target":null,"filters":{"ext":"xlsx"},"match_mode":"fuzzy","fuzzy_hints":{"time_ref":"recent","partial_name":null,"description":null,"synonyms":[],"likely_ext":["xlsx","xls"]},"confidence":0.8}

User: "打开PS"
{"action":"run_program","query":null,"target":"PS","filters":{},"match_mode":"fuzzy","fuzzy_hints":{"time_ref":null,"partial_name":null,"description":"Photoshop","synonyms":["photoshop","photoshop.exe","Adobe Photoshop"],"likely_ext":null},"confidence":0.85}
```

### 5.2 Intent 模型扩展

```python
# gotit/domain/models.py

@dataclass(frozen=True, slots=True)
class Intent:
    action: ActionType
    raw_text: str
    query: str | None = None
    target: str | None = None
    filters: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    match_mode: str = "exact"                              # 新增
    fuzzy_hints: dict[str, Any] | None = None              # 新增
```

---

## 6. Pipeline 集成

### 6.1 修改 `_run_from_transcript`

```python
async def _run_from_transcript(self, transcript: Transcript) -> ExecutionResult:
    intent = await self._llm.parse_intent(transcript.text)
    await self._bus.publish(IntentEvent(intent=intent))

    results = []
    if intent.action in (ActionType.SEARCH, ActionType.OPEN_FILE):
        if intent.match_mode == "fuzzy":
            results = await self._fuzzy_resolve(intent)
        else:
            # 精确搜索 — 现有逻辑不变
            results = await self._searcher.search(
                intent.query or intent.raw_text, intent.filters or None
            )
        await self._bus.publish(SearchEvent(results=results))

    elif intent.action == ActionType.RUN_PROGRAM:
        if intent.match_mode == "fuzzy":
            results = await self._fuzzy_resolve_program(intent)
            # results 非空 → targets 传给 executor
        # executor 自身仍保留 shutil.which → Everything fallback

    result = await self._executor.execute(intent, results)
    await self._bus.publish(ExecutionEvent(result=result))
    return result
```

### 6.2 `_fuzzy_resolve` 实现

```python
async def _fuzzy_resolve(self, intent: Intent) -> list[SearchResult]:
    """模糊解析链：活动历史 → synonyms搜索 → 放宽搜索 → LLM重试。"""
    hints = intent.fuzzy_hints or {}

    # Strategy 1: 活动历史
    if self._activity_store:
        time_range = _time_ref_to_range(hints.get("time_ref"))
        extensions = hints.get("likely_ext")
        query = hints.get("partial_name") or intent.query or hints.get("description")
        if query:
            results = await self._activity_store.search_files(
                query=query, time_range=time_range,
                extensions=extensions, limit=20,
            )
            if results:
                return _activity_to_search_results(results)

    # Strategy 2: Everything + synonyms
    queries = [intent.query] if intent.query else []
    queries += hints.get("synonyms") or []
    if queries:
        results = await self._search_with_synonyms(queries, intent.filters, hints)
        if results:
            return results

    # Strategy 3: 放宽条件
    results = await self._relaxed_search(intent, hints)
    if results:
        return results

    # (可选) Strategy 4: LLM 二次理解
    # results = await self._llm_retry(intent)

    return []
```

### 6.3 `_fuzzy_resolve_program` — 程序模糊查找

```python
async def _fuzzy_resolve_program(self, intent: Intent) -> list[SearchResult]:
    """模糊程序查找：静态别名 → 活动历史 → Everything。"""
    hints = intent.fuzzy_hints or {}
    target = intent.target or ""

    # 1. 查静态别名表
    candidates = PROGRAM_ALIASES.get(target, [])
    # 加上 LLM synonyms
    candidates += hints.get("synonyms") or []
    candidates = list(dict.fromkeys(candidates))  # 去重保序

    # 2. 在活动历史中查找
    if self._activity_store and candidates:
        for name in candidates:
            results = await self._activity_store.search_programs(name, limit=5)
            if results:
                # 返回第一个匹配的程序路径
                return [SearchResult(
                    path=results[0].path, filename=results[0].name
                )]

    # 3. shutil.which + Everything 已在 executor 中处理
    # 但这里可以用 candidates 列表预先搜索
    for name in candidates:
        resolved = shutil.which(name)
        if resolved:
            return [SearchResult(path=resolved, filename=Path(resolved).name)]

    return []
```

---

## 7. 结果处理

无论走精确路径还是模糊路径，结果处理统一：

| 结果数量 | 行为 | 模式 |
|---------|------|------|
| 0 | 告知用户未找到，展示已尝试的搜索策略 | CLI: 文字提示 / UI: ActionFeedback |
| 1 | 直接执行（打开文件/启动程序） | 与现有逻辑一致 |
| 多个 | 列表展示，用户选择 | CLI: 编号选择 / UI: ResultList（已有） |

**来源标识**：结果可附带来源信息（`source: "activity"` / `"everything"` / `"synonym"`），
帮助用户理解为什么匹配到这个文件。UI 中可用小标签展示来源。

---

## 8. 模块架构

### 8.1 新增模块

```
gotit/
├── adapters/
│   └── activity/                    # 新增
│       ├── __init__.py
│       ├── tracker.py               # ActivityTracker — 后台监控协调者
│       ├── recent_watcher.py        # Recent 目录扫描器
│       ├── window_poller.py         # 前台窗口轮询器
│       └── aliases.py               # 程序别名静态表
├── domain/
│   ├── models.py                    # 扩展: ActivityRecord, Intent 新增字段
│   ├── ports.py                     # 新增: ActivityStorePort
│   └── pipeline.py                  # 修改: fuzzy 分流 + 解析链
├── services/
│   └── activity_store.py            # 新增: SQLite 活动存储实现
```

### 8.2 Port 接口

```python
# gotit/domain/ports.py — 新增

class ActivityStorePort(Protocol):
    async def record_file_open(
        self, filepath: str, source: str = "recent"
    ) -> None: ...

    async def record_program_use(
        self, exe_path: str, window_title: str | None = None,
        source: str = "poll"
    ) -> None: ...

    async def search_files(
        self, query: str,
        time_range: tuple[datetime, datetime] | None = None,
        extensions: list[str] | None = None,
        limit: int = 20,
    ) -> list[ActivityRecord]: ...

    async def search_programs(
        self, query: str,
        time_range: tuple[datetime, datetime] | None = None,
        limit: int = 10,
    ) -> list[ActivityRecord]: ...

    async def cleanup(self, retention_days: int = 14) -> int: ...
```

### 8.3 ActivityRecord

```python
# gotit/domain/models.py — 新增

@dataclass(frozen=True, slots=True)
class ActivityRecord:
    path: str                        # 文件/程序全路径
    name: str                        # 文件名/进程名
    activity_type: str               # "file" | "program"
    last_opened: datetime            # 最近打开时间
    open_count: int = 1              # 时间范围内的打开次数
    window_title: str | None = None  # 窗口标题（程序活动时）
```

### 8.4 RecentWatcher

```python
class RecentWatcher:
    RECENT_DIR = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Recent"
    SCAN_INTERVAL = 30  # 秒

    async def run(self) -> None:
        """主循环：定时扫描 Recent 目录，增量检测新 .lnk 文件。
        记录上次扫描时间戳，仅处理新增文件。"""
        ...

    def _parse_lnk(self, lnk_path: Path) -> str | None:
        """解析 .lnk → 目标文件路径。使用 pylnk3。"""
        ...
```

### 8.5 WindowPoller

```python
class WindowPoller:
    POLL_INTERVAL = 10  # 秒

    async def run(self) -> None:
        """主循环：采样前台窗口。
        使用 ctypes 调用:
        - GetForegroundWindow → hwnd
        - GetWindowThreadProcessId → pid
        - OpenProcess + GetModuleFileNameExW → exe_path
        - GetWindowTextW → window_title
        去重：同一 exe_path 连续多次采样只更新 last_seen。"""
        ...
```

### 8.6 ActivityTracker

```python
class ActivityTracker:
    """协调 RecentWatcher + WindowPoller，管理生命周期。"""

    def __init__(self, store: ActivityStorePort, config: ActivityConfig) -> None:
        self._watcher = RecentWatcher(store, config)
        self._poller = WindowPoller(store, config)
        ...

    async def start(self) -> None:
        """在 FastAPI lifespan 中调用。启动两个后台 asyncio task。"""
        ...

    async def stop(self) -> None:
        """取消后台 task，清理资源。"""
        ...
```

---

## 9. 配置

```python
# gotit/config.py — 新增

class ActivityConfig(BaseModel):
    enabled: bool = True
    retention_days: int = 14
    db_path: str = "~/.gotit/activity.db"
    recent_scan_interval: int = 30        # Recent 扫描间隔（秒）
    window_poll_interval: int = 10        # 窗口轮询间隔（秒）
    enable_llm_retry: bool = False        # 是否启用 Strategy 4
    excluded_programs: list[str] = [
        "explorer.exe",
        "SearchHost.exe",
        "ShellExperienceHost.exe",
        "SystemSettings.exe",
    ]
    excluded_extensions: list[str] = [
        "tmp", "log", "lock", "lnk",
    ]
```

环境变量：
```
GOTIT_ACTIVITY__RETENTION_DAYS=30
GOTIT_ACTIVITY__ENABLED=false
GOTIT_ACTIVITY__ENABLE_LLM_RETRY=true
```

---

## 10. 对现有代码的影响

| 文件 | 变更 | 说明 |
|------|------|------|
| `domain/models.py` | 扩展 | Intent 新增 `match_mode`, `fuzzy_hints`；新增 `ActivityRecord` |
| `domain/ports.py` | 扩展 | 新增 `ActivityStorePort` |
| `domain/pipeline.py` | **修改** | 搜索前 match_mode 分流，fuzzy 走解析链 |
| `config.py` | 扩展 | 新增 `ActivityConfig` |
| `services/container.py` | 修改 | 构建 ActivityTracker / Store，注入 Pipeline |
| `adapters/llm/prompts/intent_system.txt` | **修改** | 新增 match_mode + fuzzy_hints 字段定义和示例 |
| `adapters/llm/claude.py` | 修改 | 解析新字段到 Intent |
| `adapters/executor/windows.py` | 小改 | 可利用 targets 中的程序路径 |
| `main.py` / `app.py` | 小改 | 启停 ActivityTracker |
| `adapters/activity/*` | **新增** | tracker, recent_watcher, window_poller, aliases |
| `services/activity_store.py` | **新增** | SQLite 存储实现 |

精确查询路径（`match_mode=exact`）的代码完全不变。

---

## 11. 新增依赖

| 包 | 用途 |
|----|------|
| `aiosqlite` | 异步 SQLite |
| `pylnk3` | 解析 .lnk 快捷方式 |

---

## 12. 实施步骤

| 步骤 | 内容 | 依赖 |
|------|------|------|
| 1 | 扩展 models.py（Intent 新字段, ActivityRecord）、ports.py（ActivityStorePort） | - |
| 2 | 实现 activity_store.py（SQLite CRUD + 模糊查询）+ 测试 | 1 |
| 3 | 实现 recent_watcher.py + 测试 | 2 |
| 4 | 实现 window_poller.py + 测试 | 2 |
| 5 | 实现 aliases.py（静态别名表） | - |
| 6 | 实现 tracker.py（协调 watcher + poller）| 3,4 |
| 7 | 修改 intent_system.txt + claude.py（match_mode + fuzzy_hints） | 1 |
| 8 | 修改 pipeline.py（分流 + 解析链）| 2,5,7 |
| 9 | 修改 config.py + container.py（DI 注入）| 6,8 |
| 10 | 集成测试 + 端到端验证 | 9 |

---

## 13. 测试策略

### 单元测试
- `test_activity_store.py` — CRUD、模糊匹配、时间范围查询、清理
- `test_recent_watcher.py` — .lnk 解析、增量扫描
- `test_window_poller.py` — Win32 API mock
- `test_aliases.py` — 别名查找
- `test_fuzzy_resolve.py` — 解析链各策略及降级
- `test_intent_match_mode.py` — LLM 返回 exact/fuzzy 的解析

### 集成测试
- `test_fuzzy_pipeline.py` — 完整 fuzzy 路径端到端
- `test_exact_unchanged.py` — 验证精确查询路径无回归

---

## 14. 边界与约束

- **精确查询零开销** — `match_mode=exact` 不查历史、不做扩展，路径与现有完全一致。
- **仅本地存储** — 活动数据不上传不同步。
- **隐私友好** — 可禁用（`GOTIT_ACTIVITY__ENABLED=false`）、可清空。
- **不需要管理员权限** — Recent 扫描 + 窗口轮询均为用户级操作。
- **LLM 调用成本可控** — Strategy 1~3 不产生额外 LLM 调用（fuzzy_hints 在首次意图解析中一并生成）。Strategy 4 默认关闭。
- **GotIt 自身操作也记录** — 打开成功的文件/程序自动写入历史（source="gotit"）。
