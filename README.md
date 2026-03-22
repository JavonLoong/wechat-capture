# wechat-capture

> Export WeChat chat history with **zero reverse-engineering** — a dual-engine approach.

[中文文档](./README_CN.md)

## Features

| Mode | How it works | Need decryption key? | Survives WeChat updates? |
|------|-------------|---------------------|------------------------|
| **Screenshot** | Auto-scrolls the WeChat window and captures each page | ❌ No | ✅ Yes |
| **Database** | Reads decrypted local SQLite databases | ✅ Yes | ❌ May break |

Both modes export to a beautiful, self-contained HTML file with a dark-themed UI.

## Installation

```bash
pip install -e .
```

### Dependencies

- Python 3.8+
- Windows (WeChat PC only)
- WeChat PC must be open and logged in

## Usage

### Screenshot Mode (Zero Intrusion)

Open the chat you want to export in WeChat, then run:

```bash
wechat-capture screenshot "联系人名" --output-dir ./output
```

The tool will automatically scroll to the top, capture every page, and generate an HTML file.

### Database Mode

First decrypt the WeChat database using tools like [wechat-decrypt](https://github.com/nickliqian/wechat-decrypt), then:

```bash
wechat-capture database "联系人名" --db-dir /path/to/decrypted --output-dir ./output
```

## Output Example

The exported HTML features:
- Dark gradient background with glassmorphism header
- Embedded images (self-contained, no external dependencies)
- Page labels for screenshot mode
- Chat bubble UI with timestamps for database mode
- Statistics (message count, date range)

## How Screenshot Mode Works

1. Finds the WeChat window via Win32 API
2. **Auto-detects the input box boundary** using pixel color scanning (so it's never captured)
3. Sends `Ctrl+Home` + scroll to reach the top of chat history
4. Takes a screenshot of the chat area, then presses `PageDown`
5. Repeats until the bottom is reached (detects stable screen hash)
6. Compiles all screenshots into a single HTML file

## License

MIT
