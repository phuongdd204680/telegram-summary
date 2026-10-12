"""Kiểm thử tính năng phân quyền Role-Based Access Control và quản lý permissions.json."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.bot.handlers import grant_command, revoke_command, users_command, summary_command
from app.permissions import PermissionManager


@pytest.fixture
def temp_perm_file():
    """Tạo file permissions tạm thời cho kiểm thử."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_permission_manager_lifecycle(temp_perm_file):
    """Kiểm tra chu trình cấp và thu hồi quyền trong PermissionManager."""
    pm = PermissionManager(file_path=temp_perm_file)

    admin_id = 111111
    user_id = 222222

    # Ban đầu user chưa có quyền
    assert pm.is_user_allowed(user_id, admin_id) is False
    assert pm.can_access_chat(user_id, "Dự Án Web", admin_id) is False

    # Admin luôn có quyền với mọi nhóm
    assert pm.is_admin(admin_id, admin_id) is True
    assert pm.can_access_chat(admin_id, "Bất Kỳ Nhóm Nào", admin_id) is True

    # Cấp quyền cho user xem nhóm "Dự Án Web"
    pm.grant_permission(user_id, "Dự Án Web", "Hoàng Dev")
    assert pm.is_user_allowed(user_id, admin_id) is True
    assert pm.can_access_chat(user_id, "Dự Án Web", admin_id) is True
    assert pm.can_access_chat(user_id, "dự án web", admin_id) is True  # Khớp chữ thường
    assert pm.can_access_chat(user_id, "Nhóm Kế Toán", admin_id) is False  # Nhóm khác bị cấm

    # Cấp thêm nhóm thứ 2
    pm.grant_permission(user_id, "Team Frontend")
    allowed = pm.get_allowed_chats(user_id, admin_id)
    assert "Dự Án Web" in allowed
    assert "Team Frontend" in allowed

    # Thu hồi 1 nhóm
    pm.revoke_permission(user_id, "Dự Án Web")
    assert pm.can_access_chat(user_id, "Dự Án Web", admin_id) is False
    assert pm.can_access_chat(user_id, "Team Frontend", admin_id) is True

    # Thu hồi toàn bộ quyền
    pm.revoke_permission(user_id)
    assert pm.is_user_allowed(user_id, admin_id) is False


@pytest.mark.asyncio
async def test_grant_and_users_command(temp_perm_file, sample_config):
    """Kiểm tra lệnh /grant và /users."""
    pm = PermissionManager(file_path=temp_perm_file)

    update = MagicMock()
    update.effective_user.id = sample_config.allowed_telegram_user_id
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot_data = {
        "config": sample_config,
        "permission_manager": pm,
    }

    # Chạy /grant 333444 "Nhóm Marketing"
    context.args = ["333444", "Nhóm", "Marketing"]
    await grant_command(update, context)

    update.effective_message.reply_text.assert_awaited()
    last_reply = update.effective_message.reply_text.call_args[0][0]
    assert "cấp quyền thành công" in last_reply.lower()
    assert pm.can_access_chat(333444, "Nhóm Marketing", sample_config.allowed_telegram_user_id) is True

    # Chạy /users
    update.effective_message.reply_text.reset_mock()
    await users_command(update, context)
    users_reply = update.effective_message.reply_text.call_args[0][0]
    assert "333444" in users_reply
    assert "Nhóm Marketing" in users_reply


@pytest.mark.asyncio
async def test_restricted_user_cannot_scan_unread_all(temp_perm_file, sample_config):
    """Người dùng bị giới hạn không được phép quét unread toàn bộ."""
    pm = PermissionManager(file_path=temp_perm_file)
    user_id = 555666
    pm.grant_permission(user_id, "Nhóm Riêng")

    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot_data = {
        "config": sample_config,
        "permission_manager": pm,
        "message_service": MagicMock(),
    }
    context.args = []  # Gõ /summary unread toàn bộ

    await summary_command(update, context)
    reply = update.effective_message.reply_text.call_args[0][0]
    assert "không thể quét toàn bộ" in reply
