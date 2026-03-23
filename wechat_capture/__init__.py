# -*- coding: utf-8 -*-
"""
wechat-capture — Export WeChat chat history with zero reverse-engineering.

Two modes:
  - screenshot: Auto-scroll and capture the WeChat window (zero intrusion)
  - database: Read from decrypted local databases (fast and structured)

Usage as a library:
    from wechat_capture import screenshot_export, database_export

    # Screenshot mode
    result = screenshot_export("联系人名")

    # Database mode
    result = database_export("联系人名", decrypted_dir="/path/to/decrypted")
"""

__version__ = "0.2.0"

from .screenshot import export as screenshot_export
from .database import export as database_export

__all__ = ["screenshot_export", "database_export"]
