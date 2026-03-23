# wechat-capture

导出微信聊天记录 — 无需逆向工程的双引擎方案。

[English](README.md)

## 功能特性

| 模式 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **截图模式** | 自动滚动微信窗口并截图 | 零侵入，无需密钥 | 仅图片，不可搜索 |
| **数据库模式** | 读取解密后的本地 SQLite 数据库 | 结构化文本，快速，可搜索 | 需要先解密数据库 |

两种模式均导出为精美的深色主题 HTML 文件。

## 安装

```bash
pip install -e .

# 数据库模式需要 zstd 支持：
pip install -e ".[database]"
```

### 依赖
- Python 3.8+
- Windows（仅支持微信 PC 版）
- 微信 PC 版需保持打开并登录

## 使用方法

### 命令行

#### 截图模式（零侵入）

在微信中打开要导出的聊天，然后运行：

```bash
wechat-capture screenshot "联系人名" --output-dir ./output
```

#### 数据库模式

先用 [wechat-decrypt](https://github.com/nickliqian/wechat-decrypt) 等工具解密数据库，然后：

```bash
# 基本用法
wechat-capture database "联系人名" --db-dir /path/to/decrypted

# 推荐：指定 config.json 以准确识别消息发送方
wechat-capture database "联系人名" --db-dir /path/to/decrypted --config /path/to/config.json

# 或直接指定你的 wxid
wechat-capture database "联系人名" --db-dir /path/to/decrypted --self-wxid wxid_abc123
```

### Python API（适用于 AI Agent 和脚本）

```python
from wechat_capture import screenshot_export, database_export

# 截图模式
result = screenshot_export("联系人名", output_dir="./output")
print(result["html_path"])   # 生成的 HTML 路径
print(result["pages"])       # 截图页数

# 数据库模式（推荐提供 config_file 或 self_wxid）
result = database_export(
    "联系人名",
    decrypted_dir="/path/to/decrypted",
    output_dir="./output",
    config_file="/path/to/config.json",  # 用于准确识别发送方
)
print(result["html_path"])      # HTML 路径
print(result["contact_name"])   # 联系人显示名
print(result["stats"])          # {"me_count": 50, "them_count": 38, ...}
print(result["messages"][:5])   # [(时间戳, 是否是我, 文本, 消息类型), ...]
```

## 发送方识别（数据库模式）

微信 4.0 数据库使用 `real_sender_id` 标识消息发送方，但该值是 `Name2Id` 表中的 rowid，**不是固定的 0/1**。为正确区分"我发的"和"对方发的"，请提供：

- `--config` / `config_file`：wechat-decrypt 的 `config.json` 路径
- `--self-wxid` / `self_wxid`：你的 wxid 字符串

不提供时会回退到启发式判断 (`real_sender_id == 0`)，可能不准确。

## 许可证

MIT
