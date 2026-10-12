"""Service điều phối đọc tin nhắn và tóm tắt trong bộ nhớ tạm thời."""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional
from app.ai.summarizer import MessageSummarizer
from app.config import Config
from app.telegram_client.client import ChatDialogData, TelethonService

logger = logging.getLogger(__name__)


class MessageService:
    """Điều phối quy trình lấy tin nhắn và gửi tóm tắt AI hoàn toàn trong RAM."""

    def __init__(
        self,
        config: Config,
        telethon_service: TelethonService,
        summarizer: MessageSummarizer,
    ):
        self.config = config
        self.telethon_service = telethon_service
        self.summarizer = summarizer

    async def summarize_unread(
        self,
        max_chats: Optional[int] = None,
        max_messages_per_chat: Optional[int] = None,
    ) -> str:
        """Tóm tắt các tin nhắn chưa đọc từ các cuộc trò chuyện (Private & Group)."""
        chats_limit = max_chats or self.config.max_chats_to_scan
        msgs_limit = max_messages_per_chat or self.config.max_messages_per_chat
        total_limit = self.config.total_max_messages

        logger.info(
            "Bắt đầu lấy tin nhắn chưa đọc (tối đa %s hội thoại, %s tin/hội thoại)...",
            chats_limit,
            msgs_limit,
        )

        chats: List[ChatDialogData] = []
        try:
            chats = await self.telethon_service.get_unread_chats(
                max_chats=chats_limit,
                max_messages_per_chat=msgs_limit,
                total_max_messages=total_limit,
            )

            if not chats:
                return "Hiện tại không có tin nhắn chưa đọc nào trong các cuộc trò chuyện cá nhân hoặc nhóm."

            total_messages_count = sum(len(c.messages) for c in chats)
            logger.info(
                "Đã lấy %s tin nhắn từ %s cuộc trò chuyện chưa đọc. Bắt đầu tóm tắt AI...",
                total_messages_count,
                len(chats),
            )

            summary = await self.summarizer.summarize_chats(chats)
            return summary

        except asyncio.CancelledError:
            logger.info("Tác vụ tóm tắt tin nhắn chưa đọc đã bị người dùng hủy.")
            raise
        finally:
            # Giải phóng dữ liệu tạm thời trong bộ nhớ
            chats.clear()
            del chats

    async def summarize_24h(
        self,
        max_chats: Optional[int] = None,
        max_messages_per_chat: Optional[int] = None,
    ) -> str:
        """Tóm tắt các tin nhắn phát sinh trong vòng 24 giờ qua."""
        chats_limit = max_chats or self.config.max_chats_to_scan
        msgs_limit = max_messages_per_chat or self.config.max_messages_per_chat
        total_limit = self.config.total_max_messages

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        logger.info("Bắt đầu lấy tin nhắn 24 giờ qua (tính từ %s)...", since.isoformat())

        chats: List[ChatDialogData] = []
        try:
            chats = await self.telethon_service.get_recent_messages_chats(
                since_datetime=since,
                max_chats=chats_limit,
                max_messages_per_chat=msgs_limit,
                total_max_messages=total_limit,
            )

            if not chats:
                return "Không có tin nhắn nào được gửi trong vòng 24 giờ qua trong các hội thoại cá nhân và nhóm."

            total_messages_count = sum(len(c.messages) for c in chats)
            logger.info(
                "Đã lấy %s tin nhắn trong 24h từ %s cuộc trò chuyện. Bắt đầu tóm tắt AI...",
                total_messages_count,
                len(chats),
            )

            summary = await self.summarizer.summarize_chats(
                chats,
                custom_instructions="Lưu ý: Đây là toàn bộ tin nhắn trao đổi trong 24 giờ qua.",
            )
            return summary

        except asyncio.CancelledError:
            logger.info("Tác vụ tóm tắt tin nhắn 24h đã bị người dùng hủy.")
            raise
        finally:
            chats.clear()
            del chats

    async def summarize_specific_chat(
        self,
        chat_identifier: str,
        limit: int = 30,
        unread_only: bool = False,
    ) -> str:
        """Tóm tắt tin nhắn của một cuộc trò chuyện cụ thể (theo tên hoặc username)."""
        logger.info("Bắt đầu lấy tin nhắn cho cuộc trò chuyện cụ thể: '%s'...", chat_identifier)

        chat_data: Optional[ChatDialogData] = None
        try:
            chat_data = await self.telethon_service.get_specific_chat_messages(
                chat_identifier=chat_identifier,
                limit=limit,
                unread_only=unread_only,
            )

            if not chat_data or not chat_data.messages:
                return f"Không tìm thấy cuộc trò chuyện hoặc không có tin nhắn nào từ '{chat_identifier}'."

            logger.info(
                "Đã lấy %s tin nhắn từ '%s'. Bắt đầu tóm tắt AI...",
                len(chat_data.messages),
                chat_data.chat_title,
            )

            summary = await self.summarizer.summarize_chats([chat_data])
            return summary

        except asyncio.CancelledError:
            logger.info("Tác vụ tóm tắt cuộc trò chuyện cụ thể đã bị người dùng hủy.")
            raise
        finally:
            if chat_data:
                chat_data.messages.clear()
            del chat_data
