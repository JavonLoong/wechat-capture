# -*- coding: utf-8 -*-
"""
wechat_capture.html_render — 公共 HTML 渲染模板
支持截图导出和数据库导出两种数据源，输出风格一致的 HTML 文件。
"""
import base64
import os
from datetime import datetime


# ════════════════════════════════════════════
#  共享 CSS 样式
# ════════════════════════════════════════════

CSS = """\
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(180deg,#0f0c29 0%,#1a1a2e 50%,#16213e 100%);
     color:#eee;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;
     display:flex;flex-direction:column;align-items:center;padding:30px 20px;min-height:100vh}
.header{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);
        padding:25px 40px;border-radius:20px;margin-bottom:30px;text-align:center;
        border:1px solid rgba(255,255,255,.1);box-shadow:0 8px 32px rgba(0,0,0,.4)}
.header h1{font-size:1.8em;font-weight:700;margin-bottom:8px;
           background:linear-gradient(135deg,#a8edea,#fed6e3);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header p{opacity:.7;font-size:.9em}
.chat-container{width:100%;max-width:800px}
.page-container{margin:4px 0;border-radius:12px;overflow:hidden;
                box-shadow:0 4px 20px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.05);
                position:relative;max-width:800px}
.page-container img{display:block;width:100%;height:auto}
.page-label{position:absolute;top:8px;right:8px;background:rgba(0,0,0,.6);color:#fff;
            padding:4px 12px;border-radius:12px;font-size:11px;backdrop-filter:blur(4px)}
.date-divider{text-align:center;margin:20px 0;color:rgba(255,255,255,.4);
              font-size:.78em;position:relative}
.date-divider::before,.date-divider::after{content:'';position:absolute;top:50%;
  width:30%;height:1px;background:rgba(255,255,255,.1)}
.date-divider::before{left:0}.date-divider::after{right:0}
.msg{display:flex;margin:8px 0;gap:10px}
.msg.me{flex-direction:row-reverse}
.avatar{width:38px;height:38px;border-radius:8px;background:linear-gradient(135deg,#667eea,#764ba2);
        display:flex;align-items:center;justify-content:center;font-size:.8em;
        font-weight:700;flex-shrink:0}
.avatar.me{background:linear-gradient(135deg,#43c6ac,#191654)}
.bubble-wrap{max-width:65%;display:flex;flex-direction:column}
.msg.me .bubble-wrap{align-items:flex-end}
.sender-name{font-size:.72em;color:rgba(255,255,255,.5);margin-bottom:3px;padding:0 4px}
.bubble{padding:10px 14px;border-radius:16px;font-size:.92em;line-height:1.5;
        word-break:break-word;white-space:pre-wrap}
.bubble.them{background:rgba(255,255,255,.1);border-radius:16px 16px 16px 4px}
.bubble.me{background:linear-gradient(135deg,#43c6ac,#191654);border-radius:16px 16px 4px 16px}
.bubble.system{background:transparent;color:rgba(255,255,255,.4);font-size:.8em;
               text-align:center;padding:4px 10px;font-style:italic}
.bubble.meta{opacity:.6;font-style:italic}
.time{font-size:.68em;color:rgba(255,255,255,.3);margin-top:4px;padding:0 4px}
.stats{margin-top:30px;background:rgba(255,255,255,.05);padding:16px 24px;
       border-radius:12px;font-size:.85em;opacity:.7;text-align:center;
       border:1px solid rgba(255,255,255,.08)}
.footer{margin-top:30px;padding:20px;color:#445;font-size:12px;text-align:center}
"""


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ════════════════════════════════════════════
#  截图模式 HTML
# ════════════════════════════════════════════

def render_screenshot_html(contact_name, screenshot_dir, output_path):
    """将截图目录中的图片合成为 HTML 文件"""
    files = sorted(
        f for f in os.listdir(screenshot_dir)
        if f.startswith("page_") and f.endswith(".png")
    )
    if not files:
        raise FileNotFoundError(f"No screenshots found in {screenshot_dir}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>微信聊天记录 - {_esc(contact_name)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <h1>💬 {_esc(contact_name)}</h1>
  <p>聊天记录（截图模式）· 共 {len(files)} 页 · {now}</p>
</div>
"""]

    for i, f in enumerate(files):
        path = os.path.join(screenshot_dir, f)
        with open(path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()
        parts.append(f"""<div class="page-container">
  <span class="page-label">第 {i+1}/{len(files)} 页</span>
  <img src="data:image/png;base64,{b64}" alt="第{i+1}页">
</div>
""")

    parts.append(f"""<div class="footer">
  <p>由 wechat-capture 截图模式导出 · {now}</p>
</div>
</body></html>""")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))

    return len(files)


# ════════════════════════════════════════════
#  数据库模式 HTML
# ════════════════════════════════════════════

def render_database_html(contact_name, messages, output_path):
    """
    将消息列表渲染为 HTML 文件。
    messages: [(timestamp, is_me, text, msg_type), ...]
    msg_type: "text" | "meta" | "system"
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    self_initial = "我"
    them_initial = contact_name[0] if contact_name else "?"

    lines = []
    last_date = None

    for ts, is_me, text, msg_type in messages:
        dt = datetime.fromtimestamp(ts)
        date_str = dt.strftime("%Y年%m月%d日")
        time_str = dt.strftime("%H:%M")

        if date_str != last_date:
            lines.append(f'<div class="date-divider">{date_str}</div>')
            last_date = date_str

        if msg_type == "system":
            lines.append(
                f'<div class="msg"><div class="bubble-wrap" style="width:100%">'
                f'<div class="bubble system">{_esc(text)}</div></div></div>'
            )
            continue

        side = "me" if is_me else "them"
        initial = self_initial if is_me else them_initial
        bubble_cls = side + (" meta" if msg_type == "meta" else "")

        lines.append(
            f'<div class="msg {side}">'
            f'<div class="avatar {side}">{initial}</div>'
            f'<div class="bubble-wrap">'
            f'<div class="bubble {bubble_cls}">{_esc(text)}</div>'
            f'<div class="time">{time_str}</div>'
            f'</div></div>'
        )

    # 统计
    me_count = sum(1 for _, is_me, _, t in messages if is_me and t != "system")
    them_count = sum(1 for _, is_me, _, t in messages if not is_me and t != "system")
    if messages:
        first_dt = datetime.fromtimestamp(messages[0][0]).strftime("%Y-%m-%d")
        last_dt = datetime.fromtimestamp(messages[-1][0]).strftime("%Y-%m-%d")
    else:
        first_dt = last_dt = "—"

    body = "\n".join(lines)
    stats = (
        f'<div class="stats">'
        f'时间跨度: {first_dt} ~ {last_dt} &nbsp;|&nbsp; '
        f'我: {me_count} 条 &nbsp;|&nbsp; {_esc(contact_name)}: {them_count} 条'
        f'</div>'
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>微信聊天记录 - {_esc(contact_name)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <h1>💬 {_esc(contact_name)}</h1>
  <p>聊天记录（数据库模式）· 共 {len(messages)} 条 · {now}</p>
</div>
<div class="chat-container">
{body}
</div>
{stats}
<div class="footer">
  <p>由 wechat-capture 数据库模式导出 · {now}</p>
</div>
</body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return len(messages)
