"""Script CLI đăng nhập Telethon lần đầu độc lập trên Terminal/PowerShell.

Script này cho phép bạn đăng nhập an toàn vào tài khoản Telegram cá nhân,
nhập Số điện thoại, Mã OTP và Mật khẩu 2FA (nếu có) trực tiếp trên terminal.
Sau khi đăng nhập thành công, file session sẽ được lưu và bot chính có thể sử dụng.
"""

import asyncio
import sys
from telethon import TelegramClient
from app.config import load_config, ConfigError


async def main() -> None:
    print("=" * 60)
    print("  KHỞI TẠO ĐĂNG NHẬP TELETHON (TÀI KHOẢN CÁ NHÂN)")
    print("=" * 60)

    try:
        config = load_config()
    except ConfigError as e:
        print(f"\n[LỖI CẤU HÌNH] {e}")
        print("Vui lòng kiểm tra file .env trước khi chạy lại.")
        sys.exit(1)

    print(f"\nĐang kết nối Telethon với App ID: {config.telegram_api_id}...")
    print(f"Tên session: {config.telegram_session_name}.session")

    client = TelegramClient(
        config.telegram_session_name,
        config.telegram_api_id,
        config.telegram_api_hash,
    )

    try:
        await client.start()
        me = await client.get_me()

        print("\n" + "=" * 60)
        print(" [THÀNH CÔNG] Bạn đã đăng nhập Telethon thành công!")
        print("=" * 60)
        print(f"Họ tên:        {getattr(me, 'first_name', '')} {getattr(me, 'last_name', '')}".strip())
        print(f"Username:      @{getattr(me, 'username', 'Không có')}")
        print(f"User ID của bạn: {me.id}")
        print("-" * 60)
        print(f"-> HÃY SAO CHÉP USER ID TRÊN VÀO BIẾN `ALLOWED_TELEGRAM_USER_ID={me.id}` TRONG FILE .env")
        print("-> Giờ bạn có thể chạy bot chính bằng lệnh: python -m app.main")
        print("=" * 60 + "\n")

    except Exception as err:
        print(f"\n[LỖI ĐĂNG NHẬP] Không thể đăng nhập Telethon: {err}")
        sys.exit(1)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
