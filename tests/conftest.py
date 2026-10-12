"""Fixtures chung cho test suite."""

import pytest
from app.config import Config


@pytest.fixture
def sample_config() -> Config:
    """Trả về đối tượng Config mẫu phục vụ kiểm thử."""
    return Config(
        telegram_bot_token="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
        telegram_api_id=1234567,
        telegram_api_hash="abcdef0123456789abcdef0123456789",
        telegram_session_name="test_session",
        allowed_telegram_user_id=999888777,
        openrouter_api_key="sk-or-v1-testkey1234567890",
        openrouter_model="meta-llama/llama-3.3-70b-instruct:free",
        openrouter_base_url="https://openrouter.ai/api/v1",
        openrouter_site_url="https://example.com",
        openrouter_app_name="Test App",
        openrouter_timeout=30.0,
        max_chats_to_scan=5,
        max_messages_per_chat=10,
        total_max_messages=50,
    )
