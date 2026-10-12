# HƯỚNG DẪN SỬ DỤNG CHI TIẾT (USAGE GUIDE)

Tài liệu này giải thích chi tiết cách sử dụng các lệnh của **Telegram Message Summarizer Bot**, ví dụ dữ liệu đầu vào và cấu trúc kết quả trả về.

---

## Danh sách các lệnh chính

### 1. `/start`
- **Mục đích:** Khởi động phiên làm việc với bot, hiển thị thông tin giới thiệu và tóm tắt danh sách các lệnh khả dụng.
- **Quyền hạn:** Chỉ hiển thị đầy đủ tính năng cho người dùng sở hữu (`ALLOWED_TELEGRAM_USER_ID`).
- **Ví dụ sử dụng:**
  ```text
  /start
  ```
- **Kết quả phản hồi:**
  ```text
  Xin chào! Tôi là Trợ lý Tóm tắt Tin nhắn Telegram của bạn.

  Tôi có thể giúp bạn đọc và tóm tắt nhanh tin nhắn chưa đọc hoặc các cuộc trò chuyện gần đây bằng AI thông qua OpenRouter hoàn toàn tự động và an toàn.

  Các lệnh chính:
  • /summary: Tóm tắt tất cả các tin nhắn chưa đọc hiện tại
  • /summary 24h: Tóm tắt các tin nhắn trong vòng 24 giờ qua
  • /summary <tên/username> [số_tin]: Tóm tắt một cuộc trò chuyện cụ thể
  • /status: Kiểm tra trạng thái hoạt động của bot và các kết nối
  • /cancel: Hủy tác vụ tóm tắt đang diễn ra
  • /help: Xem hướng dẫn chi tiết
  ```

---

### 2. `/help`
- **Mục đích:** Hiển thị cẩm nang hướng dẫn sử dụng nhanh, giải thích rõ các tham số mở rộng.
- **Ví dụ sử dụng:**
  ```text
  /help
  ```

---

### 3. `/summary` (Tóm tắt tin nhắn chưa đọc)
- **Mục đích:** Đọc tất cả các cuộc trò chuyện (cá nhân và nhóm) đang có tin nhắn chưa đọc trên tài khoản Telegram của bạn, sau đó gửi nội dung đến OpenRouter để tổng hợp báo cáo.
- **Hành vi quan trọng:**
  - Bot **tuyệt đối không đánh dấu đã đọc** (không mark-as-read). Trạng thái unread trên Telegram của bạn vẫn được giữ nguyên.
  - Tự động bỏ qua các kênh thông báo (Broadcast Channels) và Bots để tiết kiệm token và tránh tin rác.
- **Ví dụ sử dụng:**
  ```text
  /summary
  ```
  Hoặc chỉ định số lượng tin tối đa lấy mỗi nhóm:
  ```text
  /summary 15
  ```
- **Định dạng kết quả trả về mẫu:**
  ```text
  **Tóm tắt chung**
  - Nhóm Dự Án Web đã chốt xong lịch họp release vào 15:00 chiều mai.
  - Anh Hoàng đã gửi file thiết kế Figma mới và yêu cầu duyệt trước 12:00.

  **Việc cần làm và thời hạn**
  - Duyệt bản vẽ Figma: Người giao việc: Hoàng - Hạn chót: 12:00 ngày 13/10.
  - Chuẩn bị slide báo cáo: Nhóm Dự Án Web - Họp 15:00 ngày 13/10.

  **Tin nhắn cần phản hồi**
  - Chị Lan (Kế toán): Hỏi về hóa đơn thanh toán máy chủ tháng trước.

  **Theo từng cuộc trò chuyện**
  - **Dự Án Web** (Nhóm chat):
    - Nội dung chính: Thảo luận chuẩn bị bản build và kiểm thử trước khi lên production.
    - Điểm cần lưu ý: Cần kiểm tra kỹ các lỗi liên quan đến cổng thanh toán.
  - **Hoàng Thiết Kế** (Tin nhắn cá nhân):
    - Nội dung chính: Đã cập nhật layout trang chủ theo feedback.
  ```

---

### 4. `/summary 24h` (Tóm tắt theo thời gian)
- **Mục đích:** Tóm tắt tất cả các tin nhắn được gửi trong vòng 24 giờ qua trên các cuộc trò chuyện, **không phụ thuộc** vào việc tin nhắn đó đã đọc hay chưa.
- **Phân biệt với `/summary`:**
  - `/summary`: Dựa trên trạng thái **chưa đọc (unread)** của Telegram tại thời điểm gọi lệnh. Nếu bạn đã lỡ đọc tin nhắn trên điện thoại, `/summary` sẽ không lấy lại tin đó.
  - `/summary 24h`: Dựa trên **mốc thời gian tạo tin nhắn** (`timestamp >= now - 24 hours`). Phù hợp để tổng kết lại một ngày làm việc dù bạn đã đọc lướt qua các tin nhắn trong ngày.
- **Ví dụ sử dụng:**
  ```text
  /summary 24h
  ```

---

### 5. `/summary <tên cuộc trò chuyện / @username> [số_lượng_tin]`
- **Mục đích:** Tóm tắt riêng biệt một cuộc trò chuyện cụ thể.
- **Ví dụ sử dụng:**
  - Tóm tắt 20 tin nhắn gần nhất với bạn bè:
    ```text
    /summary @hoangdesign 20
    ```
  - Tóm tắt thảo luận trong một nhóm theo tên:
    ```text
    /summary Team Kỹ Thuật 30
    ```

---

### 6. `/model [tên_model]` (Xem hoặc đổi model OpenRouter)
- **Mục đích:** Xem model hiện đang sử dụng hoặc đổi sang bất kỳ model nào khác trên OpenRouter ngay lập tức mà không cần chỉnh sửa `.env` hay khởi động lại bot.
- **Ví dụ sử dụng:**
  - Xem model đang dùng:
    ```text
    /model
    ```
  - Chuyển sang model Gemini 2.0 Flash:
    ```text
    /model google/gemini-2.0-flash-exp:free
    ```
  - Chuyển sang DeepSeek:
    ```text
    /model deepseek/deepseek-chat:free
    ```

---

### 7. `/status`
- **Mục đích:** Kiểm tra tình trạng sức khỏe của hệ thống một cách an toàn.
- **Ví dụ sử dụng:**
  ```text
  /status
  ```
- **Kết quả phản hồi mẫu:**
  ```text
  TRẠNG THÁI HỆ THỐNG

  • Bot Telegram: Đang hoạt động bình thường
  • Tài khoản Telegram (Telethon): Đang kết nối & Đã xác thực
  • OpenRouter API: Đã cấu hình API Key
  • Model AI: meta-llama/llama-3.3-70b-instruct:free
  • Timeout AI: 60.0s
  • Giới hạn quét: Tối đa 10 hội thoại / 30 tin mỗi hội thoại
  • Lưu trữ cơ sở dữ liệu: Không sử dụng (Xử lý hoàn toàn trong bộ nhớ tạm)
  ```
  *(Lưu ý: Không bao giờ hiển thị API Key, Hash hoặc mã bí mật)*.

### 8. `/cancel`
- **Mục đích:** Hủy ngay lập tức tác vụ tóm tắt AI đang xử lý nếu thời gian phản hồi quá lâu hoặc bạn không muốn tiếp tục.
- **Ví dụ sử dụng:**
  ```text
  /cancel
  ```

---

## 🔐 Các lệnh Phân quyền & Quản lý Người dùng (Dành riêng cho Admin)

### 9. `/users`
- **Mục đích:** Xem danh sách những ai đang được cấp quyền và họ được phép xem nhóm nào.
- **Ví dụ:**
  ```text
  /users
  ```

### 10. `/grant <user_id> <Tên nhóm> [Tên hiển thị]`
- **Mục đích:** Cấp quyền xem và tóm tắt một nhóm cụ thể cho một người dùng.
- **Ví dụ:**
  ```text
  /grant 987654321 Dự Án Web Hoàng Dev
  ```
  *(Sau khi cấp, người có ID `987654321` sẽ chỉ có thể tóm tắt nhóm "Dự Án Web", hoàn toàn không xem được các tin nhắn hay nhóm khác của bạn).*

### 11. `/revoke <user_id> [Tên nhóm]`
- **Mục đích:** Thu hồi quyền xem một nhóm hoặc xóa vĩnh viễn quyền truy cập của người dùng.
- **Ví dụ:**
  - Thu hồi 1 nhóm:
    ```text
    /revoke 987654321 Dự Án Web
    ```
  - Xóa toàn bộ quyền:
    ```text
    /revoke 987654321
    ```
