"""Kiểm thử kiểm soát quyền truy cập Telegram bot."""

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.bot.handlers import require_auth
from app.config import Config


@pytest.mark.asyncio
async def test_require_auth_allowed(sample_config):
    """Người dùng hợp lệ được phép thực thi handler."""
    dummy_handler = AsyncMock(return_value="OK")
    wrapped = require_auth(dummy_handler)

    update = MagicMock()
    update.effective_user.id = sample_config.allowed_telegram_user_id

    context = MagicMock()
    context.bot_data = {"config": sample_config}

    result = await wrapped(update, context)
    assert result == "OK"
    dummy_handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_require_auth_denied(sample_config):
    """Người dùng không hợp lệ bị từ chối và nhận thông báo tiếng Việt."""
    dummy_handler = AsyncMock()
    wrapped = require_auth(dummy_handler)

    update = MagicMock()
    update.effective_user.id = 12345  # Không phải ID được cấp phép
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot_data = {"config": sample_config}

    await wrapped(update, context)
    dummy_handler.assert_not_awaited()
    update.effective_message.reply_text.assert_awaited_once()
    sent_text = update.effective_message.reply_text.call_args[0][0]
    assert "không có quyền" in sent_text.lower()


@pytest.mark.asyncio
async def test_require_auth_no_allowed_id_configured(sample_config):
    """Nếu ALLOWED_TELEGRAM_USER_ID là None, từ chối mọi yêu cầu."""
    config_no_auth = replace(sample_config, allowed_telegram_user_id=None)

    dummy_handler = AsyncMock()
    wrapped = require_auth(dummy_handler)

    update = MagicMock()
    update.effective_user.id = 999888777
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot_data = {"config": config_no_auth}

    await wrapped(update, context)
    dummy_handler.assert_not_awaited()
    update.effective_message.reply_text.assert_awaited_once()
