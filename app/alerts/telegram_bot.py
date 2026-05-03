from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    def send(self, message: str) -> bool:
        if not self.token or not self.chat_id:
            print(message)
            return False
        payload = urllib.parse.urlencode({"chat_id": self.chat_id, "text": message}).encode()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        request = urllib.request.Request(url, data=payload, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        return bool(data.get("ok"))

