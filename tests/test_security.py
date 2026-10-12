"""Kiểm thử bảo mật: không lộ thông tin vào log và không phụ thuộc database."""

import importlib
import logging
import os
import sys
from unittest.mock import AsyncMock, patch
import pytest
from app.ai.summarizer import MessageSummarizer
from app.telegram_client.client import ChatDialogData, ChatMessage
from datetime import datetime, timezone


def test_no_database_modules_in_app():
    """Kiểm tra mã nguồn không import hoặc sử dụng bất kỳ thư viện database nào."""
    forbidden_db_keywords = [
        "sqlite3",
        "sqlalchemy",
        "databases",
        "psycopg2",
        "asyncpg",
        "mysql",
        "redis",
        "pymongo",
        "motor",
        "tortoise",
        "peewee",
    ]

    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))

    for root, _, files in os.walk(app_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for keyword in forbidden_db_keywords:
                        assert f"import {keyword}" not in content, (
                            f"Phát hiện import database trái phép '{keyword}' trong file {file}"
                        )
                        assert f"from {keyword}" not in content, (
                            f"Phát hiện import database trái phép '{keyword}' trong file {file}"
                        )


@pytest.mark.asyncio
async def test_logs_do_not_contain_private_message_content(caplog):
    """Kiểm tra nội dung tin nhắn riêng tư không bao giờ bị ghi vào log."""
    caplog.set_level(logging.DEBUG)

    private_secret_text = "CONFIDENTIAL_PAYROLL_DATA_XYZ987"
    user_name = "Giám Đốc Tài Chính"

    now = datetime.now(timezone.utc)
    chat_data = [
        ChatDialogData(
            chat_id=123,
            chat_title="Phòng Kế Toán",
            chat_type="group",
            unread_count=1,
            messages=[ChatMessage(1, user_name, private_secret_text, now)],
        )
    ]

    mock_ai_client = AsyncMock()
    mock_ai_client.complete_chat.return_value = "Bản tóm tắt an toàn."

    summarizer = MessageSummarizer(ai_client=mock_ai_client)
    await summarizer.summarize_chats(chat_data)

    # Toàn bộ text trong caplog không được chứa nội dung tin nhắn nhạy cảm
    full_log_text = caplog.text
    assert private_secret_text not in full_log_text
