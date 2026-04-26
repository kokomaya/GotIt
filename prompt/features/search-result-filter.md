# Feature: Search Result Filter — 搜索结果过滤器

> 过滤 Everything 返回的无关结果（如 `.git`、`node_modules`），支持用户自定义规则并持久化。

---

## 1. 问题

Everything 全盘搜索时会返回大量用户不关心的路径：

| 用户搜索 | 干扰结果 | 原因 |
|---------|---------|------|
| "adas_mtsi" | `...\adas_mtsi\.git` | Git 内部目录 |
| "config" | `...\node_modules\...\config.js` | npm 依赖 |
| "test" | `...\__pycache__\test.cpython-312.pyc` | Python 编译缓存 |
| "build" | `...\build\intermediates\...` | 构建产物 |

这些结果占据列表位置，降低查找效率，甚至导致错误打开（如打开了 `.git` 目录里的文件）。

---

## 2. 设计

### 2.1 两层过滤

| 层 | 时机 | 方式 | 说明 |
|----|------|------|------|
| **Everything 层** | 查询时 | `!path:` 排除语法 | 在 es.exe 参数中注入排除路径，不会进入结果 |
| **代码层** | 结果返回后 | Python 路径匹配 | 兜底过滤，处理 Everything 语法无法覆盖的场景 |

优先使用 Everything 层 — 让 es.exe 在索引层面排除，避免无效 IO。代码层做兜底。

### 2.2 过滤规则类型

```yaml
# ~/.gotit/filters.yaml
excluded_paths:
  - ".git"
  - ".svn"
  - ".hg"
  - "node_modules"
  - "__pycache__"
  - ".venv"
  - ".tox"
  - "$RECYCLE.BIN"
  - "System Volume Information"

excluded_filenames:
  - "desktop.ini"
  - "thumbs.db"
  - "~$*"              # Office 临时文件

excluded_extensions:
  - "pyc"
  - "pyo"
  - "obj"
  - "o"
  - "dll"
  - "sys"
```

三种规则：
- **`excluded_paths`** — 路径中包含这些目录名的结果被排除（路径片段匹配）
- **`excluded_filenames`** — 文件名匹配的结果被排除（支持 `*` 通配符）
- **`excluded_extensions`** — 扩展名匹配的结果被排除

### 2.3 持久化

过滤规则存储在 `~/.gotit/filters.yaml`：
- 首次运行时自动创建，写入内置默认规则
- 用户可直接编辑文件自定义规则
- 应用启动时加载，运行时可通过 API 重新加载
- YAML 格式，人类可读可编辑

为什么不用环境变量/`.env`：过滤规则是列表，YAML 比环境变量自然得多。且这是用户频繁编辑的配置，独立文件更方便。

### 2.4 Everything 层排除注入

es.exe 支持 `!path:` 排除语法：
```bash
es.exe "*adas_mtsi*" !path:.git !path:node_modules !path:__pycache__
```

在 `_build_query_args()` 中自动注入排除参数。

### 2.5 代码层兜底过滤

Everything 的 `!path:` 是路径子串匹配，但无法处理文件名通配符（如 `~$*`）和扩展名过滤。代码层在 es.exe 返回结果后做二次过滤：

```python
def _should_exclude(filepath: str, rules: FilterRules) -> bool:
    path_lower = filepath.lower()
    p = Path(filepath)

    # 路径片段排除
    parts = {part.lower() for part in p.parts}
    for excluded in rules.excluded_paths:
        if excluded.lower() in parts:
            return True

    # 文件名排除（支持通配符）
    name = p.name.lower()
    for pattern in rules.excluded_filenames:
        if fnmatch(name, pattern.lower()):
            return True

    # 扩展名排除
    ext = p.suffix.lstrip(".").lower()
    if ext in rules.excluded_extensions_set:
        return True

    return False
```

---

## 3. 模块设计

### 3.1 新增文件

```
gotit/
├── services/
│   └── filter_rules.py           # FilterRules 加载/保存/匹配
```

### 3.2 FilterRules 类

```python
@dataclass
class FilterRules:
    excluded_paths: list[str]
    excluded_filenames: list[str]
    excluded_extensions: list[str]

    @classmethod
    def load(cls, path: str = "~/.gotit/filters.yaml") -> FilterRules:
        """从 YAML 文件加载。文件不存在则创建默认规则。"""
        ...

    def save(self, path: str = "~/.gotit/filters.yaml") -> None:
        """保存到 YAML 文件。"""
        ...

    def should_exclude(self, filepath: str) -> bool:
        """判断路径是否应被过滤。"""
        ...

    def to_everything_excludes(self) -> list[str]:
        """生成 es.exe 的 !path: 排除参数列表。"""
        return [f"!path:{p}" for p in self.excluded_paths]
```

### 3.3 默认规则

```python
DEFAULT_EXCLUDED_PATHS = [
    ".git", ".svn", ".hg",
    "node_modules",
    "__pycache__", ".venv", ".tox", ".mypy_cache", ".ruff_cache",
    "$RECYCLE.BIN", "System Volume Information",
    ".vs", ".idea",
]

DEFAULT_EXCLUDED_FILENAMES = [
    "desktop.ini", "thumbs.db",
    "~$*",            # Office 临时锁文件
]

DEFAULT_EXCLUDED_EXTENSIONS = [
    "pyc", "pyo", "obj", "o", "lib",
    "tmp", "bak",
]
```

---

## 4. 集成点

### 4.1 EverythingAdapter

修改 `_build_query_args()` 和 `EverythingAdapter`：

```python
class EverythingAdapter:
    def __init__(self, config: SearchConfig, filter_rules: FilterRules | None = None):
        self._filter_rules = filter_rules
        ...

    async def search(self, query, filters):
        query_parts = _build_query_args(query, filters)

        # 注入 Everything 层排除
        if self._filter_rules:
            query_parts.extend(self._filter_rules.to_everything_excludes())

        cmd = [self._es_path, *query_parts, ...]
        ...

        # 代码层兜底过滤
        results = [...]
        if self._filter_rules:
            results = [r for r in results if not self._filter_rules.should_exclude(r.path)]

        return results
```

### 4.2 Container

在 `Container.__init__` 中加载 `FilterRules`，传入 `EverythingAdapter`。

### 4.3 Config

在 `SearchConfig` 中新增 `filter_rules_path`：

```python
class SearchConfig(BaseModel):
    everything_path: str = "es.exe"
    max_results: int = 20
    filter_rules_path: str = "~/.gotit/filters.yaml"
```

### 4.4 REST API（可选）

```
GET  /api/filters          — 获取当前过滤规则
PUT  /api/filters          — 更新过滤规则（保存到 YAML）
POST /api/filters/reload   — 重新从文件加载
```

---

## 5. 对现有代码的影响

| 文件 | 变更 | 说明 |
|------|------|------|
| `gotit/services/filter_rules.py` | **新增** | FilterRules 加载/保存/匹配 |
| `gotit/config.py` | 扩展 | SearchConfig 新增 `filter_rules_path` |
| `gotit/adapters/search/everything.py` | 修改 | 注入排除参数 + 结果后过滤 |
| `gotit/services/container.py` | 修改 | 加载 FilterRules，传入 EverythingAdapter |

---

## 6. 新增依赖

| 包 | 用途 |
|----|------|
| `pyyaml` | 解析/生成 YAML 过滤规则文件 |

---

## 7. 测试策略

- `test_filter_rules.py` — 加载/保存 YAML、路径匹配、文件名通配符、扩展名过滤、默认文件创建
- `test_everything_filter.py` — `to_everything_excludes()` 生成的 `!path:` 参数、搜索结果过滤集成
- 手动验证：搜索 "adas_mtsi" 不再返回 `.git` 路径

---

## 8. 实施步骤

| 步骤 | 内容 | 依赖 |
|------|------|------|
| 1 | 添加 `pyyaml` 依赖 | - |
| 2 | 实现 `filter_rules.py`（FilterRules + 默认规则 + YAML 读写）+ 测试 | 1 |
| 3 | 修改 `SearchConfig` 新增 `filter_rules_path` | - |
| 4 | 修改 `EverythingAdapter` 注入排除 + 结果过滤 | 2 |
| 5 | 修改 `container.py` 加载 FilterRules | 2,3 |
| 6 | 集成测试 + 端到端验证 | 5 |
