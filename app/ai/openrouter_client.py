"""Client gọi OpenRouter Chat Completions API qua httpx.AsyncClient."""

import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Lớp lỗi cơ sở cho các lỗi gọi OpenRouter API."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class OpenRouterAuthError(OpenRouterError):
    """Lỗi xác thực (401) hoặc phân quyền (403)."""
    pass


class OpenRouterQuotaError(OpenRouterError):
    """Lỗi số dư hoặc điều kiện thanh toán (402)."""
    pass


class OpenRouterRateLimitError(OpenRouterError):
    """Lỗi vượt hạn mức tần suất gửi yêu cầu hoặc quota (429)."""
    pass


class OpenRouterModelNotFoundError(OpenRouterError):
    """Lỗi model hoặc endpoint không tồn tại (404)."""
    pass


class OpenRouterTimeoutError(OpenRouterError):
    """Lỗi timeout khi gọi API (408 hoặc httpx.TimeoutException)."""
    pass


class OpenRouterServiceError(OpenRouterError):
    """Lỗi từ phía máy chủ dịch vụ OpenRouter (5xx)."""
    pass


class OpenRouterClient:
    """Client giao tiếp với OpenRouter Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        endpoint: str = "https://openrouter.ai/api/v1/chat/completions",
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.site_url = site_url
        self.app_name = app_name
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _build_headers(self) -> Dict[str, str]:
        """Xây dựng HTTP headers chuẩn cho OpenRouter API.

        Chỉ thêm các header tùy chọn nếu chúng có giá trị.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url and self.site_url.strip():
            headers["HTTP-Referer"] = self.site_url.strip()
        if self.app_name and self.app_name.strip():
            headers["X-OpenRouter-Title"] = self.app_name.strip()
        return headers

    async def get_client(self) -> httpx.AsyncClient:
        """Lấy hoặc khởi tạo HTTP client dùng chung."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Đóng kết nối HTTP client an toàn."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def complete_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = 2000,
    ) -> str:
        """Gửi request chat completions đến OpenRouter.

        Không retry vô hạn, không tự động chuyển model trả phí.
        """
        client = await self.get_client()
        headers = self._build_headers()

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        logger.info("Đang gửi yêu cầu tóm tắt tới OpenRouter với model: %s", self.model)

        # Hỗ trợ tối đa 1 lần retry đối với các lỗi mạng tạm thời hoặc 503/504
        max_attempts = 2
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )

                status = response.status_code

                if status == 200:
                    try:
                        data = response.json()
                    except Exception as json_err:
                        raise OpenRouterError(
                            "Dữ liệu phản hồi từ OpenRouter không đúng định dạng JSON."
                        ) from json_err

                    choices = data.get("choices")
                    if not choices or not isinstance(choices, list) or len(choices) == 0:
                        raise OpenRouterError(
                            "OpenRouter trả về phản hồi rỗng (không có choices)."
                        )

                    first_choice = choices[0]
                    message = first_choice.get("message", {})
                    content = message.get("content", "")

                    if not content:
                        raise OpenRouterError(
                            "Nội dung tóm tắt trong phản hồi từ OpenRouter rỗng."
                        )

                    return str(content).strip()

                # Xử lý các mã lỗi cụ thể
                if status in (401, 403):
                    raise OpenRouterAuthError(
                        "Lỗi xác thực OpenRouter (401/403): Vui lòng kiểm tra lại OPENROUTER_API_KEY.",
                        status_code=status,
                    )
                elif status == 402:
                    raise OpenRouterQuotaError(
                        "Lỗi tài khoản OpenRouter (402): Số dư không đủ hoặc model yêu cầu trả phí.",
                        status_code=status,
                    )
                elif status == 404:
                    raise OpenRouterModelNotFoundError(
                        f"Lỗi OpenRouter (404): Model '{self.model}' hoặc endpoint không tồn tại.",
                        status_code=status,
                    )
                elif status == 408:
                    raise OpenRouterTimeoutError(
                        "Lỗi OpenRouter (408): Yêu cầu bị timeout ở phía máy chủ AI.",
                        status_code=status,
                    )
                elif status == 429:
                    raise OpenRouterRateLimitError(
                        "Lỗi OpenRouter (429): Quá giới hạn tần suất yêu cầu (Rate Limit). Vui lòng thử lại sau.",
                        status_code=status,
                    )
                elif 500 <= status < 600:
                    if attempt < max_attempts:
                        logger.warning(
                            "OpenRouter gặp lỗi máy chủ %s ở lần thử %s. Đang thử lại...",
                            status,
                            attempt,
                        )
                        continue
                    raise OpenRouterServiceError(
                        f"Lỗi máy chủ OpenRouter ({status}): Dịch vụ đang gặp sự cố tạm thời.",
                        status_code=status,
                    )
                else:
                    # Lỗi 400 hoặc mã lỗi khác
                    err_detail = ""
                    try:
                        err_body = response.json()
                        err_detail = err_body.get("error", {}).get("message", "")
                    except Exception:
                        pass
                    msg = f"Lỗi yêu cầu OpenRouter ({status})"
                    if err_detail:
                        msg += f": {err_detail}"
                    raise OpenRouterError(msg, status_code=status)

            except httpx.TimeoutException as te:
                if attempt < max_attempts:
                    logger.warning("Timeout kết nối tới OpenRouter ở lần thử %s. Đang thử lại...", attempt)
                    continue
                raise OpenRouterTimeoutError(
                    f"Kết nối tới OpenRouter bị timeout sau {self.timeout} giây. Vui lòng thử lại sau."
                ) from te
            except httpx.RequestError as re:
                if attempt < max_attempts:
                    logger.warning("Lỗi mạng khi gọi OpenRouter ở lần thử %s: %s", attempt, str(re))
                    continue
                raise OpenRouterError(
                    "Không thể kết nối đến OpenRouter. Vui lòng kiểm tra kết nối mạng."
                ) from re
            except OpenRouterError:
                # Không bắt lại và retry với các lỗi nghiệp vụ 4xx
                raise
            except Exception as e:
                last_error = e
                break

        if last_error:
            raise OpenRouterError(f"Lỗi không xác định khi gọi OpenRouter: {last_error}")
        raise OpenRouterError("Không thể hoàn thành yêu cầu tới OpenRouter.")
