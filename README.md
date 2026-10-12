# Telegram Message Summarizer

> **Trợ lý tóm tắt tin nhắn Telegram cá nhân bằng AI (OpenRouter & Telethon)**

Telegram Message Summarizer là một Telegram Bot cá nhân độc lập giúp bạn đọc và tóm tắt các tin nhắn Telegram chưa đọc hoặc các cuộc hội thoại gần đây bằng tiếng Việt, tương tự như tính năng tóm tắt tin nhắn của Messenger.

Dự án ưu tiên tính **riêng tư**, **bảo mật**, **không sử dụng database** và **tối ưu chi phí** bằng cách kết nối với các mô hình ngôn ngữ lớn (LLM) miễn phí trên [OpenRouter](https://openrouter.ai).

---

## 🌟 Chức năng chính

- 📬 **Đọc tin nhắn chưa đọc:** Tự động lấy tin nhắn chưa đọc từ các cuộc hội thoại 1-1 và các nhóm chat mà tài khoản cá nhân của bạn tham gia.
- 🕒 **Tóm tắt 24 giờ qua:** Tổng hợp toàn bộ trao đổi quan trọng trong 24 giờ gần nhất bằng lệnh `/summary 24h`.
- 🎯 **Tóm tắt hội thoại chỉ định:** Cho phép tóm tắt riêng một người hoặc một nhóm cụ thể theo tên hoặc username: `/summary @username 20`.
- 🛡️ **Bảo mật trạng thái đọc:** Tuyệt đối **không** đánh dấu tin nhắn là đã đọc trên Telegram.
- ⚡ **Chống Prompt Injection:** Bảo vệ hệ thống khỏi các chỉ dẫn độc hại được nhúng trong nội dung tin nhắn Telegram.
- 🚫 **Không lưu trữ dữ liệu (Zero-Database):** Dữ liệu tin nhắn chỉ tồn tại tạm thời trong RAM trong lúc AI xử lý và được giải phóng ngay sau đó. Không lưu log nội dung tin nhắn.
- 🛑 **Hủy tác vụ linh hoạt:** Cho phép hủy ngay tác vụ tóm tắt đang chạy bằng lệnh `/cancel`.
- 💰 **Chi phí 0đ:** Mặc định cấu hình mô hình AI miễn phí (`meta-llama/llama-3.3-70b-instruct:free`).

---

## 🏗️ Kiến trúc hoạt động tổng quát

```text
[Người dùng]
     │  (Gửi lệnh: /summary, /status, /cancel)
     ▼
[Telegram Bot (python-telegram-bot)]
     │
     ├─► [Xác thực User ID] (ALLOWED_TELEGRAM_USER_ID)
     │
     ├─► [Telethon Client] ──► Kết nối Telegram MTProto (Đọc tin nhắn RAM-only)
     │
     ├─► [Message Service] ──► Lọc & đóng gói tin nhắn
     │
     ├─► [OpenRouter Client] ──► Gửi HTTP POST tới OpenRouter API
     │                                 │
     │                                 ▼
     │                          [OpenRouter LLM]
     │                                 │
     │◄── Nhận kết quả tóm tắt (Tiếng Việt)
     │
     ▼
[Gửi phản hồi về cuộc trò chuyện Telegram]
     │
     ▼
[Giải phóng bộ nhớ RAM] (Zero Database)
```

---

## 📋 Yêu cầu trước khi cài đặt

- **Hệ điều hành:** Windows 10/11, Linux hoặc macOS (Dự án được tối ưu và có tài liệu chi tiết cho Windows PowerShell).
- **Python:** Phiên bản `3.11` trở lên (Khuyến nghị Python 3.11 hoặc 3.12).
- **Tài khoản Telegram cá nhân:** Cần có số điện thoại để đăng nhập Telethon.
- **BotFather:** Một Telegram Bot Token từ [@BotFather](https://t.me/BotFather).
- **Telegram App Credentials:** `API_ID` và `API_HASH` từ [my.telegram.org](https://my.telegram.org).
- **OpenRouter API Key:** Đăng ký miễn phí tại [openrouter.ai](https://openrouter.ai).

---

## 🚀 Cài đặt nhanh (Quick Start)

### 1. Tạo môi trường ảo và cài đặt thư viện

Mở Windows PowerShell tại thư mục dự án:

```powershell
# Tạo môi trường ảo với Python 3.11+
py -3.12 -m venv .venv

# Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

> *Mẹo:* Nếu gặp lỗi chính sách thực thi script trên PowerShell (`ExecutionPolicy`), hãy chạy:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```

### 2. Thiết lập cấu hình `.env`

Sao chép file cấu hình mẫu và điền các thông tin của bạn:

```powershell
Copy-Item .env.example .env
```

Điền các thông tin trong file `.env`:
- `TELEGRAM_BOT_TOKEN`: Token lấy từ BotFather.
- `TELEGRAM_API_ID`: App ID từ my.telegram.org.
- `TELEGRAM_API_HASH`: App Hash từ my.telegram.org.
- `OPENROUTER_API_KEY`: Key từ openrouter.ai.
- `OPENROUTER_MODEL`: `meta-llama/llama-3.3-70b-instruct:free`

### 3. Đăng nhập Telegram cá nhân (Telethon) lần đầu

Chạy script đăng nhập độc lập trên terminal để nhập Số điện thoại, mã OTP và mật khẩu 2FA:

```powershell
python -m app.login
```

Sau khi đăng nhập thành công, script sẽ hiển thị **User ID** của bạn. Hãy dán ID đó vào biến `ALLOWED_TELEGRAM_USER_ID` trong `.env`.

### 4. Khởi chạy Bot

```powershell
python -m app.main
```

Bây giờ bạn có thể mở bot trên Telegram và gửi `/start`!

---

## 🤖 Hướng dẫn sử dụng các lệnh

| Lệnh | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- |
| `/start` | Giới thiệu bot và các lệnh có sẵn | `/start` |
| `/help` | Hướng dẫn chi tiết từng cú pháp | `/help` |
| `/summary` | Tóm tắt các tin nhắn chưa đọc | `/summary` |
| `/summary 24h` | Tóm tắt tin nhắn trong 24 giờ qua | `/summary 24h` |
| `/summary <tên> [số]` | Tóm tắt một cuộc trò chuyện cụ thể | `/summary @dongnghiep 20` |
| `/model [tên]` | Xem hoặc đổi model OpenRouter trực tiếp | `/model nvidia/nemotron-3-super-120b-a12b:free` |
| `/status` | Kiểm tra kết nối Telethon, AI model, RAM | `/status` |
| `/users` | Xem danh sách người dùng được cấp quyền (Admin) | `/users` |
| `/grant <id> <nhóm>` | Cấp quyền xem nhóm cho ai đó (Admin) | `/grant 987654321 Dự Án Web` |
| `/revoke <id> [nhóm]` | Thu hồi quyền xem nhóm (Admin) | `/revoke 987654321 Dự Án Web` |
| `/cancel` | Hủy ngay tác vụ tóm tắt đang chạy | `/cancel` |

---

## 🔒 Lưu ý bảo mật & Quyền riêng tư

1. **Không sử dụng Database:** Ứng dụng không lưu tin nhắn, tệp log hay lịch sử vào ổ đĩa. Dữ liệu tin nhắn chỉ được lưu tạm thời trong RAM trong thời gian gọi AI và được thu hồi ngay sau đó.
2. **Không đồng nghĩa dữ liệu không rời máy:** Khi yêu cầu tóm tắt, nội dung các tin nhắn được chọn sẽ được gửi qua kết nối HTTPS mã hóa tới OpenRouter để AI phân tích. Vui lòng đọc kỹ [docs/SECURITY.md](docs/SECURITY.md) để hiểu rõ chính sách bảo mật dữ liệu.
3. **Bảo vệ file `.env` và `*.session`:** Tuyệt đối không commit hoặc gửi hai file này cho bất kỳ ai. File `.gitignore` đã được cấu hình sẵn để loại trừ các file này.

---

## 📚 Tài liệu chi tiết

- [Hướng dẫn cài đặt từng bước cho Windows (docs/INSTALLATION.md)](docs/INSTALLATION.md)
- [Hướng dẫn sử dụng chi tiết & ví dụ (docs/USAGE.md)](docs/USAGE.md)
- [Kiến trúc hệ thống & luồng dữ liệu (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)
- [Khắc phục sự cố thường gặp (docs/TROUBLESHOOTING.md)](docs/TROUBLESHOOTING.md)
- [Chính sách & Giới hạn bảo mật (docs/SECURITY.md)](docs/SECURITY.md)
