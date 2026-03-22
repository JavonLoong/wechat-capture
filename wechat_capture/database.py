# -*- coding: utf-8 -*-
"""
wechat_capture.database — 方法二：数据库导出
从解密后的微信本地数据库读取聊天记录，生成 HTML。
需要先用 wechat-decrypt 等工具解密数据库。
"""
import hashlib
import os
import re
import sqlite3
import sys

from .html_render import render_database_html


# ─────────────────── 联系人 ───────────────────

def load_contacts(decrypted_dir):
    """加载联系人表，返回 {username: display_name}"""
    db = os.path.join(decrypted_dir, "contact", "contact.db")
    if not os.path.exists(db):
        raise FileNotFoundError(f"联系人数据库不存在: {db}")

    conn = sqlite3.connect(db)
    names = {}
    for username, nick, remark in conn.execute(
        "SELECT username, nick_name, remark FROM contact"
    ).fetchall():
        names[username] = remark or nick or username
    conn.close()
    return names


def find_contact(query, contacts):
    """模糊搜索联系人，返回 (username, display_name) 或 None"""
    q = query.lower()
    # 精确匹配
    for uname, display in contacts.items():
        if q == display.lower() or q == uname.lower():
            return uname, display
    # 模糊匹配
    for uname, display in contacts.items():
        if q in display.lower() or q in uname.lower():
            return uname, display
    return None


# ─────────────────── 消息 ───────────────────

def _find_msg_dbs(decrypted_dir):
    """查找所有 message_N.db 文件"""
    msg_dir = os.path.join(decrypted_dir, "message")
    if not os.path.isdir(msg_dir):
        return []
    return sorted(
        os.path.join(msg_dir, f)
        for f in os.listdir(msg_dir)
        if re.match(r"message_\d+\.db$", f)
    )


def _find_msg_table(decrypted_dir, username):
    """在所有 message_N.db 中找包含该用户消息表的 (conn, table_name)"""
    table_name = "Msg_" + hashlib.md5(username.encode()).hexdigest()
    for db_path in _find_msg_dbs(decrypted_dir):
        conn = sqlite3.connect(db_path)
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        if exists:
            return conn, table_name
        conn.close()
    return None, None


def _decompress_content(content, ct):
    """解压消息内容（支持 zstd 压缩）"""
    if ct == 4 and isinstance(content, bytes):
        try:
            import zstandard
            return zstandard.ZstdDecompressor().decompress(content).decode("utf-8", errors="replace")
        except Exception:
            pass
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return content or ""


def _parse_type(local_type):
    t = int(local_type) if local_type else 0
    if t > 0xFFFFFFFF:
        return t & 0xFFFFFFFF, t >> 32
    return t, 0


def _format_content(local_type, content):
    """将消息类型和内容转换为显示文本和类型标记"""
    base, _ = _parse_type(local_type)
    type_map = {
        1: (content, "text"),
        3: ("[图片]", "meta"),
        34: ("[语音消息]", "meta"),
        43: ("[视频]", "meta"),
        47: ("[表情包]", "meta"),
        48: ("[位置]", "meta"),
        50: ("[语音通话]", "meta"),
        10000: (content or "[系统消息]", "system"),
        10002: ("[撤回了一条消息]", "system"),
    }
    if base in type_map:
        return type_map[base]
    if base == 49:
        if content and "<title>" in content:
            m = re.search(r"<title>(.*?)</title>", content, re.S)
            if m:
                return f"[链接] {m.group(1).strip()[:80]}", "meta"
        return "[链接/文件]", "meta"
    return content or f"[type={local_type}]", "meta"


# ─────────────────── 主流程 ───────────────────

def export(contact_name, decrypted_dir, output_dir="./output"):
    """
    数据库导出微信聊天记录。

    Args:
        contact_name: 联系人名称/备注名
        decrypted_dir: wechat-decrypt 解密后的数据目录
        output_dir: 输出目录

    Returns:
        输出的 HTML 文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"[wechat-capture] 数据库模式 — {contact_name}")
    print(f"[wechat-capture] 数据库目录: {decrypted_dir}")

    # 1. 加载联系人
    contacts = load_contacts(decrypted_dir)
    result = find_contact(contact_name, contacts)
    if not result:
        candidates = [
            (u, d) for u, d in contacts.items()
            if contact_name.lower() in d.lower() or contact_name.lower() in u.lower()
        ]
        if candidates:
            print(f"[wechat-capture] ❌ 未找到精确匹配，相似联系人：")
            for u, d in candidates[:10]:
                print(f"  {d}  ({u})")
        else:
            print("[wechat-capture] ❌ 未找到匹配的联系人")
        sys.exit(1)

    username, display_name = result
    print(f"[wechat-capture] ✅ 找到联系人: {display_name} ({username})")

    # 2. 查找消息表
    conn, table_name = _find_msg_table(decrypted_dir, username)
    if not conn:
        print(f"[wechat-capture] ❌ 未找到消息表")
        sys.exit(1)

    # 3. 读取消息
    raw_rows = conn.execute(f"""
        SELECT local_id, local_type, create_time, real_sender_id, message_content,
               WCDB_CT_message_content
        FROM [{table_name}]
        ORDER BY create_time ASC
    """).fetchall()
    conn.close()

    print(f"[wechat-capture] 共 {len(raw_rows)} 条消息，正在处理...")

    messages = []
    for local_id, local_type, create_time, real_sender_id, content, ct in raw_rows:
        content = _decompress_content(content, ct)
        text, msg_type = _format_content(local_type, content)
        is_me = (real_sender_id == 0)
        messages.append((create_time, is_me, text, msg_type))

    # 4. 生成 HTML
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", display_name)
    output_path = os.path.join(output_dir, f"{safe_name}_聊天记录.html")
    render_database_html(display_name, messages, output_path)

    file_size = os.path.getsize(output_path) / 1024 / 1024
    print(f"[wechat-capture] ✅ 导出完成: {output_path} ({file_size:.1f} MB, {len(messages)} 条)")

    return output_path
