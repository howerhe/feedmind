import os
from unittest.mock import MagicMock, patch

import pytest
from google.genai.errors import APIError
from openai import APIConnectionError

from src.llm_providers import GeminiProvider, OpenAICompatibleProvider, _is_retryable_error


def test_is_retryable_error_gemini():
    # Test retryable Gemini error
    error_429 = MagicMock(spec=APIError)
    error_429.code = 429
    assert _is_retryable_error(error_429) is True

    # Test non-retryable Gemini error
    error_400 = MagicMock(spec=APIError)
    error_400.code = 400
    assert _is_retryable_error(error_400) is False

def test_is_retryable_error_openai():
    # Test retryable OpenAI error
    req = MagicMock()
    error_conn = APIConnectionError(request=req)
    assert _is_retryable_error(error_conn) is True

    # Test timeout generic
    timeout_error = Exception("Read timeout occurred")
    assert _is_retryable_error(timeout_error) is True

    # Test unknown error
    assert _is_retryable_error(Exception("Unknown")) is False

def test_gemini_provider_init_no_key():
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            GeminiProvider()

def test_gemini_provider_generate_summary():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        with patch('src.llm_providers.genai.Client') as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = '{"events": []}'
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            provider = GeminiProvider()
            result = provider.generate_summary("test prompt", {"type": "OBJECT"})
            assert result == '{"events": []}'
            mock_client.models.generate_content.assert_called_once()

def test_openai_provider_init_no_key():
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY is not set"):
            OpenAICompatibleProvider()

def test_openai_provider_generate_summary():
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "fake_key"}):
        with patch('src.llm_providers.OpenAI') as mock_openai_cls:
            mock_client = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = '{"events": []}'
            mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
            mock_openai_cls.return_value = mock_client

            provider = OpenAICompatibleProvider()
            result = provider.generate_summary("test prompt", {"type": "OBJECT"})
            assert result == '{"events": []}'
            mock_client.chat.completions.create.assert_called_once()
