"""Kiểm thử các lệnh bot và tính năng hủy tác vụ."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.bot.handlers import (
    _active_summary_tasks,
    cancel_command,
    help_command,
    markdown_to_telegram_html,
    model_command,
    send_split_message,
    start_command,
    status_command,
    summary_command,
)


@pytest.fixture
def mock_bot_update(sample_config):
    update = MagicMock()
    update.effective_user.id = sample_config.allowed_telegram_user_id
    update.effective_message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_bot_context(sample_config):
    context = MagicMock()
    mock_telethon = MagicMock()
    mock_telethon.is_connected = AsyncMock(return_value=True)

    mock_msg_service = MagicMock()
    mock_msg_service.summarizer = MagicMock()
    mock_msg_service.summarizer.ai_client = MagicMock()
    mock_msg_service.summarizer.ai_client.model = sample_config.openrouter_model
    mock_msg_service.summarize_unread = AsyncMock(return_value="Nội dung tóm tắt mẫu")
    mock_msg_service.summarize_24h = AsyncMock(return_value="Nội dung tóm tắt 24h")
    mock_msg_service.summarize_specific_chat = AsyncMock(return_value="Nội dung chat cụ thể")

    context.bot_data = {
        "config": sample_config,
        "telethon": mock_telethon,
        "message_service": mock_msg_service,
    }
    context.args = []
    return context


@pytest.mark.asyncio
async def test_start_command(mock_bot_update, mock_bot_context):
    """Kiểm tra lệnh /start."""
    await start_command(mock_bot_update, mock_bot_context)
    mock_bot_update.effective_message.reply_text.assert_awaited_once()
    text = mock_bot_update.effective_message.reply_text.call_args[0][0]
    assert "/summary" in text
    assert "/status" in text


@pytest.mark.asyncio
async def test_help_command(mock_bot_update, mock_bot_context):
    """Kiểm tra lệnh /help."""
    await help_command(mock_bot_update, mock_bot_context)
    mock_bot_update.effective_message.reply_text.assert_awaited_once()
    text = mock_bot_update.effective_message.reply_text.call_args[0][0]
    assert "HƯỚNG DẪN SỬ DỤNG" in text


@pytest.mark.asyncio
async def test_status_command(mock_bot_update, mock_bot_context, sample_config):
    """Kiểm tra lệnh /status hiển thị thông tin an toàn."""
    await status_command(mock_bot_update, mock_bot_context)
    mock_bot_update.effective_message.reply_text.assert_awaited_once()
    text = mock_bot_update.effective_message.reply_text.call_args[0][0]

    assert "TRẠNG THÁI HỆ THỐNG" in text
    assert sample_config.openrouter_model in text
    # Không lộ secrets
    assert sample_config.openrouter_api_key not in text
    assert sample_config.telegram_api_hash not in text


@pytest.mark.asyncio
async def test_model_command_view(mock_bot_update, mock_bot_context, sample_config):
    """Kiểm tra lệnh /model xem model hiện tại."""
    mock_bot_context.args = []
    await model_command(mock_bot_update, mock_bot_context)
    mock_bot_update.effective_message.reply_text.assert_awaited_once()
    text = mock_bot_update.effective_message.reply_text.call_args[0][0]
    assert "MODEL AI HIỆN TẠI" in text
    assert sample_config.openrouter_model in text


@pytest.mark.asyncio
async def test_model_command_switch(mock_bot_update, mock_bot_context):
    """Kiểm tra lệnh /model đổi sang model khác."""
    mock_bot_context.args = ["google/gemini-2.0-flash-exp:free"]
    await model_command(mock_bot_update, mock_bot_context)
    mock_bot_update.effective_message.reply_text.assert_awaited_once()
    text = mock_bot_update.effective_message.reply_text.call_args[0][0]
    assert "Đã chuyển model AI sang: google/gemini-2.0-flash-exp:free" in text
    ai_client = mock_bot_context.bot_data["message_service"].summarizer.ai_client
    assert ai_client.model == "google/gemini-2.0-flash-exp:free"


@pytest.mark.asyncio
async def test_cancel_when_no_task_running(mock_bot_update, mock_bot_context):
    """Kiểm tra /cancel khi không có tác vụ nào đang chạy."""
    _active_summary_tasks.clear()
    await cancel_command(mock_bot_update, mock_bot_context)
    text = mock_bot_update.effective_message.reply_text.call_args[0][0]
    assert "không có tác vụ" in text.lower()


@pytest.mark.asyncio
async def test_cancel_active_task(mock_bot_update, mock_bot_context, sample_config):
    """Kiểm tra /cancel khi có tác vụ đang chạy."""
    user_id = sample_config.allowed_telegram_user_id

    async def long_running():
        await asyncio.sleep(10)

    task = asyncio.create_task(long_running())
    _active_summary_tasks[user_id] = task

    try:
        await cancel_command(mock_bot_update, mock_bot_context)
        assert task.cancelling() or task.cancelled()
    finally:
        task.cancel()
        _active_summary_tasks.clear()


@pytest.mark.asyncio
async def test_send_split_message():
    """Kiểm tra hàm chia nhỏ tin nhắn khi vượt quá 4000 ký tự."""
    update = MagicMock()
    update.effective_message.reply_text = AsyncMock()

    # Đoạn văn 5000 ký tự
    long_text = ("Đoạn văn ngắn mẫu.\n\n" * 250)
    await send_split_message(update, long_text)

    # Phải gọi reply_text ít nhất 2 lần
    assert update.effective_message.reply_text.await_count >= 2


def test_markdown_to_telegram_html():
    """Kiểm tra chuyển đổi Markdown sang HTML hợp lệ cho Telegram."""
    sample_md = "**Tóm tắt chung**\n- Chi phí **10 triệu**\n- Mã: `ABC123`\n- Link: [Xem](https://test.com)"
    html_out = markdown_to_telegram_html(sample_md)

    assert "<b>Tóm tắt chung</b>" in html_out
    assert "<b>10 triệu</b>" in html_out
    assert "<code>ABC123</code>" in html_out
    assert '<a href="https://test.com">Xem</a>' in html_out
