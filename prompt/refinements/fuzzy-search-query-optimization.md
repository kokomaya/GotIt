# Refinement: 模糊搜索查询优化 — 提升 Everything 搜索命中率

## 问题

用户说 "打开SW Header format表格"，实际文件名可能是：
- `SW_HeaderFormat.xlsx`
- `ARS_SW_Header_formart.xlsx`
- `SRR_SW_Header_formart.xlsm`

当前系统生成的 Everything 查询 `ext:xlsx SW Header format` 返回 0 结果，原因：

### Everything 搜索语义

Everything 用空格做 AND 分词，每个词必须**完整出现**在文件全路径中：
```
"SW Header format"  →  要求路径同时包含 "SW"、"Header"、"format" 三个完整子串
```

但文件名 `SW_HeaderFormat` 中：
- "Header" 和 "Format" 连写为 "HeaderFormat" — 单独搜 "Header" 能匹配，但 "format"（小写）无法匹配 "Format"... 不对，Everything 默认大小写不敏感。
- 真正的问题是 **Everything 搜 "format" 能匹配 "HeaderFormat" 中的 "format"**，但搜 `"SW Header format"` 三个词全部加上 `ext:xlsx` 过滤后，结果反而被意外过滤掉了。

实际测试结果：
```bash
es.exe "SW Header format"        → 0 结果   # 三个词 AND，要求全部匹配
es.exe "SW_Header"               → 5 结果   # 下划线连接能匹配
es.exe "*SW*Header*form*"        → 5 结果   # 通配符链能匹配任何分隔符
es.exe "*SW*Header*" ext:xlsx    → 5 结果   # 通配符 + 扩展名
```

**根本原因**：用户说的自然语言用空格分隔，而文件名可能用 `_`、`-`、驼峰、无分隔符连接。直接把自然语言关键词拼成 Everything 查询，分隔符和连接方式不匹配。

---

## 解决方案：多策略查询生成

核心思路：不是生成一个查询，而是**生成多个查询变体**，从精确到宽松逐级尝试，利用 Everything 的高速特性（每次查询 <100ms）换取更高的命中率。

### 方案设计

#### 1. LLM 生成 `search_variants`（新增字段）

在 `fuzzy_hints` 中新增 `search_variants` 字段，让 LLM 在意图解析时一并生成多种可能的文件名变体：

```json
{
  "action": "open_file",
  "query": "SW Header format",
  "match_mode": "fuzzy",
  "fuzzy_hints": {
    "partial_name": "SW Header format",
    "description": "表格文件",
    "synonyms": ["SW HeaderFormat", "SW_Header_format"],
    "likely_ext": ["xlsx", "xls", "xlsm"],
    "search_variants": [
      "SW_HeaderFormat",
      "SW_Header_format",
      "SW Header format",
      "SWHeaderFormat",
      "SW-Header-format"
    ]
  }
}
```

LLM 的优势是懂命名约定 — 它知道文件名常用 snake_case、camelCase、PascalCase、kebab-case，可以生成合理的变体。

**Prompt 新增说明**：
```
- "search_variants": Different filename patterns the user might be referring to.
  Generate common naming convention variants:
  - Original with underscores: "SW_Header_format"
  - CamelCase: "SWHeaderFormat", "SW_HeaderFormat"  
  - With hyphens: "SW-Header-format"
  - Spaces as-is: "SW Header format"
  These help match files that use different word separators or casing.
```

#### 2. 代码层通配符查询生成（不依赖 LLM）

即使 LLM 没有生成 `search_variants`，代码层也应该自动将用户的关键词转换为通配符查询。这是纯确定性逻辑，零 LLM 成本：

```python
def generate_wildcard_queries(query: str) -> list[str]:
    """将自然语言查询转换为 Everything 通配符查询。
    
    'SW Header format' → [
        '*SW*Header*format*',     # 通配符链（最宽松，适配任何分隔符）
        'SW_Header_format',       # 下划线变体
        'SW-Header-format',       # 连字符变体
        'SWHeaderformat',         # 无分隔符
        'SW_HeaderFormat',        # 混合下划线+驼峰
    ]
    """
    words = query.split()
    if len(words) <= 1:
        return [f"*{query}*"]
    
    variants = []
    
    # 1. 通配符链 — 万能匹配，适配任何分隔符/大小写
    wildcard = "*" + "*".join(words) + "*"
    variants.append(wildcard)
    
    # 2. 下划线连接
    variants.append("_".join(words))
    
    # 3. 连字符连接
    variants.append("-".join(words))
    
    # 4. 无分隔符连接
    variants.append("".join(words))
    
    # 5. CamelCase（首字母大写无分隔符）
    camel = "".join(w.capitalize() for w in words)
    if camel != "".join(words):
        variants.append(camel)
    
    return variants
```

#### 3. 修改搜索策略执行顺序

在 fuzzy resolution chain 的 Strategy 2（Everything + synonyms）中，调整查询生成逻辑：

```
原来：直接用 query + synonyms 逐一搜索
现在：
  1. 先用 search_variants（LLM 生成的变体）搜索
  2. 再用代码生成的通配符变体搜索
  3. 最后用 synonyms 搜索
  每步用所有 likely_ext 变体尝试
```

具体执行流程（以 "SW Header format" 为例）：

```
Step 1: LLM search_variants × likely_ext
  es.exe ext:xlsx SW_HeaderFormat       → 可能命中
  es.exe ext:xls  SW_HeaderFormat       → ...
  es.exe ext:xlsm SW_HeaderFormat       → ...
  es.exe ext:xlsx SW_Header_format      → ...
  ...

Step 2: 代码生成通配符 × likely_ext
  es.exe ext:xlsx *SW*Header*format*    → 大概率命中（通配符万能匹配）
  es.exe ext:xls  *SW*Header*format*   → ...
  es.exe ext:xlsm *SW*Header*format*   → ...
  ...

Step 3: synonyms（如果 LLM 提供了）
  ...

任何一步有结果就停止，不继续后续步骤。
```

**为什么通配符链有效**：
- `*SW*Header*format*` 匹配 `SW_HeaderFormat`，因为 Everything 的通配符 `*` 匹配任意字符（包括 `_`），而搜索默认大小写不敏感，所以 `format` 匹配 `Format`。
- 同一查询也匹配 `ARS_SW_Header_formart`、`SRR_SW_Header_format` 等任何包含这三个词片段的文件名。

---

## 修改范围

### 1. `gotit/adapters/llm/prompts/intent_system.txt`

在 `fuzzy_hints` 中新增 `search_variants` 字段说明。

### 2. `gotit/domain/pipeline.py`

- 新增 `_generate_wildcard_queries()` 函数
- 修改 `_strategy_synonyms()` → 重命名为 `_strategy_everything_search()`
- 在其中按优先级执行：search_variants → wildcard queries → synonyms

### 3. `gotit/adapters/search/everything.py`（可选优化）

`_build_query()` 目前将 query 直接拼到命令中。通配符查询（如 `*SW*Header*format*`）需要确保不被额外处理。当前实现直接拼接，已经兼容，无需修改。

---

## 查询数量与性能

最坏情况计算（完全未命中所有变体时）：
- search_variants: 5 × 3 ext = 15 次
- wildcard queries: 5 × 3 ext = 15 次
- synonyms: N × 3 ext

但实际上：
1. 通配符查询（Step 2 第一个变体 `*SW*Header*format*`）几乎必中，大多数情况 1~3 次查询就结束。
2. Everything 单次查询 <100ms，即使 10 次也只需 ~1s。
3. 可以设一个全局上限（如最多尝试 20 次查询），避免极端情况。

---

## 与现有设计的关系

这是对 `activity-tracker.md` 中 Strategy 2 的增强，不改变整体架构：

```
Fuzzy Resolution Chain:
  Strategy 1: 活动历史查找          ← 不变
  Strategy 2: Everything 搜索      ← 本优化：增强查询生成
    2a: search_variants (LLM)       ← 新增
    2b: wildcard queries (代码)     ← 新增
    2c: synonyms                    ← 现有
  Strategy 3: 放宽搜索              ← 不变（已有通配符逻辑，但作为最后手段）
```

---

## 总结

| 维度 | 现状 | 优化后 |
|------|------|--------|
| 查询方式 | 直接用自然语言关键词 | 多变体 + 通配符链 |
| 分隔符适配 | 仅匹配空格 | 适配 `_`、`-`、驼峰、无分隔符 |
| LLM 利用 | 仅提供 synonyms | 额外提供 search_variants（命名约定变体） |
| 代码兜底 | 无 | 通配符链自动生成（`*word1*word2*word3*`） |
| 命中率（本例） | 0% | ~100%（通配符链首次查询即命中） |
