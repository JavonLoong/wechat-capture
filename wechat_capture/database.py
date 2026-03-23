# -*- coding: utf-8 -*-
"""
wechat_capture.database — Method 2: Database export

Read chat messages from decrypted WeChat local databases and generate HTML.
Requires pre-decrypted databases (e.g. via wechat-decrypt).

Key improvement over naive approach: uses Name2Id table + self_wxid
to correctly identify message sender (fixes the is_me detection bug).
"""
import hashlib
import json
import os
import re
import sqlite3
import sys

from .html_render import render_database_html


# ─────────────────── Contacts ───────────────────

def load_contacts(decrypted_dir):
    """Load contacts table, returns {username: display_name}"""
    db = os.path.join(decrypted_dir, "contact", "contact.db")
    if not os.path.exists(db):
        raise FileNotFoundError(f"Contact database not found: {db}")

    conn = sqlite3.connect(db)
    names = {}
    for username, nick, remark in conn.execute(
        "SELECT username, nick_name, remark FROM contact"
    ).fetchall():
        names[username] = remark or nick or username
    conn.close()
    return names


def find_contact(query, contacts):
    """Fuzzy search contacts, returns (username, display_name) or None"""
    q = query.lower()
    # Exact match
    for uname, display in contacts.items():
        if q == display.lower() or q == uname.lower():
            return uname, display
    # Fuzzy match
    for uname, display in contacts.items():
        if q in display.lower() or q in uname.lower():
            return uname, display
    return None


# ─────────────────── Self ID Detection ───────────────────

def _get_self_wxid(config_file=None, self_wxid=None):
    """
    Determine self wxid from (in priority order):
    1. Directly provided self_wxid parameter
    2. config.json file (db_dir field contains wxid_xxx)
    """
    if self_wxid:
        return self_wxid

    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, encoding="utf-8") as f:
                cfg = json.load(f)
            db_dir = cfg.get("db_dir", "")
            m = re.search(r"(wxid_[a-z0-9]+)", db_dir)
            if m:
                return m.group(1)
        except Exception:
            pass

    return None


def _get_self_sender_id(conn, self_wxid):
    """
    Look up self wxid in the Name2Id table to get the rowid
    used as real_sender_id for messages sent by self.
    """
    if not self_wxid:
        return None
    try:
        rows = conn.execute("SELECT rowid, user_name FROM Name2Id").fetchall()
        for rowid, uname in rows:
            if uname == self_wxid:
                return rowid
    except Exception:
        pass
    return None


# ─────────────────── Messages ───────────────────

def _find_msg_dbs(decrypted_dir):
    """Find all message_N.db files"""
    msg_dir = os.path.join(decrypted_dir, "message")
    if not os.path.isdir(msg_dir):
        return []
    return sorted(
        os.path.join(msg_dir, f)
        for f in os.listdir(msg_dir)
        if re.match(r"message_\d+\.db$", f)
    )


def _find_msg_table(decrypted_dir, username):
    """Find the message table for a user across all message_N.db shards.
    Returns (conn, table_name) or (None, None)"""
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
    """Decompress message content (supports zstd compression)"""
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
    """Convert message type and content to display text and type tag"""
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


# ─────────────────── Main Export ───────────────────

def export(contact_name, decrypted_dir, output_dir="./output",
           config_file=None, self_wxid=None):
    """
    Export WeChat chat history from decrypted databases.

    Args:
        contact_name: Contact name or remark name to search for
        decrypted_dir: Path to wechat-decrypt decrypted data directory
        output_dir: Output directory for the HTML file
        config_file: Optional path to wechat-decrypt config.json
                     (used to extract self wxid for sender identification)
        self_wxid: Optional self wxid string (e.g. "wxid_abc123").
                   Takes priority over config_file.

    Returns:
        dict with keys:
            - html_path (str): Path to the generated HTML file
            - contact_name (str): Display name of the contact
            - username (str): WeChat internal username
            - messages (list): List of (timestamp, is_me, text, msg_type) tuples
            - stats (dict): {"me_count": int, "them_count": int,
                             "first_date": str, "last_date": str, "total": int}
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"[wechat-capture] 数据库模式 — {contact_name}")
    print(f"[wechat-capture] 数据库目录: {decrypted_dir}")

    # 1. Load contacts
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
        raise ValueError(f"Contact not found: {contact_name}")

    username, display_name = result
    print(f"[wechat-capture] ✅ 找到联系人: {display_name} ({username})")

    # 2. Find message table
    conn, table_name = _find_msg_table(decrypted_dir, username)
    if not conn:
        raise FileNotFoundError(
            f"Message table not found for {display_name}. "
            f"Expected: Msg_{hashlib.md5(username.encode()).hexdigest()}"
        )

    print(f"[wechat-capture] 消息表: {table_name}")

    # 3. Determine self sender_id via Name2Id
    wxid = _get_self_wxid(config_file=config_file, self_wxid=self_wxid)
    self_sid = _get_self_sender_id(conn, wxid) if wxid else None

    if self_sid is not None:
        print(f"[wechat-capture] ✅ 自己的 sender_id: {self_sid} (wxid: {wxid})")
    else:
        print("[wechat-capture] ⚠️ 无法确定自己的 sender_id，将使用启发式判断 (real_sender_id == 0)")

    # 4. Read messages
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
        # Use Name2Id-based detection if available, fall back to heuristic
        is_me = (real_sender_id == self_sid) if self_sid is not None else (real_sender_id == 0)
        messages.append((create_time, is_me, text, msg_type))

    # 5. Generate HTML
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", display_name)
    output_path = os.path.join(output_dir, f"{safe_name}_聊天记录.html")
    render_database_html(display_name, messages, output_path)

    # 6. Compute stats
    from datetime import datetime
    me_count = sum(1 for _, is_me, _, t in messages if is_me and t != "system")
    them_count = sum(1 for _, is_me, _, t in messages if not is_me and t != "system")
    first_date = datetime.fromtimestamp(messages[0][0]).strftime("%Y-%m-%d") if messages else "—"
    last_date = datetime.fromtimestamp(messages[-1][0]).strftime("%Y-%m-%d") if messages else "—"

    stats = {
        "me_count": me_count,
        "them_count": them_count,
        "first_date": first_date,
        "last_date": last_date,
        "total": len(messages),
    }

    file_size = os.path.getsize(output_path) / 1024 / 1024
    print(f"[wechat-capture] ✅ 导出完成: {output_path} ({file_size:.1f} MB, {len(messages)} 条)")

    return {
        "html_path": output_path,
        "contact_name": display_name,
        "username": username,
        "messages": messages,
        "stats": stats,
    }
