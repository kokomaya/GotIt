# Refinement: Intent Prompt 通用化 — 让 LLM 真正理解用户意图

## 问题

当前 prompt 依赖大量硬编码示例来教 LLM 如何翻译和推断：

```
for "劳特巴赫" → ["lauterbach", "t32", "trace32", "t32marm"]
for "六代雷达" → ["RAD600", "6th gen radar", "gen6"]
```

这种方式有三个根本缺陷：

1. **无法穷举** — 每个用户的工具链、项目命名、行业术语都不同，不可能为每种情况写示例。
2. **示例即局限** — LLM 看到具体示例后倾向于只处理"像示例一样的"输入，遇到不像的就退化。
3. **没有利用 LLM 真正的能力** — LLM 本身就懂 "劳特巴赫 = Lauterbach"、"画图 = mspaint"，不需要教它这些知识。需要教的是**如何运用这些知识生成搜索参数**。

核心问题：prompt 在教 LLM **具体知识**，而不是教它**解题方法**。

---

## 设计思路

### 原则：教方法，不教知识

LLM 已经具备：
- 多语言翻译能力（中→英、音译还原、缩写展开）
- 对软件工具、品牌、产品的广泛知识
- 对文件命名约定的理解（snake_case, CamelCase 等）

我们需要做的不是往 prompt 里塞更多翻译映射，而是：

1. **明确告诉 LLM：文件系统是英文的** — 这是最关键的一条规则
2. **教会 LLM 生成搜索关键词的思维链** — 而不是给出结果
3. **注入用户个性化上下文** — 把用户的真实使用环境（项目列表、工具链）作为动态 context

### 三层优化

```
┌────────────────────────────────────────────────┐
│ Layer 1: 通用推理指令（静态，适用所有用户）        │
│   教 LLM "怎么想"，而非"答案是什么"              │
├────────────────────────────────────────────────┤
│ Layer 2: 用户环境上下文（动态，每个用户不同）      │
│   注入用户实际的项目、工具、路径信息              │
├────────────────────────────────────────────────┤
│ Layer 3: 使用历史反馈（自动积累）                 │
│   成功执行过的指令作为 few-shot 示例注入           │
└────────────────────────────────────────────────┘
```

---

## Layer 1: 通用推理指令

### 当前问题

当前 prompt 的 `synonyms` 说明：
```
- "synonyms": CRITICAL — you MUST translate and provide alternative names.
  e.g. for "劳特巴赫" → ["lauterbach", "t32", "trace32", "t32marm"]
```

这在教 LLM "劳特巴赫的翻译是什么"，而不是教它"遇到中文名时应该怎么做"。

### 优化后

将 `synonyms` 和整体 fuzzy 逻辑改为**推理指令**：

```
## Key principle: Think in filenames

The user speaks naturally, but files and programs on Windows have English names.
Your job is to BRIDGE the gap between human language and filesystem naming.

When generating synonyms and search_variants, follow this reasoning process:

1. TRANSLATE: If the user speaks in Chinese/other language about something
   with an English name, translate it.
   - "劳特巴赫" → think: this is "Lauterbach" (German debugger company)
   - "画图" → think: this is the Windows Paint program, "mspaint"

2. EXPAND: Generate all names the thing is known by.
   - Brand name, product name, CLI command, executable name, abbreviation
   - "Lauterbach" → also known as "TRACE32", "T32", exe is "t32marm"

3. GUESS FILE TYPE: What kind of file would this be stored as?
   - A "launcher script" → likely .bat, .cmd
   - An "application" → likely .exe
   - A "report" or "form" → likely .xlsx, .docx, .pdf

4. VARY THE FORMAT: Filenames use different conventions.
   - "SW Header Format" could be: SW_HeaderFormat, SW_Header_format,
     SWHeaderFormat, SW-Header-format

5. THINK ABOUT CONTEXT: Use contextual clues.
   - "六代" / "六代雷达" → this qualifies a project/product generation,
     search should include the generation identifier
   - "打开项目的XX" → XX is likely inside a project folder

Always ask yourself: "If I were to search for this in a file explorer,
what English keywords would I type?" — that's what synonyms should contain.
```

### 对比

| 维度 | 当前（教知识） | 优化后（教方法） |
|------|-------------|---------------|
| "画图" | prompt 里写死 `["mspaint", "paint"]` | LLM 自行推理出 mspaint |
| "劳特巴赫" | prompt 里写死 `["lauterbach", "t32"]` | LLM 从品牌知识推理出来 |
| "甘特图工具" | prompt 里没有，搜不到 | LLM 推理出 "gantt", "project", "ms project" |
| "代码质量检查" | prompt 里没有 | LLM 推理出 "lint", "sonar", "cppcheck" |

---

## Layer 2: 用户环境上下文

### 问题

LLM 不知道用户的电脑上有什么。用户说"打开六代劳特巴赫"，LLM 可以翻译出 "lauterbach"，但不知道文件具体叫 `Run_LauterbachToolBoxEnvironment_awr2944_ars620_s2a2.cmd`。

### 方案：自动收集用户环境，注入 prompt

在首次运行或定期（如每天一次）时，自动扫描用户环境生成一份**环境摘要**，作为 system prompt 的一部分注入：

```yaml
# ~/.gotit/user_context.yaml（自动生成 + 用户可编辑）

projects:
  - name: "RAD600 / RAD6XXCN"
    path: "D:\\02_Work\\repo\\RAD6XXCN_DevEnv"
    aliases: ["六代", "六代雷达", "RAD600"]
  - name: "RAD500"
    path: "D:\\02_Work\\repo\\RAD5XX_DevEnv"
    aliases: ["五代", "五代雷达"]

tools:
  - name: "Lauterbach TRACE32"
    launch_pattern: "*LauterbachToolBox*.cmd"
    aliases: ["劳特巴赫", "T32", "trace32"]
  - name: "Restbus Simulation"
    launch_pattern: "*restbus*.bat"
    aliases: ["restbus", "仿真"]

common_paths:
  - "D:\\02_Work\\repo"
  - "D:\\01_Engineering"
  - "D:\\03_Tools"
```

注入 prompt 的方式：

```
## User environment context

The user works in the following environment. Use this to resolve ambiguous references:

Projects:
- RAD600/RAD6XXCN at D:\02_Work\repo\RAD6XXCN_DevEnv (aliases: 六代, 六代雷达, RAD600)
- RAD500 at D:\02_Work\repo\RAD5XX_DevEnv (aliases: 五代, 五代雷达)

Tools:
- Lauterbach TRACE32: launch with *LauterbachToolBox*.cmd (aliases: 劳特巴赫, T32)
- Restbus Simulation: launch with *restbus*.bat (aliases: restbus, 仿真)
```

### 自动生成 vs 手动编辑

- **自动生成**：扫描 ActivityStore 中高频使用的程序和文件，提取项目路径模式，生成初始 context
- **手动编辑**：用户可以补充项目别名（"六代"→RAD600）、工具启动模式等
- **CLI 命令**：`gotit context show` / `gotit context edit` / `gotit context refresh`

### 自动收集逻辑

```python
def generate_user_context(activity_store, filter_rules) -> UserContext:
    """从活动历史中自动推断用户环境。"""

    # 1. 高频程序 → 工具列表
    top_programs = activity_store.get_top_programs(limit=20)
    # 按目录聚类 → 项目列表
    
    # 2. 高频文件路径 → 常用路径
    top_file_dirs = activity_store.get_top_directories(limit=10)
    
    # 3. 检测项目结构（含 .git 的目录 → 代码项目）
    ...
    
    return UserContext(projects=..., tools=..., common_paths=...)
```

---

## Layer 3: 使用历史反馈

### 问题

即使有了通用推理 + 环境上下文，LLM 第一次处理某种指令时仍可能生成不够好的 synonyms。但**一旦成功执行过一次**，我们就知道了正确的"话 → 文件"映射。

### 方案：成功执行记录作为 few-shot 示例

每次用户成功执行一个模糊查询时，记录这条映射：

```yaml
# ~/.gotit/learned_mappings.yaml（自动维护）

mappings:
  - input: "打开劳特巴赫"
    resolved_to: "D:\\02_Work\\repo\\RAD6XXCN_DevEnv\\DebugScripts\\Run_LauterbachToolBoxEnvironment_awr2944_ars620_s2a2.cmd"
    action: "open_file"
    timestamp: "2026-04-27"

  - input: "打开SW Header format表格"
    resolved_to: "D:\\01_Engineering\\SW_HeaderFormat.xlsx"
    action: "open_file"
    timestamp: "2026-04-27"
```

将最近的成功映射（最多 5~10 条）注入 prompt 作为动态 few-shot：

```
## Recent successful commands (for reference)

These are commands the user recently executed successfully.
Use them to understand the user's naming patterns:

- "打开劳特巴赫" → opened Run_LauterbachToolBoxEnvironment_awr2944_ars620_s2a2.cmd (bat/cmd script)
- "打开SW Header format表格" → opened SW_HeaderFormat.xlsx
```

这样 LLM 就知道这个用户说"劳特巴赫"时，文件名里有 "LauterbachToolBox"，下次会自动生成更好的 search_variants。

### 与 Quick Commands 的关系

- **Quick Commands**（`features/quick-commands.md`）：在 LLM **之前**匹配，完全跳过 LLM，毫秒级。适合高频固定指令。
- **Learned Mappings**（本方案 Layer 3）：仍然走 LLM，但用历史作为 few-shot 改善 LLM 输出质量。适合中低频或有变化的指令。

两者互补：
1. 第一次说"打开劳特巴赫" → 纯 LLM 推理（可能不够好）
2. 成功后 → 记录 learned mapping
3. 第二次说 → LLM 有 few-shot 参考，输出更准
4. 第三次说 → 推荐为 Quick Command，之后直接跳过 LLM

---

## 修改范围

### Layer 1（通用推理指令）

| 文件 | 变更 |
|------|------|
| `intent_system.txt` | 重写 fuzzy_hints 说明为推理指令，移除硬编码翻译示例 |

### Layer 2（用户环境上下文）

| 文件 | 变更 |
|------|------|
| `gotit/services/user_context.py` | **新增** — UserContext 加载/保存/自动生成 |
| `gotit/adapters/llm/claude.py` | 修改 — prompt 拼接时注入 user_context |
| `gotit/config.py` | 扩展 — `LLMConfig` 新增 `user_context_path` |
| `gotit/main.py` | 新增 — `gotit context` 子命令 |

### Layer 3（使用历史反馈）

| 文件 | 变更 |
|------|------|
| `gotit/services/learned_mappings.py` | **新增** — 成功执行记录 |
| `gotit/domain/pipeline.py` | 修改 — 执行成功后记录 mapping |
| `gotit/adapters/llm/claude.py` | 修改 — prompt 拼接时注入 recent mappings |

---

## 实施步骤

| 步骤 | 内容 | 优先级 |
|------|------|--------|
| 1 | 重写 intent_system.txt 的推理指令部分（Layer 1） | 高 — 零成本，立即生效 |
| 2 | 实现 learned_mappings（Layer 3）| 高 — 自动积累，越用越准 |
| 3 | 实现 user_context 自动生成（Layer 2） | 中 — 需要 ActivityStore 积累数据 |
| 4 | 实现 `gotit context` CLI 命令 | 中 |

建议 Layer 1 先做（只改 prompt 文本），然后 Layer 3（代码量小，价值高），最后 Layer 2。

---

## 预期效果

| 场景 | 当前 | Layer 1 后 | Layer 1+3 后 |
|------|------|-----------|-------------|
| "打开劳特巴赫" | 依赖 prompt 示例 | LLM 自行推理 lauterbach | LLM 推理 + 历史 few-shot 知道精确文件名 |
| "打开甘特图" | 搜不到 | LLM 推理出 gantt, ms project | 同左 |
| "打开六代 restbus" | 搜不到 | LLM 推理出 restbus + RAD600 | 历史记录知道具体 .bat 路径 |
| 新用户首次使用 | 需要先配置别名 | 开箱即用 | 用两三次后自动变准 |
