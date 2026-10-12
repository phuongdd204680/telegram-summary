"""Quản lý phân quyền người dùng (Role-Based Access Control).

Lưu trữ danh sách người dùng được cấp quyền giới hạn và các nhóm họ được phép truy cập
vào file permissions.json mà không cần sử dụng cơ sở dữ liệu.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PERMISSIONS_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "permissions.json")
)


class PermissionManager:
    """Quản lý đọc/ghi phân quyền từ file JSON."""

    def __init__(self, file_path: str = DEFAULT_PERMISSIONS_FILE):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Đảm bảo file permissions.json luôn tồn tại."""
        if not os.path.exists(self.file_path):
            initial_data = {"restricted_users": {}}
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error("Không thể tạo file permissions.json: %s", e)

    def load_permissions(self) -> Dict[str, Any]:
        """Đọc danh sách quyền từ file."""
        if not os.path.exists(self.file_path):
            return {"restricted_users": {}}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Lỗi khi đọc permissions.json: %s", e)
            return {"restricted_users": {}}

    def save_permissions(self, data: Dict[str, Any]) -> bool:
        """Lưu danh sách quyền vào file JSON."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Lỗi khi ghi permissions.json: %s", e)
            return False

    def is_user_allowed(self, user_id: Optional[int], admin_id: Optional[int]) -> bool:
        """Kiểm tra người dùng có quyền dùng bot hay không (Admin hoặc Restricted)."""
        if user_id is None:
            return False
        if admin_id is not None and user_id == admin_id:
            return True
        data = self.load_permissions()
        return str(user_id) in data.get("restricted_users", {})

    def is_admin(self, user_id: Optional[int], admin_id: Optional[int]) -> bool:
        """Kiểm tra có phải chủ sở hữu (Admin) hay không."""
        return user_id is not None and admin_id is not None and user_id == admin_id

    def get_allowed_chats(self, user_id: int, admin_id: Optional[int]) -> Optional[List[str]]:
        """Lấy danh sách nhóm được phép của user. Trả về None nếu là Admin (xem tất cả)."""
        if self.is_admin(user_id, admin_id):
            return None  # Admin được xem mọi nhóm
        data = self.load_permissions()
        user_info = data.get("restricted_users", {}).get(str(user_id))
        if user_info and "allowed_chats" in user_info:
            return user_info["allowed_chats"]
        return []

    def can_access_chat(
        self, user_id: int, chat_identifier: str, admin_id: Optional[int]
    ) -> bool:
        """Kiểm tra user có quyền truy cập nhóm/chat cụ thể hay không."""
        if self.is_admin(user_id, admin_id):
            return True

        allowed_chats = self.get_allowed_chats(user_id, admin_id)
        if allowed_chats is None:
            return True

        target = chat_identifier.strip().lower()
        for allowed in allowed_chats:
            clean_allowed = allowed.strip().lower()
            # Khớp tên chính xác hoặc từ khóa
            if clean_allowed in target or target in clean_allowed:
                return True
        return False

    def grant_permission(
        self,
        user_id: int,
        chat_name: str,
        display_name: Optional[str] = None,
    ) -> bool:
        """Cấp quyền xem một nhóm cho người dùng."""
        data = self.load_permissions()
        users = data.setdefault("restricted_users", {})
        str_id = str(user_id)

        if str_id not in users:
            users[str_id] = {
                "name": display_name or f"User_{user_id}",
                "allowed_chats": [],
            }

        if display_name:
            users[str_id]["name"] = display_name

        allowed_chats: List[str] = users[str_id].setdefault("allowed_chats", [])
        clean_chat = chat_name.strip()
        if clean_chat and clean_chat not in allowed_chats:
            allowed_chats.append(clean_chat)

        return self.save_permissions(data)

    def revoke_permission(
        self,
        user_id: int,
        chat_name: Optional[str] = None,
    ) -> bool:
        """Thu hồi quyền xem nhóm hoặc xóa hoàn toàn người dùng khỏi danh sách."""
        data = self.load_permissions()
        users = data.setdefault("restricted_users", {})
        str_id = str(user_id)

        if str_id not in users:
            return False

        if chat_name is None:
            # Xóa hoàn toàn user khỏi quyền
            del users[str_id]
        else:
            clean_chat = chat_name.strip().lower()
            allowed_chats = users[str_id].get("allowed_chats", [])
            users[str_id]["allowed_chats"] = [
                c for c in allowed_chats if c.strip().lower() != clean_chat
            ]

        return self.save_permissions(data)

    def list_all_users(self) -> Dict[str, Any]:
        """Lấy toàn bộ danh sách phân quyền."""
        data = self.load_permissions()
        return data.get("restricted_users", {})
