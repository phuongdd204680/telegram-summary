# HƯỚNG DẪN CÀI ĐẶT CHI TIẾT (WINDOWS POWERSHELL)

Tài liệu này cung cấp hướng dẫn cài đặt từng bước cho dự án **Telegram Message Summarizer** trên hệ điều hành Windows sử dụng **Windows PowerShell**.

---

## Mục lục
1. [Cài đặt và kiểm tra Python](#1-cài-đặt-và-kiểm-tra-python)
2. [Cài đặt Git (nếu cần)](#2-cài-đặt-git)
3. [Mở thư mục dự án](#3-mở-thư-mục-dự-án)
4. [Tạo môi trường ảo Virtual Environment](#4-tạo-môi-trường-ảo-virtual-environment)
5. [Kích hoạt môi trường ảo trong PowerShell](#5-kích-hoạt-môi-trường-ảo-trong-powershell)
6. [Xử lý lỗi Execution Policy khi chạy script PowerShell](#6-xử-lý-lỗi-execution-policy)
7. [Cài đặt các thư viện phụ thuộc](#7-cài-đặt-các-thư-viện-phụ-thuộc)
8. [Tạo Telegram Bot qua @BotFather và lấy Bot Token](#8-tạo-telegram-bot-qua-botfather)
9. [Lấy Telegram API ID và API HASH](#9-lấy-telegram-api-id-và-api-hash)
10. [Xác định Telegram User ID của bạn](#10-xác-định-telegram-user-id)
11. [Tạo OpenRouter API Key](#11-tạo-openrouter-api-key)
12. [Chọn và cấu hình Model OpenRouter](#12-chọn-và-cấu-hình-model-openrouter)
13. [Tạo và cấu hình file .env](#13-tạo-và-cấu-hình-file-env)
14. [Đăng nhập Telethon lần đầu](#14-đăng-nhập-telethon-lần-đầu)
15. [Khởi chạy ứng dụng Bot](#15-khởi-chạy-ứng-dụng-bot)
16. [Kiểm tra hoạt động của Bot](#16-kiểm-tra-hoạt-động-của-bot)
17. [Chạy bộ kiểm thử tự động (Unit Tests)](#17-chạy-bộ-kiểm-thử-tự-động)
18. [Xử lý các lỗi phổ biến](#18-xử-lý-các-lỗi-phổ-biến)

---

### 1. Cài đặt và kiểm tra Python
Dự án yêu cầu **Python 3.11 trở lên**.
Để kiểm tra phiên bản Python trên máy:
```powershell
py --list
```
Hoặc:
```powershell
python --version
```
Nếu chưa có Python 3.11+, tải và cài đặt từ trang chủ [python.org](https://www.python.org/downloads/).
> **Lưu ý quan trọng khi cài:** Hãy tích chọn vào ô **"Add python.exe to PATH"** trên trình cài đặt Windows.

---

### 2. Cài đặt Git
Nếu bạn tải mã nguồn qua Git:
```powershell
git --version
```
Nếu chưa có Git, tải tại [git-scm.com](https://git-scm.com/).

---

### 3. Mở thư mục dự án
Mở Windows Terminal hoặc PowerShell và điều hướng tới thư mục chứa mã nguồn:
```powershell
cd f:\lungtung\telegram-summary
```

---

### 4. Tạo môi trường ảo (Virtual Environment)
Tạo môi trường ảo `.venv` bằng Python launcher:
```powershell
py -3.12 -m venv .venv
```
*(Nếu bạn dùng Python 3.11, thay bằng `py -3.11 -m venv .venv`)*.

---

### 5. Kích hoạt môi trường ảo trong PowerShell
Chạy lệnh kích hoạt:
```powershell
.\.venv\Scripts\Activate.ps1
```
Khi kích hoạt thành công, bạn sẽ thấy tiền tố `(.venv)` xuất hiện ở đầu dòng lệnh PowerShell.

---

### 6. Xử lý lỗi Execution Policy
Nếu bạn gặp thông báo lỗi màu đỏ:
`... cannot be loaded because running scripts is disabled on this system ...`
Nguyên nhân là do chính sách bảo mật PowerShell mặc định chặn thực thi file `.ps1`.

**Cách giải quyết an toàn nhất (chỉ áp dụng cho phiên PowerShell hiện tại, không làm giảm bảo mật toàn hệ thống):**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```
Sau đó chạy lại lệnh kích hoạt:
```powershell
.\.venv\Scripts\Activate.ps1
```

---

### 7. Cài đặt các thư viện phụ thuộc
Khi môi trường ảo đã được kích hoạt `(.venv)`, chạy:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 8. Tạo Telegram Bot qua @BotFather
1. Mở ứng dụng Telegram, tìm kiếm bot chính thức: [@BotFather](https://t.me/BotFather).
2. Gửi lệnh `/newbot`.
3. Nhập tên hiển thị cho bot (ví dụ: `My Summarizer Bot`).
4. Nhập username kết thúc bằng chữ `bot` (ví dụ: `my_summary_assistant_bot`).
5. BotFather sẽ trả về **HTTP API Token** có dạng: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`. Lưu lại token này.

---

### 9. Lấy Telegram API ID và API HASH
Để Telethon có thể đọc tin nhắn từ tài khoản cá nhân của bạn:
1. Truy cập trang web chính thức của Telegram: [https://my.telegram.org](https://my.telegram.org).
2. Nhập số điện thoại tài khoản Telegram của bạn và mã xác nhận gửi về ứng dụng Telegram.
3. Chọn mục **"API development tools"**.
4. Điền form tạo ứng dụng mới (App title và Short name có thể đặt tùy ý, ví dụ `TeleSummary`).
5. Sao chép 2 giá trị:
   - `App api_id` (dạng số nguyên)
   - `App api_hash` (dạng chuỗi hex)

---

### 10. Xác định Telegram User ID
Dự án yêu cầu `ALLOWED_TELEGRAM_USER_ID` để bảo vệ quyền riêng tư cá nhân.
Có 2 cách lấy ID rất dễ dàng:
- **Cách 1 (Tự động):** Chạy script `python -m app.login` (ở bước 14 bên dưới), chương trình sẽ tự động in ra User ID của bạn trên màn hình!
- **Cách 2:** Mở Telegram, nhắn tin cho bot [@userinfobot](https://t.me/userinfobot) hoặc [@myidbot](https://t.me/myidbot) và xem dòng `Id`.

---

### 11. Tạo OpenRouter API Key
1. Truy cập [https://openrouter.ai](https://openrouter.ai) và đăng nhập (bằng Google hoặc GitHub).
2. Vào mục **Keys**: [https://openrouter.ai/keys](https://openrouter.ai/keys).
3. Nhấn **"Create Key"**, đặt tên cho key và sao chép mã API Key (bắt đầu bằng `sk-or-v1-...`).

---

### 12. Chọn và cấu hình Model OpenRouter
Dự án ưu tiên các model có thể gọi **miễn phí 100%**:
1. Bạn có thể kiểm tra danh sách model miễn phí cập nhật trên: [openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0).
2. Các model miễn phí chất lượng cao đề xuất:
   - `meta-llama/llama-3.3-70b-instruct:free` (Mặc định trong dự án - hiểu tiếng Việt rất tốt).
   - `google/gemini-2.0-flash-exp:free` (Tốc độ phản hồi cực nhanh).
   - `deepseek/deepseek-chat:free` (Phân tích mạch lạc).

---

### 13. Tạo và cấu hình file .env
Tạo file `.env` từ file mẫu:
```powershell
Copy-Item .env.example .env
```
Mở file `.env` bằng Notepad hoặc VSCode và điền thông tin:
```dotenv
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789
TELEGRAM_SESSION_NAME=telegram_user_session
ALLOWED_TELEGRAM_USER_ID=999888777
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

---

### 14. Đăng nhập Telethon lần đầu
Chạy script xác thực độc lập trên PowerShell:
```powershell
python -m app.login
```
Trình đăng nhập sẽ yêu cầu:
1. Nhập số điện thoại kèm mã quốc gia (Ví dụ: `+84912345678`).
2. Nhập mã OTP nhận được trong ứng dụng Telegram.
3. Nhập mật khẩu xác minh 2 bước 2FA (nếu tài khoản có bật).
Sau khi đăng nhập thành công, script sẽ tạo file session `telegram_user_session.session` và in ra User ID của bạn.

---

### 15. Khởi chạy ứng dụng Bot
Chạy bot chính thức:
```powershell
python -m app.main
```
Khi thấy dòng log:
`Telegram Bot đã sẵn sàng nhận lệnh. Đang bắt đầu polling...`
nghĩa là hệ thống đã hoạt động!

---

### 16. Kiểm tra hoạt động của Bot
1. Mở ứng dụng Telegram trên điện thoại hoặc máy tính.
2. Tìm kiếm username của bot bạn đã tạo ở bước 8.
3. Gửi lệnh `/start`.
4. Gửi lệnh `/status` để kiểm tra kết nối Telethon và OpenRouter.
5. Gửi lệnh `/summary` để thử nghiệm tóm tắt tin nhắn!

---

### 17. Chạy bộ kiểm thử tự động
Để kiểm tra tính toàn vẹn của mã nguồn:
```powershell
pytest
```
Tất cả các bài kiểm thử đều sử dụng Mock và không tiêu tốn token AI hay gửi tin nhắn thật ra ngoài.

---

### 18. Xử lý các lỗi phổ biến
Xem tài liệu chi tiết tại: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).
