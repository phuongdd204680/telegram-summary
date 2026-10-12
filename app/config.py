"""Quản lý cấu hình ứng dụng từ biến môi trường (.env)."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Đối tượng cấu hình bất biến cho ứng dụng."""

    # Telegram Bot
    telegram_bot_token: str

    # Telethon (Tài khoản cá nhân)
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session_name: str

    # Quyền truy cập
    allowed_telegram_user_id: Optional[int]

    # OpenRouter API
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str
    openrouter_site_url: Optional[str]
    openrouter_app_name: Optional[str]
    openrouter_timeout: float

    # Giới hạn xử lý tin nhắn
    max_chats_to_scan: int = 10
    max_messages_per_chat: int = 30
    total_max_messages: int = 150

    @property
    def openrouter_chat_endpoint(self) -> str:
        """Sinh ra URL endpoint /chat/completions chính xác từ base URL.

        Tránh trùng lặp /chat/completions nếu người dùng đã vô tình nhập đầy đủ URL.
        """
        base = self.openrouter_base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def is_user_allowed(self, user_id: Optional[int]) -> bool:
        """Kiểm tra Telegram user_id có được cấp quyền hay không."""
        if self.allowed_telegram_user_id is None or user_id is None:
            return False
        return user_id == self.allowed_telegram_user_id


class ConfigError(ValueError):
    """Lỗi cấu hình khi thiếu hoặc sai định dạng biến môi trường."""
    pass


def load_config(env_path: Optional[str] = None, load_env_file: bool = True) -> Config:
    """Đọc và xác thực cấu hình từ biến môi trường hoặc file .env."""
    if load_env_file:
        if env_path:
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()

    # Kiểm tra các biến bắt buộc
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip("\"'")
    if not bot_token:
        raise ConfigError("Thiếu biến môi trường bắt buộc: TELEGRAM_BOT_TOKEN")

    api_id_str = os.getenv("TELEGRAM_API_ID", "").strip().strip("\"'")
    if not api_id_str:
        raise ConfigError("Thiếu biến môi trường bắt buộc: TELEGRAM_API_ID")
    try:
        telegram_api_id = int(api_id_str)
    except ValueError:
        raise ConfigError("TELEGRAM_API_ID phải là một số nguyên hợp lệ")

    telegram_api_hash = os.getenv("TELEGRAM_API_HASH", "").strip().strip("\"'")
    if not telegram_api_hash:
        raise ConfigError("Thiếu biến môi trường bắt buộc: TELEGRAM_API_HASH")

    session_name = os.getenv("TELEGRAM_SESSION_NAME", "telegram_user_session").strip().strip("\"'") or "telegram_user_session"

    # ALLOWED_TELEGRAM_USER_ID
    allowed_id_str = os.getenv("ALLOWED_TELEGRAM_USER_ID", "").strip().strip("\"'")
    allowed_user_id: Optional[int] = None
    if allowed_id_str:
        try:
            allowed_user_id = int(allowed_id_str)
        except ValueError:
            raise ConfigError("ALLOWED_TELEGRAM_USER_ID phải là một số nguyên")

    # OpenRouter
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "").strip().strip("\"'")
    if not openrouter_api_key:
        raise ConfigError("Thiếu biến môi trường bắt buộc: OPENROUTER_API_KEY")

    openrouter_model = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip().strip("\"'")
    if not openrouter_model:
        openrouter_model = "openrouter/free"

    openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    if not openrouter_base_url:
        openrouter_base_url = "https://openrouter.ai/api/v1"

    site_url = os.getenv("OPENROUTER_SITE_URL", "").strip() or None
    app_name = os.getenv("OPENROUTER_APP_NAME", "Telegram Message Summarizer").strip() or None

    timeout_str = os.getenv("OPENROUTER_TIMEOUT", "60").strip()
    try:
        timeout = float(timeout_str)
    except ValueError:
        timeout = 60.0

    # Limits
    def _parse_int_limit(env_name: str, default: int) -> int:
        val = os.getenv(env_name, str(default)).strip()
        try:
            parsed = int(val)
            return parsed if parsed > 0 else default
        except ValueError:
            return default

    max_chats = _parse_int_limit("MAX_CHATS_TO_SCAN", 10)
    max_msgs = _parse_int_limit("MAX_MESSAGES_PER_CHAT", 30)
    total_max = _parse_int_limit("TOTAL_MAX_MESSAGES", 150)

    return Config(
        telegram_bot_token=bot_token,
        telegram_api_id=telegram_api_id,
        telegram_api_hash=telegram_api_hash,
        telegram_session_name=session_name,
        allowed_telegram_user_id=allowed_user_id,
        openrouter_api_key=openrouter_api_key,
        openrouter_model=openrouter_model,
        openrouter_base_url=openrouter_base_url,
        openrouter_site_url=site_url,
        openrouter_app_name=app_name,
        openrouter_timeout=timeout,
        max_chats_to_scan=max_chats,
        max_messages_per_chat=max_msgs,
        total_max_messages=total_max,
    )
