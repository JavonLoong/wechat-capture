# wechat-capture

Export WeChat chat history with zero reverse-engineering — a dual-engine approach.

[中文文档](README_CN.md)

## Features

| Mode | How it works | Pros | Cons |
|------|-------------|------|------|
| **Screenshot** | Auto-scrolls WeChat window & captures screenshots | Zero intrusion, no keys needed | Image-only, not searchable |
| **Database** | Reads decrypted local SQLite databases | Structured text, fast, searchable | Requires database decryption |

Both modes export to a beautiful, self-contained HTML file with a dark-themed UI.

## Installation

```bash
pip install -e .

# For database mode with zstd support:
pip install -e ".[database]"
```

### Dependencies
- Python 3.8+
- Windows (WeChat PC only)
- WeChat PC must be open and logged in

## Usage

### CLI

#### Screenshot Mode (Zero Intrusion)

Open the chat you want to export in WeChat, then run:

```bash
wechat-capture screenshot "联系人名" --output-dir ./output
```

The tool will automatically scroll to the top, capture every page, and generate an HTML file.

#### Database Mode

First decrypt the WeChat database using tools like [wechat-decrypt](https://github.com/nickliqian/wechat-decrypt), then:

```bash
# Basic usage (may have sender identification issues)
wechat-capture database "联系人名" --db-dir /path/to/decrypted --output-dir ./output

# Recommended: with config.json for accurate sender identification
wechat-capture database "联系人名" --db-dir /path/to/decrypted --config /path/to/config.json

# Or directly specify your wxid
wechat-capture database "联系人名" --db-dir /path/to/decrypted --self-wxid wxid_abc123
```

### Python API (for AI agents and scripts)

```python
from wechat_capture import screenshot_export, database_export

# Screenshot mode
result = screenshot_export("联系人名", output_dir="./output")
print(result["html_path"])   # Path to generated HTML
print(result["pages"])       # Number of pages captured

# Database mode (recommended: provide config_file or self_wxid)
result = database_export(
    "联系人名",
    decrypted_dir="/path/to/decrypted",
    output_dir="./output",
    config_file="/path/to/config.json",  # for accurate sender detection
)
print(result["html_path"])      # Path to generated HTML
print(result["contact_name"])   # Display name
print(result["stats"])          # {"me_count": 50, "them_count": 38, ...}
print(result["messages"][:5])   # [(timestamp, is_me, text, msg_type), ...]
```

#### Return Values

Both `screenshot_export()` and `database_export()` return a dict:

**Screenshot mode:**
```python
{
    "html_path": str,        # Path to the HTML file
    "contact_name": str,     # Contact name
    "pages": int,            # Number of pages captured
    "screenshot_dir": str,   # Directory with PNG files
}
```

**Database mode:**
```python
{
    "html_path": str,        # Path to the HTML file
    "contact_name": str,     # Display name of the contact
    "username": str,         # WeChat internal username
    "messages": list,        # [(timestamp, is_me, text, msg_type), ...]
    "stats": {
        "me_count": int,
        "them_count": int,
        "first_date": str,   # "2024-01-01"
        "last_date": str,
        "total": int,
    },
}
```

## Sender Identification (Database Mode)

WeChat 4.0 databases use `real_sender_id` to identify message senders, but the value is a rowid in the `Name2Id` table — **not a fixed 0/1**. To correctly distinguish "my messages" from "their messages", provide one of:

- `--config` / `config_file`: Path to wechat-decrypt's `config.json` (contains `db_dir` with your `wxid_xxx`)
- `--self-wxid` / `self_wxid`: Your wxid string directly

Without these, the tool falls back to a heuristic (`real_sender_id == 0`) which may be incorrect.

## Output Example

The exported HTML features:
- Dark gradient background with glassmorphism header
- Embedded images (self-contained, no external dependencies)
- Page labels for screenshot mode
- Chat bubble UI with timestamps for database mode
- Statistics (message count, date range)

## How Screenshot Mode Works

1. Finds the WeChat window via Win32 API
2. Auto-detects the input box boundary using pixel color scanning
3. Sends `Ctrl+Home` + scroll to reach the top of chat history
4. Takes a screenshot of the chat area, then presses `PageDown`
5. Repeats until the bottom is reached (detects stable screen hash)
6. Compiles all screenshots into a single HTML file

## License

MIT
