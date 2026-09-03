# Koi2Notion

将 Kindle 剪贴板（`My Clippings.txt`）中的高亮和笔记同步到 Notion 数据库。

## 功能

- **中文剪贴板解析** — 支持 Kindle 中文系统导出的格式（页/位置/添加于/笔记）
- **增量同步** — 基于文件签名（mtime + size）跳过未变化的文件，已同步的条目不会重复写入
- **标题模糊匹配** — NFC 标准化 + casefold，避免因编码差异创建重复页面
- **作者同步** — 从剪贴板解析的作者名自动写入 Notion 数据库的「作者」属性
- **笔记关联** — 按页码/位置范围匹配，将笔记附加到对应的高亮下方
- **Watch 模式** — 定时监听文件变化，自动触发同步
- **自定义 Notion 客户端** — 基于 `requests`，内置重试（429/5xx/SSL），无需 `notional` 等重型依赖

## 前置条件

- Python 3.10+
- 一个 Notion 集成 Token（[在此创建](https://www.notion.so/my-integrations)）
- 目标数据库需要包含以下属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| 书名 | title | 书名（默认标题属性，重命名为「书名」） |
| 作者 | rich_text | 作者名 |

数据库需要与你的 Notion 集成共享（在数据库页面点 Share → 选择集成）。

## 安装

```bash
cd kindle2notion
pip install -r requirements.txt
```

## 配置

### 交互式初始化

```bash
python -m kindle2notion init
```

按提示输入 Notion Token、数据库 ID 和 `My Clippings.txt` 路径，会自动生成 `config.json`。

### 手动配置

在项目根目录创建 `config.json`：

```json
{
    "notion_token": "ntn_xxx",
    "database_id": "你的数据库 ID",
    "clippings_file": "E:\\Kindle\\documents\\My Clippings.txt",
    "title_alias": null,
    "watch_interval": 300
}
```

| 字段 | 说明 |
|------|------|
| `notion_token` | Notion 集成 Token |
| `database_id` | 目标数据库 ID（从数据库 URL 中获取） |
| `clippings_file` | `My Clippings.txt` 的完整路径 |
| `title_alias` | 可选，标题别名映射文件路径（JSON），用于将剪贴板中的书名映射到 Notion 中的书名 |
| `watch_interval` | Watch 模式下的检查间隔，单位秒，默认 300 |

## 使用

### 单次同步

```bash
python -m kindle2notion
```

### Watch 模式

```bash
python -m kindle2notion --watch
```

监听 `My Clippings.txt` 的文件变化，检测到变化后自动同步。通过 `sync_state.json` 记录已处理的文件签名，避免重复同步。

## 项目结构

```
kindle2notion/
├── config.json          # 配置文件（含 Token，已 gitignore）
├── sync_state.json      # Watch 模式的状态记录
├── kindle2notion/
│   ├── __main__.py      # CLI 入口，配置加载，watch 循环
│   ├── reading.py       # 读取 My Clippings.txt（UTF-8-sig + BOM 处理）
│   ├── parsing.py       # 解析剪贴板（中英文格式）
│   ├── exporting.py     # 导出到 Notion（去重、标题匹配、笔记配对）
│   └── notion_client.py # Notion API 客户端
└── tests/
```

## 同步逻辑

1. 读取并解析 `My Clippings.txt`，按书名分组
2. 对每本书，在 Notion 数据库中查找已有页面（精确匹配 → 模糊匹配）
3. 找不到则创建新页面，同时写入书名和作者
4. 读取页面已有的 quote block，与待同步条目去重
5. 将笔记按页码/位置范围配对到对应高亮
6. 构建 block（divider → quote → 笔记 → 日期）追加到页面

## License

MIT
