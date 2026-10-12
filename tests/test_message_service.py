"""Kiểm thử tầng nghiệp vụ đọc và tóm tắt tin nhắn (MessageService)."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.ai.summarizer import MessageSummarizer
from app.services.message_service import MessageService
from app.telegram_client.client import ChatDialogData, ChatMessage


@pytest.fixture
def mock_telethon():
    return MagicMock()


@pytest.fixture
def mock_summarizer():
    summarizer = MagicMock(spec=MessageSummarizer)
    summarizer.summarize_chats = AsyncMock(return_value="Tóm tắt AI thành công.")
    return summarizer


@pytest.mark.asyncio
async def test_summarize_unread_no_messages(sample_config, mock_telethon, mock_summarizer):
    """Trường hợp không có tin nhắn chưa đọc."""
    mock_telethon.get_unread_chats = AsyncMock(return_value=[])

    service = MessageService(sample_config, mock_telethon, mock_summarizer)
    result = await service.summarize_unread()

    assert "không có tin nhắn chưa đọc" in result.lower()
    mock_summarizer.summarize_chats.assert_not_awaited()


@pytest.mark.asyncio
async def test_summarize_unread_with_messages(sample_config, mock_telethon, mock_summarizer):
    """Trường hợp có tin nhắn chưa đọc và gửi cho AI tóm tắt."""
    now = datetime.now(timezone.utc)
    mock_chats = [
        ChatDialogData(
            chat_id=1,
            chat_title="Nhóm Dự Án",
            chat_type="group",
            unread_count=2,
            messages=[
                ChatMessage(1, "An", "Cần nộp báo cáo trước 17h", now),
                ChatMessage(2, "Bình", "OK mình đang làm", now),
            ],
        )
    ]
    mock_telethon.get_unread_chats = AsyncMock(return_value=mock_chats)

    service = MessageService(sample_config, mock_telethon, mock_summarizer)
    result = await service.summarize_unread()

    assert result == "Tóm tắt AI thành công."
    mock_summarizer.summarize_chats.assert_awaited_once()


@pytest.mark.asyncio
async def test_summarize_24h(sample_config, mock_telethon, mock_summarizer):
    """Trường hợp tóm tắt tin nhắn trong 24h gần nhất."""
    mock_telethon.get_recent_messages_chats = AsyncMock(return_value=[])

    service = MessageService(sample_config, mock_telethon, mock_summarizer)
    result = await service.summarize_24h()

    assert "trong vòng 24 giờ qua" in result
    mock_telethon.get_recent_messages_chats.assert_awaited_once()

    # Kiểm tra since_datetime được truyền vào là khoảng 24h trước
    call_args = mock_telethon.get_recent_messages_chats.call_args[1]
    since = call_args["since_datetime"]
    assert datetime.now(timezone.utc) - since < timedelta(hours=24, minutes=1)


@pytest.mark.asyncio
async def test_summarize_specific_chat(sample_config, mock_telethon, mock_summarizer):
    """Trường hợp tóm tắt một cuộc trò chuyện cụ thể."""
    now = datetime.now(timezone.utc)
    mock_chat = ChatDialogData(
        chat_id=2,
        chat_title="Nguyễn Văn A",
        chat_type="private",
        unread_count=1,
        messages=[ChatMessage(10, "Nguyễn Văn A", "Tối nay họp nhé", now)],
    )
    mock_telethon.get_specific_chat_messages = AsyncMock(return_value=mock_chat)

    service = MessageService(sample_config, mock_telethon, mock_summarizer)
    result = await service.summarize_specific_chat("Nguyễn Văn A", limit=20)

    assert result == "Tóm tắt AI thành công."
    mock_telethon.get_specific_chat_messages.assert_awaited_once_with(
        chat_identifier="Nguyễn Văn A",
        limit=20,
        unread_only=False,
    )


@pytest.mark.asyncio
async def test_summarize_cancelled(sample_config, mock_telethon, mock_summarizer):
    """Kiểm tra xử lý hủy tác vụ (asyncio.CancelledError)."""
    mock_telethon.get_unread_chats = AsyncMock(side_effect=asyncio.CancelledError())

    service = MessageService(sample_config, mock_telethon, mock_summarizer)
    with pytest.raises(asyncio.CancelledError):
        await service.summarize_unread()
