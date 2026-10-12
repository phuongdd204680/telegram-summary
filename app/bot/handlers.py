"""Các hàm xử lý lệnh Telegram Bot bằng python-telegram-bot."""

import asyncio
import functools
import html
import logging
import re
from typing import Dict, Optional
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.ai.openrouter_client import (
    OpenRouterAuthError,
    OpenRouterError,
    OpenRouterModelNotFoundError,
    OpenRouterQuotaError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
)
from app.config import Config
from app.permissions import PermissionManager
from app.services.message_service import MessageService
from app.telegram_client.client import TelethonService

logger = logging.getLogger(__name__)

# Quản lý các task tóm tắt đang chạy theo user_id: {user_id: asyncio.Task}
_active_summary_tasks: Dict[int, asyncio.Task] = {}


def markdown_to_telegram_html(text: str) -> str:
    """Chuyển đổi Markdown chuẩn của LLM sang HTML hợp lệ tương thích với Telegram Bot API."""
    if not text:
        return ""

    # 1. Escape các ký tự HTML (&, <, >)
    escaped = html.escape(text)

    # 2. Xử lý code blocks ```...```
    def replace_code_block(match):
        code_content = match.group(1).strip()
        return f"<pre><code>{code_content}</code></pre>"

    escaped = re.sub(r'```(?:[a-zA-Z0-9_]+)?\n?(.*?)```', replace_code_block, escaped, flags=re.DOTALL)

    # 3. Xử lý inline code `...`
    escaped = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', escaped)

    # 4. Xử lý tiêu đề ### Heading -> <b>Heading</b>
    escaped = re.sub(r'^(?:#{1,6})\s+(.+?)$', r'<b>\1</b>', escaped, flags=re.MULTILINE)

    # 5. Xử lý in đậm **text** hoặc __text__ -> <b>text</b>
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped, flags=re.DOTALL)
    escaped = re.sub(r'__(.+?)__', r'<b>\1</b>', escaped, flags=re.DOTALL)

    # 6. Xử lý in nghiêng *text* hoặc _text_ -> <i>text</i>
    escaped = re.sub(r'(?<!\w)\*([^*\n]+?)\*(?!\w)', r'<i>\1</i>', escaped)
    escaped = re.sub(r'(?<!\w)_([^_\n]+?)_(?!\w)', r'<i>\1</i>', escaped)

    # 7. Xử lý gạch ngang ~~text~~ -> <s>text</s>
    escaped = re.sub(r'~~(.+?)~~', r'<s>\1</s>', escaped)

    # 8. Xử lý link [title](url) -> <a href="url">title</a>
    escaped = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<a href="\2">\1</a>', escaped)

    return escaped


def get_perm_manager(context: ContextTypes.DEFAULT_TYPE) -> PermissionManager:
    """Lấy hoặc khởi tạo PermissionManager từ bot_data."""
    if "permission_manager" not in context.bot_data:
        context.bot_data["permission_manager"] = PermissionManager()
    return context.bot_data["permission_manager"]


def require_auth(func):
    """Decorator kiểm tra quyền hạn của người dùng gửi lệnh (Admin hoặc Restricted User)."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        user_id = user.id if user else None
        config: Config = context.bot_data["config"]
        perm_mgr = get_perm_manager(context)

        if not perm_mgr.is_user_allowed(user_id, config.allowed_telegram_user_id):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Xin lỗi, bạn không có quyền sử dụng bot này. "
                    "Đây là bot cá nhân chỉ phục vụ người dùng được cấp phép."
                )
            logger.warning("Từ chối truy cập từ người dùng không được phép: %s", user_id)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


def require_admin(func):
    """Decorator yêu cầu quyền Chủ sở hữu (Admin)."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        user_id = user.id if user else None
        config: Config = context.bot_data["config"]
        perm_mgr = get_perm_manager(context)

        if not perm_mgr.is_admin(user_id, config.allowed_telegram_user_id):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Lệnh này chỉ dành riêng cho Chủ sở hữu bot (Admin)."
                )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


async def send_split_message(update: Update, text: str) -> None:
    """Gửi tin nhắn Telegram với định dạng HTML, tự động chia nhỏ nếu vượt quá giới hạn 4000 ký tự."""
    if not update.effective_message:
        return

    async def _send_chunk(chunk_text: str) -> None:
        html_formatted = markdown_to_telegram_html(chunk_text)
        try:
            await update.effective_message.reply_text(
                html_formatted,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as err:
            logger.warning("Không thể parse HTML (%s), gửi dưới dạng plain text", err)
            await update.effective_message.reply_text(chunk_text)

    MAX_LENGTH = 4000
    if len(text) <= MAX_LENGTH:
        await _send_chunk(text)
        return

    # Chia nhỏ theo từng đoạn văn để không ngắt ngang chữ
    chunks = []
    current_chunk = ""
    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 <= MAX_LENGTH:
            current_chunk += (paragraph + "\n\n")
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Nếu một đoạn văn quá dài hơn MAX_LENGTH, cắt nhỏ theo ký tự
            if len(paragraph) > MAX_LENGTH:
                for i in range(0, len(paragraph), MAX_LENGTH):
                    chunks.append(paragraph[i : i + MAX_LENGTH])
                current_chunk = ""
            else:
                current_chunk = paragraph + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    for chunk in chunks:
        if chunk:
            await _send_chunk(chunk)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /start: Giới thiệu bot và các lệnh có sẵn tùy theo vai trò."""
    user = update.effective_user
    user_id = user.id if user else None
    config: Config = context.bot_data["config"]
    perm_mgr = get_perm_manager(context)

    if not perm_mgr.is_user_allowed(user_id, config.allowed_telegram_user_id):
        await update.effective_message.reply_text(
            f"Xin chào! Telegram ID của bạn là: <code>{user_id}</code>\n\n"
            "Hiện tại bạn chưa được cấp quyền sử dụng hệ thống này.\n"
            "Hãy sao chép mã ID trên và gửi cho Admin (Chủ sở hữu) để được cấp quyền xem nhóm!",
            parse_mode=ParseMode.HTML,
        )
        return

    is_admin = perm_mgr.is_admin(user_id, config.allowed_telegram_user_id)

    if is_admin:
        welcome_text = (
            "Xin chào Chủ sở hữu (Admin)!\n\n"
            "Tôi là Trợ lý Tóm tắt Tin nhắn Telegram cá nhân của bạn.\n\n"
            "Các lệnh dành cho bạn:\n"
            "• /summary: Tóm tắt tất cả tin nhắn chưa đọc hiện tại\n"
            "• /summary 24h: Tóm tắt tin nhắn trong vòng 24 giờ qua\n"
            "• /summary <tên/username> [số_tin]: Tóm tắt một nhóm cụ thể\n"
            "• /model: Xem hoặc đổi model AI trực tiếp\n"
            "• /status: Kiểm tra trạng thái hoạt động của bot\n"
            "• /users: Xem danh sách người dùng được cấp quyền\n"
            "• /grant <id> <nhóm>: Cấp quyền xem nhóm cho người khác\n"
            "• /revoke <id> [nhóm]: Thu hồi quyền xem nhóm\n"
            "• /cancel: Hủy tác vụ đang chạy\n"
            "• /help: Xem hướng dẫn chi tiết"
        )
    else:
        allowed = perm_mgr.get_allowed_chats(user_id, config.allowed_telegram_user_id) or []
        allowed_str = "\n".join(f"• {c}" for c in allowed) if allowed else "Chưa có nhóm nào."
        welcome_text = (
            "Xin chào! Bạn đã được cấp quyền sử dụng Trợ lý Tóm tắt Tin nhắn.\n\n"
            f"Các nhóm bạn được phép xem:\n{allowed_str}\n\n"
            "Cú pháp sử dụng:\n"
            "• /summary <Tên nhóm> [số_tin]: Tóm tắt nhóm được cấp quyền\n"
            "• /cancel: Hủy tác vụ tóm tắt đang chạy\n"
            "• /help: Xem hướng dẫn sử dụng"
        )

    await update.effective_message.reply_text(welcome_text)


@require_auth
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /help: Hướng dẫn sử dụng chi tiết bằng tiếng Việt."""
    user = update.effective_user
    user_id = user.id if user else None
    config: Config = context.bot_data["config"]
    perm_mgr = get_perm_manager(context)
    is_admin = perm_mgr.is_admin(user_id, config.allowed_telegram_user_id)

    if is_admin:
        help_text = (
            "HƯỚNG DẪN SỬ DỤNG DÀNH CHO ADMIN\n\n"
            "1. TÓM TẮT TIN NHẮN:\n"
            "• /summary: Quét toàn bộ tin chưa đọc trong các nhóm và chat 1-1\n"
            "• /summary 24h: Tóm tắt tin nhắn 24 giờ qua\n"
            "• /summary <tên nhóm> [số_tin]: Tóm tắt nhóm cụ thể\n\n"
            "2. QUẢN LÝ PHÂN QUYỀN:\n"
            "• /users: Xem danh sách người dùng được cấp quyền\n"
            "• /grant <user_id> <tên nhóm>: Cấp quyền xem nhóm cho ai đó\n"
            "  (Ví dụ: /grant 987654321 Dự Án Web)\n"
            "• /revoke <user_id> [tên nhóm]: Thu hồi quyền xem nhóm hoặc xóa user\n"
            "  (Ví dụ: /revoke 987654321 Dự Án Web)\n\n"
            "3. HỆ THỐNG:\n"
            "• /model [tên_model]: Xem hoặc đổi model OpenRouter\n"
            "• /status: Xem trạng thái kết nối & model\n"
            "• /cancel: Hủy tác vụ đang chạy"
        )
    else:
        allowed = perm_mgr.get_allowed_chats(user_id, config.allowed_telegram_user_id) or []
        allowed_str = "\n".join(f"• {c}" for c in allowed) if allowed else "Chưa có nhóm nào."
        help_text = (
            "HƯỚNG DẪN SỬ DỤNG\n\n"
            "Bạn có quyền tóm tắt tại các nhóm sau:\n"
            f"{allowed_str}\n\n"
            "Cú pháp:\n"
            "• /summary <tên nhóm> [số_tin]\n"
            "  (Ví dụ: /summary Dự Án Web 30)\n"
            "• /cancel: Hủy tác vụ tóm tắt đang xử lý nếu không muốn chờ"
        )

    await update.effective_message.reply_text(help_text)


@require_auth
@require_admin
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /status: Hiển thị trạng thái vận hành an toàn không lộ secrets."""
    config: Config = context.bot_data["config"]
    telethon: TelethonService = context.bot_data["telethon"]

    is_telethon_ok = await telethon.is_connected()
    telethon_status = "Đang kết nối & Đã xác thực" if is_telethon_ok else "Chưa xác thực hoặc mất kết nối"

    ai_configured = bool(config.openrouter_api_key)
    ai_status = "Đã cấu hình API Key" if ai_configured else "Chưa có API Key"

    message_service: MessageService = context.bot_data["message_service"]
    current_model = message_service.summarizer.ai_client.model

    status_text = (
        "TRẠNG THÁI HỆ THỐNG\n\n"
        f"• Bot Telegram: Đang hoạt động bình thường\n"
        f"• Tài khoản Telegram (Telethon): {telethon_status}\n"
        f"• OpenRouter API: {ai_status}\n"
        f"• Model AI đang dùng: {current_model}\n"
        f"• Timeout AI: {config.openrouter_timeout}s\n"
        f"• Giới hạn quét: Tối đa {config.max_chats_to_scan} hội thoại / {config.max_messages_per_chat} tin mỗi hội thoại\n"
        "• Lưu trữ cơ sở dữ liệu: Không sử dụng (Xử lý hoàn toàn trong bộ nhớ tạm)"
    )
    await update.effective_message.reply_text(status_text)


@require_auth
@require_admin
async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /model: Xem hoặc thay đổi model OpenRouter đang sử dụng."""
    message_service: MessageService = context.bot_data["message_service"]
    ai_client = message_service.summarizer.ai_client
    current_model = ai_client.model

    args = context.args or []
    if not args:
        reply_text = (
            f"MODEL AI HIỆN TẠI:\n{current_model}\n\n"
            "CÁCH ĐỔI MODEL KHÁC:\n"
            "Gửi lệnh: /model <tên_model>\n\n"
            "GỢI Ý CÁC MODEL MIỄN PHÍ PHỔ BIẾN TRÊN OPENROUTER:\n"
            "• /model nvidia/nemotron-3-super-120b-a12b:free (Khuyên dùng: 120B thông minh, tóm tắt tự nhiên)\n"
            "• /model nvidia/nemotron-3.5-lightning:free (Nhanh nhẹn, ổn định)\n"
            "• /model google/gemini-2.5-flash (Nếu có nạp credit OpenRouter)\n\n"
            "(Lưu ý: Bạn cũng có thể sửa biến OPENROUTER_MODEL trong file .env để lưu vĩnh viễn)."
        )
        await update.effective_message.reply_text(reply_text)
        return

    new_model = args[0].strip()
    ai_client.model = new_model
    logger.info("Người dùng đã chuyển model AI sang: %s", new_model)
    await update.effective_message.reply_text(
        f"Đã chuyển model AI sang: {new_model}\n"
        "Các yêu cầu tóm tắt tiếp theo sẽ sử dụng model này!"
    )


@require_auth
@require_admin
async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /grant <user_id> <tên_nhóm> [tên_hiển_thị]: Cấp quyền xem nhóm cho người dùng."""
    args = context.args or []
    if len(args) < 2:
        await update.effective_message.reply_text(
            "CÚ PHÁP CẤP QUYỀN:\n"
            "/grant <user_id> <Tên nhóm> [Tên hiển thị]\n\n"
            "Ví dụ:\n"
            "• /grant 987654321 Dự Án Web\n"
            "• /grant 987654321 Dự Án Web Hoàng Dev"
        )
        return

    target_id_str = args[0]
    if not target_id_str.isdigit():
        await update.effective_message.reply_text("User ID phải là một số nguyên (ví dụ: 123456789).")
        return

    target_id = int(target_id_str)
    # Nếu đối số cuối là tên hiển thị
    chat_name = " ".join(args[1:])

    perm_mgr = get_perm_manager(context)
    success = perm_mgr.grant_permission(target_id, chat_name)
    if success:
        await update.effective_message.reply_text(
            f"✅ Đã cấp quyền thành công!\n\n"
            f"• User ID: {target_id}\n"
            f"• Nhóm được phép xem: '{chat_name}'\n\n"
            f"Người dùng này hiện đã có thể dùng lệnh:\n"
            f"/summary {chat_name} [số_tin]"
        )
    else:
        await update.effective_message.reply_text("Không thể lưu phân quyền vào file permissions.json.")


@require_auth
@require_admin
async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /revoke <user_id> [tên_nhóm]: Thu hồi quyền xem nhóm."""
    args = context.args or []
    if not args:
        await update.effective_message.reply_text(
            "CÚ PHÁP THU HỒI QUYỀN:\n"
            "• Thu hồi 1 nhóm: /revoke <user_id> <Tên nhóm>\n"
            "• Xóa toàn bộ quyền: /revoke <user_id>\n\n"
            "Ví dụ:\n"
            "• /revoke 987654321 Dự Án Web\n"
            "• /revoke 987654321"
        )
        return

    target_id_str = args[0]
    if not target_id_str.isdigit():
        await update.effective_message.reply_text("User ID phải là một số nguyên.")
        return

    target_id = int(target_id_str)
    chat_name = " ".join(args[1:]) if len(args) > 1 else None

    perm_mgr = get_perm_manager(context)
    success = perm_mgr.revoke_permission(target_id, chat_name)
    if success:
        if chat_name:
            await update.effective_message.reply_text(
                f"✅ Đã thu hồi quyền xem nhóm '{chat_name}' của User ID {target_id}."
            )
        else:
            await update.effective_message.reply_text(
                f"✅ Đã xóa toàn bộ quyền của User ID {target_id} khỏi hệ thống."
            )
    else:
        await update.effective_message.reply_text("User ID không tồn tại trong danh sách hoặc không tìm thấy nhóm.")


@require_auth
@require_admin
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /users: Xem danh sách những người dùng được cấp quyền."""
    perm_mgr = get_perm_manager(context)
    users_data = perm_mgr.list_all_users()

    if not users_data:
        await update.effective_message.reply_text(
            "Hiện chưa có người dùng phụ nào được cấp quyền.\n"
            "Chỉ có Chủ sở hữu (Admin) mới có quyền dùng bot."
        )
        return

    lines = ["👥 DANH SÁCH NGƯỜI DÙNG ĐƯỢC CẤP QUYỀN:\n"]
    for uid, info in users_data.items():
        name = info.get("name", f"User_{uid}")
        chats = info.get("allowed_chats", [])
        chats_str = ", ".join(f"'{c}'" for c in chats) if chats else "Chưa có nhóm nào"
        lines.append(f"• {name} (ID: {uid}):\n  -> Được xem: {chats_str}\n")

    await update.effective_message.reply_text("\n".join(lines))


@require_auth
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /cancel: Hủy tác vụ tóm tắt đang chạy."""
    user = update.effective_user
    user_id = user.id if user else 0

    task = _active_summary_tasks.get(user_id)
    if not task or task.done():
        await update.effective_message.reply_text("Hiện không có tác vụ tóm tắt nào đang chạy.")
        return

    task.cancel()
    await update.effective_message.reply_text("Đang yêu cầu hủy tác vụ tóm tắt...")


@require_auth
async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /summary: Tóm tắt tin nhắn linh hoạt."""
    user = update.effective_user
    user_id = user.id if user else 0
    config: Config = context.bot_data["config"]
    perm_mgr = get_perm_manager(context)
    is_admin = perm_mgr.is_admin(user_id, config.allowed_telegram_user_id)

    args = context.args or []

    # KIỂM TRA PHÂN QUYỀN NẾU LÀ RESTRICTED USER
    if not is_admin:
        allowed_chats = perm_mgr.get_allowed_chats(user_id, config.allowed_telegram_user_id) or []
        allowed_str = "\n".join(f"• {c}" for c in allowed_chats) if allowed_chats else "Chưa có nhóm nào."

        # Người dùng phụ không được quét unread toàn bộ hay quét 24h
        if not args or (len(args) == 1 and args[0].lower() in ("24h", "24")) or (len(args) == 1 and args[0].isdigit()):
            await update.effective_message.reply_text(
                "Bạn chỉ có quyền xem tin nhắn ở một số nhóm nhất định, không thể quét toàn bộ tin unread hay 24h.\n\n"
                f"Vui lòng chỉ định nhóm bạn được phép xem:\n"
                f"/summary <Tên nhóm> [số_tin]\n\n"
                f"Danh sách nhóm bạn được phép xem:\n{allowed_str}"
            )
            return

        # Xác định tên nhóm yêu cầu
        if args[-1].isdigit():
            req_chat = " ".join(args[:-1])
        else:
            req_chat = " ".join(args)

        if not perm_mgr.can_access_chat(user_id, req_chat, config.allowed_telegram_user_id):
            await update.effective_message.reply_text(
                f"Bạn không có quyền truy cập vào nhóm '{req_chat}'.\n\n"
                f"Danh sách nhóm bạn được phép xem:\n{allowed_str}"
            )
            return

    # Kiểm tra xem có task nào đang chạy cho user này không
    existing_task = _active_summary_tasks.get(user_id)
    if existing_task and not existing_task.done():
        await update.effective_message.reply_text(
            "Bạn đang có một tác vụ tóm tắt đang chạy. Vui lòng đợi hoàn thành hoặc dùng lệnh /cancel để hủy trước."
        )
        return

    message_service: MessageService = context.bot_data["message_service"]
    args = context.args or []

    # Tạo Task bất đồng bộ để có thể hủy khi cần
    async def _run_summary_task():
        processing_msg = await update.effective_message.reply_text(
            "Đang kết nối tài khoản và đọc tin nhắn Telegram, vui lòng đợi trong giây lát..."
        )
        try:
            # Phân tích tham số đầu vào
            if not args:
                # /summary -> tóm tắt tin unread
                result = await message_service.summarize_unread()
            elif len(args) == 1 and args[0].lower() in ("24h", "24"):
                # /summary 24h -> tóm tắt tin trong 24h
                await processing_msg.edit_text("Đang lọc tin nhắn trong 24 giờ qua và gửi tới AI tóm tắt...")
                result = await message_service.summarize_24h()
            elif len(args) == 1 and args[0].isdigit():
                # /summary <limit> -> tóm tắt unread với số lượng tin chỉ định
                limit = int(args[0])
                result = await message_service.summarize_unread(max_messages_per_chat=limit)
            else:
                # /summary <tên/username> [số lượng]
                limit = 30
                if args[-1].isdigit():
                    limit = int(args[-1])
                    chat_name = " ".join(args[:-1])
                else:
                    chat_name = " ".join(args)

                await processing_msg.edit_text(
                    f"Đang đọc tin nhắn từ hội thoại '{chat_name}' và gửi tới AI tóm tắt..."
                )
                result = await message_service.summarize_specific_chat(
                    chat_identifier=chat_name,
                    limit=limit,
                )

            # Xóa hoặc sửa tin nhắn thông báo xử lý
            try:
                await processing_msg.delete()
            except Exception:
                pass

            # Gửi kết quả tóm tắt cho người dùng
            await send_split_message(update, result)

        except asyncio.CancelledError:
            try:
                await processing_msg.edit_text("Đã hủy tác vụ tóm tắt thành công.")
            except Exception:
                await update.effective_message.reply_text("Đã hủy tác vụ tóm tắt thành công.")
            raise

        except OpenRouterAuthError as e:
            await update.effective_message.reply_text(f"Lỗi xác thực OpenRouter: {e}")
        except OpenRouterQuotaError as e:
            await update.effective_message.reply_text(
                f"Lỗi OpenRouter: Tài khoản không đủ số dư hoặc model yêu cầu trả phí.\nChi tiết: {e}"
            )
        except OpenRouterRateLimitError as e:
            await update.effective_message.reply_text(
                f"Lỗi OpenRouter: Đã vượt giới hạn tần suất yêu cầu (Rate Limit). Vui lòng thử lại sau vài phút."
            )
        except OpenRouterModelNotFoundError as e:
            await update.effective_message.reply_text(f"Lỗi OpenRouter: Model không tồn tại hoặc đã bị gỡ bỏ.\nChi tiết: {e}")
        except OpenRouterTimeoutError as e:
            await update.effective_message.reply_text(f"Lỗi Timeout: Yêu cầu AI bị quá thời gian chờ.\nChi tiết: {e}")
        except OpenRouterError as e:
            await update.effective_message.reply_text(f"Lỗi dịch vụ OpenRouter: {e}")
        except Exception as e:
            logger.exception("Lỗi không mong muốn trong quá trình tóm tắt")
            await update.effective_message.reply_text(
                f"Đã xảy ra lỗi trong quá trình xử lý: {type(e).__name__}. Vui lòng thử lại sau."
            )
        finally:
            _active_summary_tasks.pop(user_id, None)

    task = asyncio.create_task(_run_summary_task())
    _active_summary_tasks[user_id] = task
