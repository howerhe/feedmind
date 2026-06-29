import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.models import Article
from src.processor import Processor


@pytest.fixture
def mock_genai_client():
    with patch('src.processor.genai.Client') as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client

@pytest.fixture
def new_articles():
    now = datetime.now(timezone.utc)
    return [
        Article(
            id="1",
            title="Article 1",
            url="https://test.com/1",
            content="Content 1",
            published_at=now,
            topic="test-topic",
            feed_url="test.xml"
        ),
        Article(
            id="2",
            title="Article 2",
            url="https://test.com/2",
            content="Content 2",
            published_at=now,
            topic="test-topic",
            feed_url="test.xml"
        )
    ]

def test_processor_init_no_key():
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    with pytest.raises(ValueError, match="GEMINI_API_KEY environment variable is not set"):
        Processor()

def test_processor_passthrough(new_articles):
    processor = Processor(api_key="fake-key")
    digests = processor.process("test-topic", new_articles, [], aggregate=False, summarize=False, is_discourse=False)

    assert len(digests) == 2
    assert digests[0].id.startswith("pt-")
    assert digests[0].title == "Article 1"
    assert digests[1].title == "Article 2"

def test_processor_ai_summarize(mock_genai_client, new_articles):
    processor = Processor(api_key="fake-key")

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "events": [
            {
                "title": "Grouped Event",
                "summary": "This is an AI summary.",
                "source_ids": ["1", "2"]
            }
        ]
    })
    mock_genai_client.models.generate_content.return_value = mock_response

    digests = processor.process("test-topic", new_articles, [], aggregate=True, summarize=True, is_discourse=False)

    assert len(digests) == 1
    assert digests[0].title == "Grouped Event"
    assert digests[0].summary_paragraph == "This is an AI summary."
    assert "https://test.com/1" in digests[0].source_urls
    assert "https://test.com/2" in digests[0].source_urls

    # Verify the LLM was called
    mock_genai_client.models.generate_content.assert_called_once()
