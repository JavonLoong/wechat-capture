# wechat-capture 微信聊天记录导出

> **双引擎方案**：截图导出（零侵入）+ 数据库导出（高保真）

## 特性

| 模式 | 原理 | 需要密钥？ | 微信更新后还能用？ |
|------|------|-----------|------------------|
| **截图模式** | 自动滚动微信窗口，逐页截屏 | ❌ 不需要 | ✅ 不受影响 |
| **数据库模式** | 读取解密后的本地 SQLite 数据库 | ✅ 需要 | ❌ 可能失效 |

两种模式都输出精美的、自包含的 HTML 文件。

## 安装

```bash
pip install -e .
```

### 环境要求

- Python 3.8+
- Windows 系统
- 微信 PC 版已打开并登录

## 使用方法

### 截图模式（推荐，零侵入）

先在微信中打开要导出的聊天窗口，然后运行：

```bash
wechat-capture screenshot "联系人名" -o ./output
```

工具会自动滚动到聊天顶部，逐页截图，最后生成 HTML 文件。

### 数据库模式

先使用 [wechat-decrypt](https://github.com/nickliqian/wechat-decrypt) 等工具解密微信数据库，然后：

```bash
wechat-capture database "联系人名" --db-dir /path/to/decrypted -o ./output
```

## 截图模式的工作原理

1. 通过 Win32 API 找到微信窗口
2. **自动检测输入框边界**（像素颜色扫描），确保输入框不会被截进来
3. 发送 `Ctrl+Home` + 滚轮滚动到聊天顶部
4. 逐页截图 → `PageDown` → 重复
5. 通过屏幕哈希检测到达底部后停止
6. 将所有截图合并为一个 HTML 文件

## 许可证

MIT
