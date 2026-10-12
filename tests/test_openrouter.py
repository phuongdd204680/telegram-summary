"""Kiểm thử tích hợp OpenRouter Client."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest
from app.ai.openrouter_client import (
    OpenRouterAuthError,
    OpenRouterClient,
    OpenRouterError,
    OpenRouterModelNotFoundError,
    OpenRouterQuotaError,
    OpenRouterRateLimitError,
    OpenRouterServiceError,
    OpenRouterTimeoutError,
)


@pytest.mark.asyncio
async def test_headers_with_optional_fields():
    """Kiểm tra header khi có đầy đủ tùy chọn."""
    client = OpenRouterClient(
        api_key="test_key",
        model="test_model",
        site_url="https://myapp.com",
        app_name="App Name",
    )
    headers = client._build_headers()
    assert headers["Authorization"] == "Bearer test_key"
    assert headers["HTTP-Referer"] == "https://myapp.com"
    assert headers["X-OpenRouter-Title"] == "App Name"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_headers_without_optional_fields():
    """Kiểm tra header không gửi các trường tùy chọn nếu chưa cấu hình."""
    client = OpenRouterClient(
        api_key="test_key",
        model="test_model",
        site_url=None,
        app_name="",
    )
    headers = client._build_headers()
    assert headers["Authorization"] == "Bearer test_key"
    assert "HTTP-Referer" not in headers
    assert "X-OpenRouter-Title" not in headers


@pytest.mark.asyncio
async def test_complete_chat_success():
    """Kiểm tra gọi API thành công và trích xuất nội dung."""
    client = OpenRouterClient(
        api_key="sk-test",
        model="meta-llama/llama-3.3-70b-instruct:free",
    )

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Bản tóm tắt tin nhắn thành công.",
                    }
                }
            ]
        },
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        messages = [{"role": "user", "content": "Hello"}]
        result = await client.complete_chat(messages)

        assert result == "Bản tóm tắt tin nhắn thành công."
        mock_post.assert_awaited_once()

        # Kiểm tra payload gửi lên
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "meta-llama/llama-3.3-70b-instruct:free"
        assert call_kwargs["json"]["messages"] == messages


@pytest.mark.parametrize(
    "status_code, expected_exception",
    [
        (401, OpenRouterAuthError),
        (402, OpenRouterQuotaError),
        (403, OpenRouterAuthError),
        (404, OpenRouterModelNotFoundError),
        (408, OpenRouterTimeoutError),
        (429, OpenRouterRateLimitError),
        (500, OpenRouterServiceError),
    ],
)
@pytest.mark.asyncio
async def test_openrouter_status_errors(status_code, expected_exception):
    """Kiểm tra ánh xạ các mã lỗi HTTP tương ứng từ OpenRouter."""
    client = OpenRouterClient(api_key="sk-test", model="free_model")

    mock_resp = httpx.Response(
        status_code=status_code,
        json={"error": {"message": "Test error"}},
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(expected_exception):
            await client.complete_chat([{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_openrouter_timeout_exception():
    """Kiểm tra xử lý httpx.TimeoutException."""
    client = OpenRouterClient(api_key="sk-test", model="free_model", timeout=1.0)

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")
        with pytest.raises(OpenRouterTimeoutError) as exc_info:
            await client.complete_chat([{"role": "user", "content": "Hi"}])
        assert "timeout" in str(exc_info.value).lower()
