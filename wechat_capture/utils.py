# -*- coding: utf-8 -*-
"""
wechat_capture.utils — 公共工具函数
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import time

import numpy as np
import pyautogui

user32 = ctypes.windll.user32
pyautogui.PAUSE = 0.01
pyautogui.FAILSAFE = False


def find_wechat_window():
    """查找微信主窗口句柄"""
    for cls in ["WeChatMainWndForPC", "Qt51514QWindowIcon", None]:
        hwnd = user32.FindWindowW(cls, "微信")
        if hwnd:
            return hwnd
    return None


def activate_window(hwnd, x=50, y=50, width=1400, height=1000):
    """激活并定位微信窗口"""
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.MoveWindow(hwnd, x, y, width, height, True)
    time.sleep(0.3)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)


def get_window_rect(hwnd):
    """获取窗口位置和尺寸，返回 (left, top, right, bottom)"""
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def get_screen_hash(region):
    """截取指定区域并返回 (hash, PIL.Image)"""
    img = pyautogui.screenshot(region=region)
    small = img.resize((80, 80))
    arr = np.array(small)
    return hashlib.md5(arr.tobytes()).hexdigest(), img


def detect_input_box_top(left, right, bottom, scan_depth=300):
    """
    自动检测微信输入框上边界。
    从窗口底部向上扫描像素颜色：输入框是浅色（RGB>230），聊天区较深。
    返回输入框上边界的 y 坐标，检测失败返回 None。
    """
    cx = (left + right) // 2
    scan_width = 200
    scan_left = cx - scan_width // 2
    top_limit = bottom - scan_depth
    scan_region = (scan_left, top_limit, scan_width, scan_depth)
    img = pyautogui.screenshot(region=scan_region)
    arr = np.array(img)

    h = arr.shape[0]
    for y in range(h - 1, max(h - 300, 0), -1):
        row_mean = arr[y, :, :3].mean()
        if row_mean < 200:  # 找到非浅色区域 = 聊天消息区
            input_box_height = h - y
            return bottom - input_box_height
    return None


def get_chat_area(hwnd, fallback_bottom_offset=170):
    """
    计算聊天消息区域（排除侧边栏、标题栏、输入框）。
    返回 (chat_region, center_x, center_y)
    其中 chat_region = (left, top, width, height)
    """
    left, top, right, bottom = get_window_rect(hwnd)

    chat_left = left + 410    # 左侧边栏宽度
    chat_top = top + 70       # 顶部标题栏
    chat_right = right - 10   # 右侧边距

    # 自动检测输入框上边界
    detected = detect_input_box_top(chat_left, chat_right, bottom)
    if detected and (bottom - detected) > 50:
        chat_bottom = detected - 5  # 5px 安全边距
    else:
        chat_bottom = bottom - fallback_bottom_offset

    chat_width = chat_right - chat_left
    chat_height = chat_bottom - chat_top
    cx = (chat_left + chat_right) // 2
    cy = (chat_top + chat_bottom) // 2

    return (chat_left, chat_top, chat_width, chat_height), cx, cy
