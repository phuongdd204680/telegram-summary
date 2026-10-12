"""Kiểm thử tải và kiểm tra hợp lệ cấu hình ứng dụng."""

import pytest
from app.config import ConfigError, load_config


def test_load_config_success(monkeypatch):
    """Kiểm tra đọc đầy đủ cấu hình hợp lệ."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot_token_123")
    monkeypatch.setenv("TELEGRAM_API_ID", "112233")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash_abc")
    monkeypatch.setenv("ALLOWED_TELEGRAM_USER_ID", "999888")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_SITE_URL", "https://mysite.com")
    monkeypatch.setenv("OPENROUTER_APP_NAME", "My Bot")
    monkeypatch.setenv("OPENROUTER_TIMEOUT", "45")

    cfg = load_config(load_env_file=False)
    assert cfg.telegram_bot_token == "bot_token_123"
    assert cfg.telegram_api_id == 112233
    assert cfg.telegram_api_hash == "hash_abc"
    assert cfg.allowed_telegram_user_id == 999888
    assert cfg.openrouter_api_key == "sk-or-test"
    assert cfg.openrouter_model == "meta-llama/llama-3.3-70b-instruct:free"
    assert cfg.openrouter_site_url == "https://mysite.com"
    assert cfg.openrouter_app_name == "My Bot"
    assert cfg.openrouter_timeout == 45.0
    assert cfg.openrouter_chat_endpoint == "https://openrouter.ai/api/v1/chat/completions"


@pytest.mark.parametrize(
    "missing_var",
    [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "OPENROUTER_API_KEY",
    ],
)
def test_load_config_missing_required(monkeypatch, missing_var):
    """Kiểm tra báo lỗi khi thiếu các biến bắt buộc."""
    base_env = {
        "TELEGRAM_BOT_TOKEN": "bot_token_123",
        "TELEGRAM_API_ID": "112233",
        "TELEGRAM_API_HASH": "hash_abc",
        "OPENROUTER_API_KEY": "sk-or-test",
    }
    del base_env[missing_var]

    for k, v in base_env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv(missing_var, raising=False)

    with pytest.raises(ConfigError) as exc_info:
        load_config(load_env_file=False)
    assert missing_var in str(exc_info.value)


def test_invalid_api_id_raises_error(monkeypatch):
    """Kiểm tra TELEGRAM_API_ID không phải số nguyên."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_API_ID", "not_an_int")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")

    with pytest.raises(ConfigError) as exc_info:
        load_config(load_env_file=False)
    assert "số nguyên" in str(exc_info.value).lower()


def test_invalid_allowed_user_id_raises_error(monkeypatch):
    """Kiểm tra ALLOWED_TELEGRAM_USER_ID không phải số nguyên."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("ALLOWED_TELEGRAM_USER_ID", "abc")

    with pytest.raises(ConfigError) as exc_info:
        load_config(load_env_file=False)
    assert "ALLOWED_TELEGRAM_USER_ID" in str(exc_info.value)


def test_endpoint_no_double_path(sample_config):
    """Kiểm tra không bị lặp /chat/completions/chat/completions khi cấu hình URL."""
    assert sample_config.openrouter_chat_endpoint == "https://openrouter.ai/api/v1/chat/completions"

    # Nếu người dùng nhập thẳng URL có /chat/completions
    cfg_with_full_url = ConfigError
    from dataclasses import replace
    cfg2 = replace(sample_config, openrouter_base_url="https://openrouter.ai/api/v1/chat/completions")
    assert cfg2.openrouter_chat_endpoint == "https://openrouter.ai/api/v1/chat/completions"


def test_is_user_allowed(sample_config):
    """Kiểm tra hàm kiểm tra quyền truy cập."""
    assert sample_config.is_user_allowed(999888777) is True
    assert sample_config.is_user_allowed(111222333) is False
    assert sample_config.is_user_allowed(None) is False
