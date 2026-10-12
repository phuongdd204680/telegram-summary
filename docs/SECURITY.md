# BẢO MẬT VÀ QUYỀN RIÊNG TƯ (SECURITY & PRIVACY)

Tài liệu này giải thích rõ ràng và minh bạch các khía cạnh bảo mật, vòng đời dữ liệu và những lưu ý quan trọng khi vận hành hệ thống **Telegram Message Summarizer**.

---

## 1. Nguyên tắc cốt lõi: Không Database (Zero-Database)

Hệ thống được thiết kế hoàn toàn không sử dụng cơ sở dữ liệu (Database-less):
- **Không có SQLite, PostgreSQL, MySQL hay Redis.**
- **Không lưu lịch sử tin nhắn:** Toàn bộ tin nhắn đọc từ Telegram chỉ nằm trong biến bộ nhớ (RAM) trong khoảng thời gian cần thiết để gửi cho AI và định dạng phản hồi.
- **Không lưu bản tóm tắt:** Khi bản tóm tắt được gửi về Telegram chat của bạn, các biến chứa nội dung sẽ được giải phóng ngay lập tức cho bộ thu gom rác (Garbage Collector) của Python.
- **Không chạy quét nền định kỳ:** Bot chỉ đọc tin nhắn khi và chỉ khi bạn chủ động gửi lệnh (`/summary`). Không có cron job hoặc daemon tự động quét dữ liệu lén lút.

---

## 2. Dữ liệu rời khỏi máy tính như thế nào?

> ⚠️ **CẢNH BÁO QUAN TRỌNG VỀ QUYỀN RIÊNG TƯ:**
> Việc không sử dụng database **KHÔNG đồng nghĩa với việc dữ liệu không bao giờ rời khỏi máy tính của bạn**.

Khi bạn thực hiện lệnh tóm tắt:
1. Nội dung văn bản của các tin nhắn được chọn (người gửi, thời gian, nội dung chữ) sẽ được đóng gói và gửi qua kết nối mã hóa **HTTPS** tới máy chủ của [OpenRouter](https://openrouter.ai).
2. Tại OpenRouter, dữ liệu được chuyển tiếp tới nhà cung cấp mô hình AI tương ứng (ví dụ Meta, Google hoặc DeepSeek tùy theo model bạn chọn trong `OPENROUTER_MODEL`).
3. Sau khi AI suy luận xong, kết quả trả về cho máy tính của bạn và dữ liệu tạm trên máy được xóa bỏ.

**Khuyến nghị:**
- Trước khi sử dụng với các nội dung tin nhắn đặc biệt nhạy cảm (như thông tin tài chính mật, mật khẩu, dữ liệu y tế cá nhân), bạn nên kiểm tra chính sách lưu trữ và xử lý dữ liệu (Data Privacy Policy) của [OpenRouter](https://openrouter.ai/privacy) và nhà cung cấp mô hình tương ứng.
- Tuyệt đối không dùng bot để tóm tắt các cuộc trò chuyện chứa thông tin bí mật cấp doanh nghiệp nếu chính sách bảo mật nội bộ không cho phép gửi dữ liệu lên các dịch vụ đám mây công cộng.

---

## 3. Dữ liệu nào thực sự được lưu trên máy của bạn?

Chỉ có 2 loại dữ liệu duy nhất được lưu trên ổ đĩa máy tính của bạn:

1. **File cấu hình `.env`:**
   - Chứa `TELEGRAM_BOT_TOKEN`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `ALLOWED_TELEGRAM_USER_ID`, `OPENROUTER_API_KEY`.
   - Đây là các khóa bí mật để chạy chương trình.
2. **File phiên đăng nhập Telethon (`*.session`):**
   - Chứa thông tin khóa phiên MTProto để duy trì đăng nhập vào tài khoản Telegram cá nhân của bạn mà không cần hỏi lại mã OTP mỗi lần chạy.
   - **Tệp này có giá trị tương đương với tài khoản Telegram của bạn**. Bất kỳ ai có tệp `.session` đều có thể đăng nhập vào tài khoản Telegram của bạn.

---

## 4. Biện pháp bảo vệ khóa và tệp phiên

1. **Kiểm tra `.gitignore`:**
   - File `.gitignore` của dự án đã được cấu hình sẵn để loại trừ `.env` và `*.session`.
   - Trước khi thực hiện bất kỳ lệnh `git commit` nào, hãy luôn kiểm tra lại bằng lệnh `git status` để chắc chắn không vô tình đẩy các file này lên GitHub hoặc GitLab.
2. **Không chia sẻ thư mục dự án chưa qua làm sạch:**
   - Nếu cần sao chép mã nguồn cho người khác, hãy xóa bỏ file `.session` và file `.env` trước.
3. **Thu hồi quyền truy cập khi nghi ngờ lộ thông tin:**
   - Nếu nghi ngờ file session bị lộ: Mở ứng dụng Telegram trên điện thoại > **Cài đặt (Settings)** > **Thiết bị (Devices)** > Nhấn vào phiên Telethon và chọn **"Chấm dứt phiên" (Terminate Session)** ngay lập tức.
   - Nếu nghi ngờ lộ Bot Token: Vào `@BotFather` gửi lệnh `/revoke` để cấp lại token mới.
   - Nếu nghi ngờ lộ OpenRouter API Key: Vào [openrouter.ai/keys](https://openrouter.ai/keys) và xóa key cũ.

---

## 5. An toàn trong Ghi Log (Logging Security)

Hệ thống ghi log (`logging`) của dự án tuân thủ nghiêm ngặt:
- **Không ghi nội dung tin nhắn riêng tư vào log.**
- **Không in API Key, API Hash hoặc Token vào file log hay màn hình terminal.**
- Khi xảy ra lỗi kết nối hoặc ngoại lệ, log chỉ ghi nhận mã lỗi và thông báo kỹ thuật tổng quát, bảo vệ hoàn toàn dữ liệu của bạn khỏi việc bị lưu vết ngoài ý muốn.
