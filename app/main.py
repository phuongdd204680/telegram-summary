"""Entrypoint chính khởi chạy Telegram Bot tóm tắt tin nhắn."""

import asyncio
import logging
import signal
import sys
from telegram import BotCommand
from telegram.ext import Application, CommandHandler
from app.ai.openrouter_client import OpenRouterClient
from app.ai.summarizer import MessageSummarizer
from app.bot.handlers import (
    cancel_command,
    grant_command,
    help_command,
    model_command,
    revoke_command,
    start_command,
    status_command,
    summary_command,
    users_command,
)
from app.config import ConfigError, load_config
from app.services.message_service import MessageService
from app.telegram_client.client import TelethonService

# Cấu hình logging chuẩn (không in dữ liệu tin nhắn hoặc token)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# Giảm mức log ồn ào từ các thư viện bên thứ ba
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger("telegram_summarizer")


async def run_bot() -> None:
    """Khởi tạo và chạy bot cùng các dịch vụ liên kết."""
    print("=" * 60)
    print("  KHỞI ĐỘNG TELEGRAM MESSAGE SUMMARIZER BOT")
    print("=" * 60)

    try:
        config = load_config()
    except ConfigError as err:
        logger.error("LỖI CẤU HÌNH: %s", err)
        print(f"\n[LỖI CẤU HÌNH] {err}")
        print("Vui lòng kiểm tra lại file .env. Xem hướng dẫn tại docs/INSTALLATION.md\n")
        sys.exit(1)

    if config.allowed_telegram_user_id is None:
        logger.warning(
            "CẢNH BÁO BẢO MẬT: Chưa cấu hình ALLOWED_TELEGRAM_USER_ID. "
            "Bot sẽ từ chối mọi yêu cầu đọc dữ liệu nhạy cảm."
        )

    # Khởi tạo các dịch vụ
    telethon_service = TelethonService(
        session_name=config.telegram_session_name,
        api_id=config.telegram_api_id,
        api_hash=config.telegram_api_hash,
    )

    openrouter_client = OpenRouterClient(
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
        endpoint=config.openrouter_chat_endpoint,
        site_url=config.openrouter_site_url,
        app_name=config.openrouter_app_name,
        timeout=config.openrouter_timeout,
    )

    summarizer = MessageSummarizer(ai_client=openrouter_client)
    message_service = MessageService(
        config=config,
        telethon_service=telethon_service,
        summarizer=summarizer,
    )

    # Kết nối Telethon
    logger.info("Đang kiểm tra kết nối tài khoản Telegram qua Telethon...")
    telethon_ready = await telethon_service.start()
    if not telethon_ready:
        logger.warning(
            "CHƯA ĐĂNG NHẬP TELETHON: Tài khoản Telegram chưa được xác thực.\n"
            "-> Vui lòng chạy lệnh: python -m app.login để đăng nhập tài khoản một lần trước khi dùng bot."
        )

    # Khởi tạo python-telegram-bot
    application = Application.builder().token(config.telegram_bot_token).build()

    # Lưu trữ dependency vào bot_data
    application.bot_data["config"] = config
    application.bot_data["telethon"] = telethon_service
    application.bot_data["message_service"] = message_service

    # Đăng ký các command handler
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CommandHandler("revoke", revoke_command))
    application.add_handler(CommandHandler("users", users_command))

    # Khởi tạo và chạy bot polling
    try:
        await application.initialize()

        # Đăng ký menu gợi ý lệnh khi người dùng gõ "/" trong Telegram
        try:
            bot_commands = [
                BotCommand("summary", "Tóm tắt tin nhắn chưa đọc hoặc nhóm"),
                BotCommand("model", "Xem hoặc đổi model AI (Admin)"),
                BotCommand("status", "Kiểm tra trạng thái kết nối bot (Admin)"),
                BotCommand("users", "Danh sách người dùng được cấp quyền (Admin)"),
                BotCommand("grant", "Cấp quyền xem nhóm: /grant <id> <nhóm> (Admin)"),
                BotCommand("revoke", "Thu hồi quyền xem nhóm: /revoke <id> (Admin)"),
                BotCommand("cancel", "Hủy tác vụ tóm tắt đang chạy"),
                BotCommand("help", "Xem hướng dẫn chi tiết"),
                BotCommand("start", "Khởi động và giới thiệu bot"),
            ]
            await application.bot.set_my_commands(bot_commands)
            logger.info("Đã đăng ký gợi ý lệnh (menu /) thành công với Telegram.")
        except Exception as cmd_err:
            logger.warning("Không thể đăng ký gợi ý lệnh với Telegram: %s", cmd_err)

        await application.start()
        await application.updater.start_polling()

        logger.info("Telegram Bot đã sẵn sàng nhận lệnh. Đang bắt đầu polling...")

        # Giữ vòng lặp chạy cho đến khi nhận tín hiệu dừng
        stop_event = asyncio.Event()

        # Đăng ký bắt tín hiệu ngắt (SIGINT, SIGTERM)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except (NotImplementedError, AttributeError):
                pass

        try:
            while not stop_event.is_set():
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass

    finally:
        logger.info("Đang dừng Telegram Bot và giải phóng tài nguyên...")
        try:
            if application.updater and application.updater.running:
                await application.updater.stop()
        except Exception as e:
            logger.debug("Lỗi khi dừng updater: %s", e)

        try:
            if application.running:
                await application.stop()
        except Exception as e:
            logger.debug("Lỗi khi dừng application: %s", e)

        try:
            await application.shutdown()
        except Exception as e:
            logger.debug("Lỗi khi shutdown: %s", e)

        await telethon_service.disconnect()
        await openrouter_client.close()
        logger.info("Đã tắt ứng dụng an toàn.")


def main() -> None:
    """Hàm main đồng bộ."""
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("\nBot đã dừng hoạt động.")


if __name__ == "__main__":
    main()
