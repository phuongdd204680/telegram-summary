# HƯỚNG DẪN KHẮC PHỤC SỰ CỐ (TROUBLESHOOTING)

Tài liệu này tổng hợp các lỗi phổ biến trong quá trình cài đặt, kết nối và sử dụng bot, kèm theo hướng dẫn khắc phục chi tiết.

---

## 1. Sự cố Đăng nhập Telegram & Telethon

### ❌ Lỗi: `SessionPasswordNeededError` khi chạy `python -m app.login`
- **Nguyên nhân:** Tài khoản Telegram của bạn đã kích hoạt tính năng **Xác minh 2 bước (Two-Step Verification / 2FA)**.
- **Khắc phục:** Script `app.login` sẽ tự động phát hiện và nhắc bạn nhập mật khẩu 2FA trong terminal. Nhập đúng mật khẩu tài khoản của bạn để hoàn tất.

### ❌ Lỗi: `FloodWaitError: A wait of X seconds is required`
- **Nguyên nhân:** Bạn đã gửi yêu cầu gửi mã OTP quá nhiều lần trong thời gian ngắn. Telegram tạm thời giới hạn tài khoản.
- **Khắc phục:** Đợi hết số giây thông báo (thường từ vài phút đến vài chục phút) trước khi thử chạy lại `python -m app.login`. Không cố gắng gửi OTP liên tục.

### ❌ Lỗi: `PhoneNumberInvalidError`
- **Nguyên nhân:** Định dạng số điện thoại không hợp lệ.
- **Khắc phục:** Nhập số điện thoại kèm mã quốc gia (ví dụ ở Việt Nam thay số `09...` bằng `+849...`).

### ❌ File session bị lỗi hoặc muốn đăng nhập lại tài khoản khác
- **Khắc phục:** Xóa file `.session` hiện tại (ví dụ: `telegram_user_session.session`) và chạy lại:
  ```powershell
  python -m app.login
  ```

---

## 2. Sự cố Telegram Bot API & Quyền truy cập

### ❌ Bot không phản hồi bất kỳ tin nhắn nào
1. Kiểm tra tiến trình bot có đang chạy trên terminal không (`python -m app.main`).
2. Kiểm tra `TELEGRAM_BOT_TOKEN` trong `.env` có đúng với token do `@BotFather` cấp không.
3. Nếu bạn vừa thay đổi token, hãy khởi động lại bot.

### ❌ Bot phản hồi: `"Xin lỗi, bạn không có quyền sử dụng bot này..."`
- **Nguyên nhân:** User ID của bạn không khớp với biến `ALLOWED_TELEGRAM_USER_ID` trong file `.env`.
- **Khắc phục:**
  1. Kiểm tra User ID bằng cách chạy `python -m app.login` hoặc nhắn cho `@userinfobot`.
  2. Mở file `.env` và cập nhật chính xác:
     ```dotenv
     ALLOWED_TELEGRAM_USER_ID=<User_ID_Của_Bạn>
     ```
  3. Khởi động lại bot.

---

## 3. Sự cố OpenRouter AI

### ❌ Lỗi 401: `Lỗi xác thực OpenRouter (401/403)`
- **Nguyên nhân:** `OPENROUTER_API_KEY` bị thiếu, sai hoặc đã bị thu hồi (revoked).
- **Khắc phục:** Vào [openrouter.ai/keys](https://openrouter.ai/keys), tạo một API key mới và dán lại vào `.env`.

### ❌ Lỗi 402: `Số dư không đủ hoặc model yêu cầu trả phí (402)`
- **Nguyên nhân:** Model bạn cấu hình trong `OPENROUTER_MODEL` không phải model miễn phí, hoặc tài khoản OpenRouter chưa nạp credit.
- **Khắc phục:**
  - Chuyển sang model có hậu tố `:free` trong `.env`, ví dụ:
    ```dotenv
    OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
    ```
  - Tra cứu danh sách các model miễn phí hiện thời tại: [openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0).

### ❌ Lỗi 404: `Model không tồn tại hoặc đã bị gỡ bỏ (404)`
- **Nguyên nhân:** OpenRouter đã đổi tên định danh (slug) của model hoặc model thử nghiệm đã hết hạn.
- **Khắc phục:** Cập nhật lại model ID trong `.env`.

### ❌ Lỗi 429: `Quá giới hạn tần suất yêu cầu (Rate Limit)`
- **Nguyên nhân:** Các model miễn phí trên OpenRouter có giới hạn số lượt gọi/phút (thường là 10-20 requests/phút).
- **Khắc phục:** Đợi khoảng 1-2 phút rồi thử lại bằng lệnh `/summary`.

### ❌ Lỗi Timeout: `Kết nối tới OpenRouter bị timeout sau X giây`
- **Nguyên nhân:** Mô hình AI đang quá tải hoặc kết nối mạng quốc tế chậm.
- **Khắc phục:**
  - Tăng thời gian chờ trong `.env`:
    ```dotenv
    OPENROUTER_TIMEOUT=120
    ```
  - Hoặc chuyển sang model phản hồi nhanh hơn như `google/gemini-2.0-flash-exp:free`.

---

## 4. Sự cố Môi trường & PowerShell

### ❌ Lỗi: `Activate.ps1 cannot be loaded because running scripts is disabled`
- **Khắc phục:** Mở PowerShell và chạy:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
  .\.venv\Scripts\Activate.ps1
  ```

### ❌ Lỗi: `No module named 'app'` khi chạy lệnh
- **Nguyên nhân:** Bạn đang đứng sai thư mục hoặc không dùng cờ `-m`.
- **Khắc phục:** Đảm bảo bạn đang ở thư mục gốc của dự án (`f:\lungtung\telegram-summary`) và chạy với cú pháp module:
  ```powershell
  python -m app.main
  ```
