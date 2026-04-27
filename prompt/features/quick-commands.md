# Feature: Quick Commands — 常用指令集

> 用户可预定义常用指令，系统可自动根据使用习惯推荐指令。执行时优先匹配常用指令，未命中再走现有流程。

---

## 1. 问题与动机

用户有大量日常重复操作：

| 用户每天说的 | 实际含义（固定不变） |
|------------|-------------------|
| "打开 restbus" | 打开 `D:\Projects\xxx600\tools\restbus\restbus.exe` |
| "打开劳特尔巴赫" | 打开 `C:\T32\bin\windows64\t32marm.exe` |
| "用vscode打开某某项目" | `code.exe D:\Projects\xxx600` |
| "打开周报" | 打开 `D:\Work\周报_2026.xlsx` |

这些操作每次都要走 LLM 解析 → Everything 搜索 → 模糊匹配，耗时 3~8 秒。但用户的意图是完全确定的 — **同样的话永远指向同一个目标**。

**核心思路**：把这些"话 → 动作"的映射存下来，下次说同样的话时直接执行，跳过 LLM + 搜索，响应时间从秒级降到毫秒级。

---

## 2. 功能概述

### 2.1 Quick Command 数据结构

```yaml
# 一条 Quick Command
- trigger: "打开restbus"           # 触发短语（用户说的话）
  aliases:                          # 可选的其他触发方式
    - "restbus"
    - "打开rest bus"
  action: "open_file"               # 动作类型
  target: "D:\\Projects\\RAD600\\tools\\restbus\\restbus.exe"
  with_program: null                # 用什么程序打开（null = 默认）
  source: "manual"                  # 来源: manual（用户手动） / recommended（系统推荐）
  use_count: 15                     # 使用次数
  last_used: "2026-04-25T14:30:00"  # 最后使用时间
```

### 2.2 两种来源

| 来源 | 说明 | 触发方式 |
|------|------|---------|
| **手动添加** (`manual`) | 用户通过 CLI 或 UI 主动创建 | `gotit qc add` 命令 |
| **系统推荐** (`recommended`) | GotIt 检测到重复执行的指令，自动提示用户保存 | Pipeline 执行成功后分析历史 |

### 2.3 执行优先级

```
用户输入
  ↓
Quick Command 匹配（毫秒级）
  ├─ 命中 → 直接执行，跳过 LLM + 搜索
  │
  └─ 未命中 → 现有流程（LLM → fuzzy/exact → 搜索 → 执行）
                  ↓ 执行成功
              检查是否应推荐为 Quick Command
```

**关键原则**：Quick Command 只是一个"快捷通道"，未命中时完全退回现有流程，零影响。

---

## 3. 匹配策略

### 3.1 匹配方式

Quick Command 的匹配**不经过 LLM**，在本地用文本相似度完成：

```python
def match_quick_command(user_input: str, commands: list[QuickCommand]) -> QuickCommand | None:
    """精确匹配 + 模糊匹配，返回最佳命中或 None。"""
    input_normalized = normalize(user_input)

    # 1. 精确匹配（trigger 或 aliases）
    for cmd in commands:
        if input_normalized == normalize(cmd.trigger):
            return cmd
        if any(input_normalized == normalize(a) for a in cmd.aliases):
            return cmd

    # 2. 模糊匹配（编辑距离或包含关系）
    best = None
    best_score = 0.0
    for cmd in commands:
        score = fuzzy_score(input_normalized, cmd)
        if score > 0.85 and score > best_score:
            best = cmd
            best_score = score

    return best
```

`normalize()` 处理：
- 去除首尾空白
- 统一小写
- 去除"请"、"帮我"等无意义前缀
- "打开" / "启动" / "运行" 视为等价

### 3.2 模糊匹配细节

```python
def fuzzy_score(input_text: str, cmd: QuickCommand) -> float:
    """计算输入与 Quick Command 的匹配分数。"""
    triggers = [cmd.trigger] + cmd.aliases

    for t in triggers:
        t_norm = normalize(t)
        # 完全包含
        if t_norm in input_text or input_text in t_norm:
            return 0.95
        # 编辑距离占比
        distance = levenshtein(input_text, t_norm)
        max_len = max(len(input_text), len(t_norm))
        similarity = 1.0 - distance / max_len
        if similarity > 0.85:
            return similarity

    return 0.0
```

阈值 0.85 — 允许小幅措辞差异（"打开restbus" vs "启动restbus"），但不会误匹配完全不同的指令。

---

## 4. 自动推荐机制

### 4.1 推荐条件

当以下条件**全部满足**时，系统提示用户是否保存为 Quick Command：

1. 指令执行成功（`result.success == True`）
2. 相同或高度相似的指令在过去 7 天内执行过 ≥ 3 次
3. 目标路径/程序是固定的（每次执行都指向同一文件/程序）
4. 当前没有已存在的 Quick Command 覆盖这个指令

### 4.2 推荐流程

```
Pipeline 执行成功
  ↓
检查 SessionManager 历史 + ActivityStore
  ↓ 满足推荐条件
生成推荐：
  "你经常执行 '打开restbus'，是否保存为常用指令？"
  ↓ 用户确认 (CLI: Y/n, UI: 弹窗)
保存到 quick_commands.yaml (source: "recommended")
```

### 4.3 CLI 模式推荐交互

```
$ gotit --text "打开restbus"
[OK] Opened restbus.exe

💡 你已经第 4 次执行类似指令，是否保存为常用指令？
   触发词: "打开restbus"
   动作: 打开 D:\Projects\RAD600\tools\restbus\restbus.exe
   [Y/n]:
```

### 4.4 推荐去重

- 推荐过一次且用户拒绝的 → 30 天内不再推荐同一指令
- 存储拒绝记录在 `~/.gotit/qc_dismissed.yaml`

---

## 5. 持久化

### 5.1 存储文件

```yaml
# ~/.gotit/quick_commands.yaml

commands:
  - trigger: "打开restbus"
    aliases: ["restbus", "启动restbus"]
    action: "open_file"
    target: "D:\\Projects\\RAD600\\tools\\restbus\\restbus.exe"
    with_program: null
    source: "manual"
    use_count: 15
    last_used: "2026-04-25T14:30:00"

  - trigger: "用vscode打开雷达项目"
    aliases: ["vscode雷达", "code雷达项目"]
    action: "open_folder"
    target: "D:\\Projects\\RAD600"
    with_program: "code"
    source: "recommended"
    use_count: 8
    last_used: "2026-04-24T10:15:00"

  - trigger: "打开劳特尔巴赫"
    aliases: ["劳特尔巴赫", "T32", "trace32"]
    action: "run_program"
    target: "C:\\T32\\bin\\windows64\\t32marm.exe"
    with_program: null
    source: "manual"
    use_count: 22
    last_used: "2026-04-26T09:00:00"
```

### 5.2 被拒绝的推荐

```yaml
# ~/.gotit/qc_dismissed.yaml

dismissed:
  - trigger: "打开日报"
    dismissed_at: "2026-04-20T10:00:00"
    expires_at: "2026-05-20T10:00:00"
```

---

## 6. CLI 命令

```bash
# 查看所有 Quick Commands
gotit qc list

# 手动添加
gotit qc add "打开restbus" --action open_file --target "D:\Projects\restbus.exe"
gotit qc add "用vscode打开雷达" --action open_folder --target "D:\Projects\RAD600" --with code

# 为已有指令添加别名
gotit qc alias "打开restbus" "restbus" "启动restbus"

# 删除
gotit qc remove "打开restbus"

# 测试匹配（不执行，仅显示匹配结果）
gotit qc test "打开rest bus"
# → Matched: "打开restbus" (score: 0.92) → open_file D:\Projects\restbus.exe

# 导入/导出
gotit qc export > my_commands.yaml
gotit qc import my_commands.yaml
```

---

## 7. 模块设计

### 7.1 新增文件

```
gotit/
├── services/
│   └── quick_commands.py        # QuickCommandStore — 加载/保存/匹配/推荐
```

### 7.2 数据模型

```python
@dataclass
class QuickCommand:
    trigger: str                      # 主触发短语
    action: ActionType                # open_file / open_folder / run_program
    target: str                       # 目标路径
    aliases: list[str] = field(default_factory=list)
    with_program: str | None = None
    source: str = "manual"            # manual / recommended
    use_count: int = 0
    last_used: datetime | None = None
```

### 7.3 QuickCommandStore

```python
class QuickCommandStore:
    def __init__(self, path: str = "~/.gotit/quick_commands.yaml"):
        ...

    def load(self) -> None: ...
    def save(self) -> None: ...

    def match(self, user_input: str) -> QuickCommand | None:
        """匹配输入，返回最佳命中或 None。"""
        ...

    def add(self, cmd: QuickCommand) -> None: ...
    def remove(self, trigger: str) -> bool: ...
    def add_alias(self, trigger: str, alias: str) -> None: ...

    def record_use(self, cmd: QuickCommand) -> None:
        """记录使用，更新 use_count 和 last_used。"""
        ...

    def should_recommend(
        self, raw_text: str, target: str, history: list[SessionRecord]
    ) -> QuickCommand | None:
        """分析历史，判断是否应推荐保存为 Quick Command。"""
        ...

    def dismiss_recommendation(self, trigger: str) -> None: ...
```

---

## 8. Pipeline 集成

### 8.1 修改 `_run_from_transcript`

在 LLM 解析**之前**，先尝试 Quick Command 匹配：

```python
async def _run_from_transcript(self, transcript: Transcript) -> ExecutionResult:
    # ⓪ Quick Command 匹配 — 在 LLM 之前
    if self._quick_commands:
        matched = self._quick_commands.match(transcript.text)
        if matched:
            log.info("quick_command_matched", trigger=matched.trigger)
            self._quick_commands.record_use(matched)
            intent = Intent(
                action=matched.action,
                raw_text=transcript.text,
                target=matched.target,
                with_program=matched.with_program,
                match_mode="exact",
                confidence=1.0,
            )
            await self._bus.publish(IntentEvent(intent=intent))
            result = await self._executor.execute(intent, [])
            await self._bus.publish(ExecutionEvent(result=result))
            return result

    # ① LLM 解析（现有流程，完全不变）
    intent = await self._llm.parse_intent(transcript.text)
    ...
```

### 8.2 执行成功后推荐检查

```python
    # 执行成功后，检查是否应推荐为 Quick Command
    if result.success and self._quick_commands:
        recommendation = self._quick_commands.should_recommend(
            transcript.text, intent.target or "", session_history
        )
        if recommendation:
            result = ExecutionResult(
                success=True,
                action=result.action,
                message=result.message,
                data={**(result.data or {}), "qc_recommendation": {
                    "trigger": recommendation.trigger,
                    "target": recommendation.target,
                }},
            )
```

推荐信息通过 `ExecutionResult.data` 传递到前端/CLI，由 UI 层决定如何展示。

---

## 9. 对现有代码的影响

| 文件 | 变更 | 说明 |
|------|------|------|
| `gotit/services/quick_commands.py` | **新增** | QuickCommandStore — 加载/保存/匹配/推荐 |
| `gotit/domain/pipeline.py` | **修改** | `_run_from_transcript` 开头插入 QC 匹配 |
| `gotit/services/container.py` | 修改 | 构建 QuickCommandStore，注入 Pipeline |
| `gotit/main.py` | 修改 | 新增 `qc` 子命令（list/add/remove/alias/test） |
| `gotit/domain/models.py` | 扩展 | 新增 `QuickCommand` dataclass |

现有的 LLM → 搜索 → 执行流程**完全不变** — Quick Command 只是在最前面插入一个快速匹配层。

---

## 10. 新增依赖

无。YAML 读写复用已有的 `pyyaml`，文本相似度用标准库实现（`difflib.SequenceMatcher`）。

---

## 11. 性能

| 操作 | 耗时 |
|------|------|
| Quick Command 匹配 | < 1ms（内存中遍历 + 字符串比较） |
| 命中后执行 | < 100ms（跳过 LLM + 搜索） |
| 未命中 fallback | 0ms 额外开销（直接进入现有流程） |

对比现有流程的 3~8 秒（LLM 3~5s + 搜索 0.5~2s），常用指令的响应提速 30~80 倍。

---

## 12. 实施步骤

| 步骤 | 内容 | 依赖 |
|------|------|------|
| 1 | 新增 `QuickCommand` 到 `models.py` | - |
| 2 | 实现 `quick_commands.py`（Store + 匹配 + YAML 读写）+ 测试 | 1 |
| 3 | 实现 CLI `qc` 子命令（list/add/remove/alias/test）| 2 |
| 4 | 修改 `pipeline.py`（QC 匹配层 + 推荐检查）| 2 |
| 5 | 修改 `container.py`（DI 注入）| 2 |
| 6 | 实现推荐逻辑 + 推荐拒绝持久化 | 2 |
| 7 | 集成测试 + 端到端验证 | 4,5 |

---

## 13. 测试策略

### 单元测试
- `test_quick_commands.py` — YAML 读写、精确匹配、模糊匹配、normalize、别名匹配、use_count 更新
- `test_qc_recommend.py` — 推荐条件判断、去重、拒绝记录

### 集成测试
- `test_qc_pipeline.py` — Quick Command 命中时跳过 LLM、未命中时 fallback 到现有流程

---

## 14. 边界与约束

- **Quick Command 数量** — 预期几十到几百条，内存遍历完全够用，不需要索引。
- **不替代 LLM** — QC 只处理"完全确定"的重复操作，新指令、模糊指令仍走 LLM。
- **不自动执行推荐** — 系统只提示用户，用户确认后才保存。
- **目标路径变化** — 如果目标文件被移动/删除，执行时会失败并提示用户更新或删除该 QC。
- **可导出/导入** — 方便用户在多台机器间同步常用指令。
