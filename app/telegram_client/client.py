"""Wrapper quản lý kết nối và đọc tin nhắn Telegram qua Telethon."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import List, Optional
from telethon import TelegramClient
from telethon.tl.types import User, Channel, Chat

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Đối tượng biểu diễn một tin nhắn trong bộ nhớ tạm thời."""
    message_id: int
    sender_name: str
    text: str
    timestamp: datetime
    reply_to_msg_id: Optional[int] = None


@dataclass
class ChatDialogData:
    """Dữ liệu một cuộc trò chuyện cùng danh sách tin nhắn cần tóm tắt."""
    chat_id: int
    chat_title: str
    chat_type: str  # 'private' | 'group'
    unread_count: int
    messages: List[ChatMessage] = field(default_factory=list)


class TelethonService:
    """Dịch vụ kết nối Telethon để đọc tin nhắn từ tài khoản cá nhân."""

    def __init__(self, session_name: str, api_id: int, api_hash: str):
        self.session_name = session_name
        self.api_id = api_id
        self.api_hash = api_hash
        self._client: Optional[TelegramClient] = None

    @property
    def client(self) -> TelegramClient:
        if self._client is None:
            self._client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        return self._client

    async def start(self) -> bool:
        """Khởi động kết nối Telethon và kiểm tra trạng thái đăng nhập.

        Không yêu cầu nhập OTP trong tiến trình chạy nền.
        Nếu chưa đăng nhập, người dùng cần chạy script CLI riêng (app/login.py).
        """
        if not self.client.is_connected():
            await self.client.connect()

        authorized = await self.client.is_user_authorized()
        if not authorized:
            logger.warning("Phiên Telethon chưa được xác thực hoặc đã hết hạn.")
            return False

        me = await self.client.get_me()
        user_title = getattr(me, "first_name", "") or getattr(me, "username", "Unknown")
        logger.info("Telethon đã kết nối thành công với tài khoản: %s", user_title)
        return True

    async def disconnect(self) -> None:
        """Ngắt kết nối Telethon an toàn."""
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Đã ngắt kết nối Telethon.")

    async def is_connected(self) -> bool:
        """Kiểm tra Telethon có đang kết nối và đã xác thực hay không."""
        if self._client is None or not self._client.is_connected():
            return False
        return await self._client.is_user_authorized()

    def _resolve_chat_type(self, entity) -> Optional[str]:
        """Xác định loại cuộc trò chuyện: private hoặc group.

        Bỏ qua broadcast channels và bot.
        """
        if isinstance(entity, User):
            if getattr(entity, "bot", False):
                return None
            return "private"
        elif isinstance(entity, Chat):
            return "group"
        elif isinstance(entity, Channel):
            # Trong Telethon, Channel có thể là Broadcast Channel hoặc Megagroup/Supergroup
            # Chỉ lấy nếu là group/megagroup
            if getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False):
                return "group"
            return None
        return None

    def _get_sender_name(self, sender) -> str:
        """Lấy tên người gửi an toàn, không chứa thông tin nhạy cảm."""
        if not sender:
            return "Người dùng ẩn danh"
        if isinstance(sender, User):
            first = getattr(sender, "first_name", "") or ""
            last = getattr(sender, "last_name", "") or ""
            full_name = f"{first} {last}".strip()
            if full_name:
                return full_name
            username = getattr(sender, "username", "")
            return f"@{username}" if username else f"User_{sender.id}"
        elif hasattr(sender, "title"):
            return sender.title
        return "Người dùng"

    async def get_unread_chats(
        self,
        max_chats: int = 10,
        max_messages_per_chat: int = 30,
        total_max_messages: int = 150,
    ) -> List[ChatDialogData]:
        """Lấy danh sách các cuộc trò chuyện có tin nhắn chưa đọc.

        LƯU Ý QUAN TRỌNG:
        Tuyệt đối không gọi client.send_read_acknowledge() để giữ nguyên trạng thái
        chưa đọc của tin nhắn trên Telegram.
        """
        results: List[ChatDialogData] = []
        total_collected = 0

        # Lấy danh sách dialogs
        async for dialog in self.client.iter_dialogs():
            if dialog.unread_count <= 0:
                continue

            chat_type = self._resolve_chat_type(dialog.entity)
            if not chat_type:
                # Bỏ qua bot và broadcast channel
                continue

            limit = min(dialog.unread_count, max_messages_per_chat)
            if total_collected + limit > total_max_messages:
                limit = max(1, total_max_messages - total_collected)

            messages: List[ChatMessage] = []
            async for msg in self.client.iter_messages(dialog, limit=limit):
                text = msg.message or msg.raw_text or ""
                # Bỏ qua tin nhắn không có text (ví dụ sticker/media không có caption)
                if not text.strip():
                    if msg.media:
                        text = "[Đính kèm tệp/hình ảnh/media]"
                    else:
                        continue

                sender = await msg.get_sender()
                sender_name = self._get_sender_name(sender)

                messages.append(
                    ChatMessage(
                        message_id=msg.id,
                        sender_name=sender_name,
                        text=text.strip(),
                        timestamp=msg.date,
                        reply_to_msg_id=msg.reply_to_msg_id if hasattr(msg, "reply_to_msg_id") else None,
                    )
                )

            if messages:
                # iter_messages trả về từ mới nhất đến cũ nhất -> đảo lại theo thứ tự thời gian tăng dần
                messages.reverse()
                results.append(
                    ChatDialogData(
                        chat_id=dialog.id,
                        chat_title=dialog.title or f"Chat_{dialog.id}",
                        chat_type=chat_type,
                        unread_count=dialog.unread_count,
                        messages=messages,
                    )
                )
                total_collected += len(messages)

            if len(results) >= max_chats or total_collected >= total_max_messages:
                break

        return results

    async def get_recent_messages_chats(
        self,
        since_datetime: datetime,
        max_chats: int = 10,
        max_messages_per_chat: int = 30,
        total_max_messages: int = 150,
    ) -> List[ChatDialogData]:
        """Lấy các tin nhắn được gửi từ thời điểm since_datetime (ví dụ: 24 giờ qua).

        Dựa trên mốc thời gian tin nhắn, không phụ thuộc vào trạng thái chưa đọc.
        Tuyệt đối không đánh dấu đã đọc.
        """
        results: List[ChatDialogData] = []
        total_collected = 0

        # Chuẩn hóa timezone
        if since_datetime.tzinfo is None:
            since_datetime = since_datetime.replace(tzinfo=timezone.utc)

        async for dialog in self.client.iter_dialogs():
            chat_type = self._resolve_chat_type(dialog.entity)
            if not chat_type:
                continue

            messages: List[ChatMessage] = []
            async for msg in self.client.iter_messages(dialog, limit=max_messages_per_chat):
                msg_date = msg.date
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)

                if msg_date < since_datetime:
                    # Vì iter_messages theo thứ tự mới nhất về cũ nhất, nên nếu msg_date < since_datetime
                    # ta có thể dừng quét dialog này
                    break

                text = msg.message or msg.raw_text or ""
                if not text.strip():
                    if msg.media:
                        text = "[Đính kèm tệp/hình ảnh/media]"
                    else:
                        continue

                sender = await msg.get_sender()
                sender_name = self._get_sender_name(sender)

                messages.append(
                    ChatMessage(
                        message_id=msg.id,
                        sender_name=sender_name,
                        text=text.strip(),
                        timestamp=msg.date,
                        reply_to_msg_id=msg.reply_to_msg_id if hasattr(msg, "reply_to_msg_id") else None,
                    )
                )

                if total_collected + len(messages) >= total_max_messages:
                    break

            if messages:
                messages.reverse()
                results.append(
                    ChatDialogData(
                        chat_id=dialog.id,
                        chat_title=dialog.title or f"Chat_{dialog.id}",
                        chat_type=chat_type,
                        unread_count=dialog.unread_count,
                        messages=messages,
                    )
                )
                total_collected += len(messages)

            if len(results) >= max_chats or total_collected >= total_max_messages:
                break

        return results

    async def get_specific_chat_messages(
        self,
        chat_identifier: str,
        limit: int = 30,
        unread_only: bool = False,
    ) -> Optional[ChatDialogData]:
        """Lấy tin nhắn từ một cuộc trò chuyện cụ thể (theo tên, @username hoặc ID).

        Nếu unread_only=True: chỉ lấy các tin chưa đọc của cuộc trò chuyện đó.
        Nếu unread_only=False: lấy tối đa limit tin nhắn gần nhất.
        """
        # Tìm entity phù hợp
        target_dialog = None
        clean_target = chat_identifier.strip().lower()

        async for dialog in self.client.iter_dialogs():
            title = (dialog.title or "").strip().lower()
            entity = dialog.entity
            username = getattr(entity, "username", "") or ""
            username = f"@{username}".lower() if username else ""
            str_id = str(dialog.id)

            if clean_target in (title, username, str_id) or (clean_target.startswith("@") and clean_target == username):
                target_dialog = dialog
                break
            # So khớp tương đối tên cuộc trò chuyện nếu tên chứa từ khóa
            elif clean_target in title:
                target_dialog = dialog
                break

        if not target_dialog:
            return None

        chat_type = self._resolve_chat_type(target_dialog.entity) or "group"
        fetch_limit = limit
        if unread_only and target_dialog.unread_count > 0:
            fetch_limit = min(target_dialog.unread_count, limit)

        messages: List[ChatMessage] = []
        async for msg in self.client.iter_messages(target_dialog, limit=fetch_limit):
            text = msg.message or msg.raw_text or ""
            if not text.strip():
                if msg.media:
                    text = "[Đính kèm tệp/hình ảnh/media]"
                else:
                    continue

            sender = await msg.get_sender()
            sender_name = self._get_sender_name(sender)

            messages.append(
                ChatMessage(
                    message_id=msg.id,
                    sender_name=sender_name,
                    text=text.strip(),
                    timestamp=msg.date,
                    reply_to_msg_id=msg.reply_to_msg_id if hasattr(msg, "reply_to_msg_id") else None,
                )
            )

        if messages:
            messages.reverse()

        return ChatDialogData(
            chat_id=target_dialog.id,
            chat_title=target_dialog.title or f"Chat_{target_dialog.id}",
            chat_type=chat_type,
            unread_count=target_dialog.unread_count,
            messages=messages,
        )
