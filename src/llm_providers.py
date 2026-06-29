import json
import logging
import os
from abc import ABC, abstractmethod

import google.genai as genai
from google.genai.errors import APIError
from openai import APIConnectionError, InternalServerError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

def _is_retryable_error(exception: Exception) -> bool:
    # Gemini Errors
    if isinstance(exception, APIError):
        status = getattr(exception, 'code', str(exception))
        if "429" in str(status) or "500" in str(status) or "503" in str(status) or "504" in str(status):
            logger.warning(f"Retryable Gemini APIError encountered: {status}")
            return True

    # OpenAI / DeepSeek Errors
    if isinstance(exception, (RateLimitError, APIConnectionError, InternalServerError)):
        logger.warning(f"Retryable OpenAI error encountered: {exception}")
        return True

    if "timeout" in str(exception).lower():
        logger.warning(f"Retryable timeout exception encountered: {exception}")
        return True

    logger.error(f"Non-retryable error or unknown exception: {exception}")
    return False

class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def generate_summary(self, prompt: str, schema: dict) -> str:
        """Generates a summary based on the given prompt and expected JSON schema.

        Args:
            prompt (str): The input prompt for the LLM.
            schema (dict): The expected JSON schema output.

        Returns:
            str: The raw JSON string returned by the LLM.
        """
        pass

class GeminiProvider(BaseProvider):
    """LLM Provider implementation using Google's Gemini API."""

    def __init__(self, api_key: str = None, model_name: str = None):
        """Initialize the Gemini Provider.

        Args:
            api_key (str, optional): The Gemini API key. Defaults to GEMINI_API_KEY env variable.
            model_name (str, optional): The Gemini model name. Defaults to GEMINI_MODEL env variable or gemini-3.5-flash.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=self.api_key, http_options={'timeout': 120})
        self.model_name = model_name or os.environ.get("GEMINI_MODEL") or 'gemini-3.5-flash'

    @retry(retry=retry_if_exception(_is_retryable_error), stop=stop_after_attempt(3), wait=wait_exponential(multiplier=5, min=10, max=60))
    def generate_summary(self, prompt: str, schema: dict) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': schema,
                'temperature': 0.3,
            },
        )
        return response.text

class OpenAICompatibleProvider(BaseProvider):
    """LLM Provider implementation for DeepSeek or any OpenAI-compatible API."""

    def __init__(self, api_key: str = None, model_name: str = None, base_url: str = "https://api.deepseek.com"):
        """Initialize the OpenAI-compatible Provider.

        Args:
            api_key (str, optional): The API key. Defaults to DEEPSEEK_API_KEY env variable.
            model_name (str, optional): The model name. Defaults to DEEPSEEK_MODEL env variable or deepseek-v4-pro.
            base_url (str, optional): The API base URL. Defaults to DeepSeek's API.
        """
        # We default to looking for DEEPSEEK_API_KEY first for convenience, but can be generic
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")

        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=300.0)
        self.model_name = model_name or os.environ.get("DEEPSEEK_MODEL") or 'deepseek-v4-pro'

    @retry(retry=retry_if_exception(_is_retryable_error), stop=stop_after_attempt(3), wait=wait_exponential(multiplier=5, min=10, max=60))
    def generate_summary(self, prompt: str, schema: dict) -> str:
        # For OpenAI compatible JSON mode, we append the schema requirement to the prompt
        enhanced_prompt = prompt + f"\n\nOutput strictly in the following JSON schema format:\n{json.dumps(schema, indent=2)}"

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": enhanced_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return response.choices[0].message.content
