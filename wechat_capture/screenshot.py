# -*- coding: utf-8 -*-
"""
wechat_capture.screenshot — Method 1: Screenshot export

Auto-scrolls WeChat chat window page by page and captures screenshots.
Zero intrusion — no database decryption or reverse-engineering needed.
Requires WeChat PC to be open with the target chat visible.
"""
import os
import time

import pyautogui

from .utils import (
    find_wechat_window,
    activate_window,
    get_chat_area,
    get_screen_hash,
    user32,
)
from .html_render import render_screenshot_html


def export(contact_name, output_dir="./output", max_scroll_batches=150):
    """
    Export WeChat chat history via automated screenshots.

    Args:
        contact_name: Contact name (the chat must already be open in WeChat)
        output_dir: Output directory for screenshots and HTML
        max_scroll_batches: Max scroll-up batches to prevent infinite loop

    Returns:
        dict with keys:
            - html_path (str): Path to the generated HTML file
            - contact_name (str): Name of the contact
            - pages (int): Number of screenshots captured
            - screenshot_dir (str): Directory containing the screenshots
    """
    screenshot_dir = os.path.join(output_dir, f"{contact_name}_screenshots")
    output_html = os.path.join(output_dir, f"{contact_name}_聊天记录.html")
    os.makedirs(screenshot_dir, exist_ok=True)

    # Clean old screenshots
    for f in os.listdir(screenshot_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(screenshot_dir, f))

    print(f"[wechat-capture] 截图模式 — {contact_name}")
    print(f"[wechat-capture] 截图目录: {screenshot_dir}")

    # 1. Find and activate WeChat window
    hwnd = find_wechat_window()
    if not hwnd:
        raise RuntimeError("未找到微信窗口，请确保微信 PC 版已打开")

    activate_window(hwnd)

    # Search for contact
    _search_contact(hwnd, contact_name)

    # 2. Calculate chat area
    chat_region, cx, cy = get_chat_area(hwnd)
    print(f"[wechat-capture] 聊天区域: {chat_region}")

    # Ensure chat area has focus
    pyautogui.click(cx, cy)
    time.sleep(0.3)

    # 3. Scroll to top
    print("[wechat-capture] 正在滚动到聊天顶部...")
    pyautogui.click(cx, cy)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "Home")
    time.sleep(1)

    stable_count = 0
    scroll_count = 0
    prev_hash = None

    while stable_count < 3 and scroll_count < max_scroll_batches:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.01)
        pyautogui.click(cx, cy)
        time.sleep(0.01)

        for _ in range(30):
            pyautogui.scroll(20, cx, cy)
            time.sleep(0.005)

        scroll_count += 1
        time.sleep(0.15)

        curr_hash, _ = get_screen_hash(chat_region)
        if curr_hash == prev_hash:
            stable_count += 1
        else:
            stable_count = 0
        prev_hash = curr_hash

        if scroll_count % 20 == 0:
            print(f"  ↑ 已滚动 {scroll_count}/{max_scroll_batches} 批次")

    print(f"[wechat-capture] 到达顶部（{scroll_count} 批次）")
    time.sleep(0.3)

    # 4. Capture screenshots page by page
    print("[wechat-capture] 正在逐页截图...")
    page = 0
    stable_count = 0
    prev_hash = None

    while stable_count < 3:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)

        curr_hash, screenshot = get_screen_hash(chat_region)

        if curr_hash == prev_hash:
            stable_count += 1
        else:
            stable_count = 0
            filepath = os.path.join(screenshot_dir, f"page_{page:04d}.png")
            screenshot.save(filepath)
            if page % 10 == 0:
                print(f"  📸 第 {page} 页")
            page += 1

        prev_hash = curr_hash

        pyautogui.click(cx, cy)
        time.sleep(0.01)
        pyautogui.press("pagedown")
        time.sleep(0.15)

    print(f"[wechat-capture] 截图完成，共 {page} 页")

    # 5. Generate HTML
    print("[wechat-capture] 正在生成 HTML...")
    render_screenshot_html(contact_name, screenshot_dir, output_html)

    file_size = os.path.getsize(output_html) / 1024 / 1024
    print(f"[wechat-capture] ✅ 导出完成: {output_html} ({file_size:.1f} MB, {page} 页)")

    return {
        "html_path": output_html,
        "contact_name": contact_name,
        "pages": page,
        "screenshot_dir": screenshot_dir,
    }


def _search_contact(hwnd, contact_name):
    """Search and open a contact's chat window in WeChat"""
    try:
        import pyperclip
    except ImportError:
        print("[wechat-capture] ⚠️ 未安装 pyperclip，跳过自动搜索。请手动打开聊天窗口。")
        time.sleep(3)
        return

    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    pyperclip.copy(contact_name)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.5)
    pyautogui.press("enter")
    time.sleep(1.5)
