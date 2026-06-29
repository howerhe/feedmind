from unittest.mock import MagicMock, patch

import pytest

from src.fetcher import Fetcher


@pytest.fixture
def mock_session():
    with patch('src.fetcher.requests.Session') as mock_session_cls:
        mock_session_inst = MagicMock()
        mock_session_inst.__enter__.return_value = mock_session_inst
        mock_session_cls.return_value = mock_session_inst
        yield mock_session_inst

def test_fetch_feed_success(mock_session):
    # Mock RSS XML response
    mock_response = MagicMock()
    mock_response.content = b"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
    <channel>
      <title>Test Feed</title>
      <link>https://test.com</link>
      <description>A test feed</description>
      <item>
        <title>Test Article 1</title>
        <link>https://test.com/article1</link>
        <description>This is a description.</description>
        <guid>12345</guid>
      </item>
    </channel>
    </rss>
    """
    mock_session.get.return_value = mock_response

    fetcher = Fetcher()
    articles = fetcher.fetch_feed("https://fake.com/rss", "test-topic", is_discourse=False)

    assert len(articles) == 1
    assert articles[0].title == "Test Article 1"
    assert articles[0].url == "https://test.com/article1"
    assert articles[0].id == "12345"
    assert articles[0].topic == "test-topic"

def test_fetch_feed_error(mock_session):
    # Mock error during fetch
    mock_session.get.side_effect = Exception("Connection Error")

    fetcher = Fetcher()
    articles = fetcher.fetch_feed("https://fake.com/rss", "test-topic", is_discourse=False)

    # Should return a system alert article
    assert len(articles) == 1
    assert articles[0].id.startswith("sys-alert-")
    assert "Source Fetch Failed" in articles[0].title
    assert "Connection Error" in articles[0].content

def test_fetch_discourse(mock_session):
    # Setup fetcher with mocked session
    fetcher = Fetcher()
    fetcher.session = mock_session

    # First mock the RSS fetch
    mock_rss_response = MagicMock()
    mock_rss_response.content = b"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
    <channel>
      <item>
        <title>Forum Post</title>
        <link>https://forum.test.com/t/123</link>
        <guid>https://forum.test.com/t/123</guid>
      </item>
    </channel>
    </rss>
    """

    # Second mock the Discourse JSON API fetch
    mock_json_response = MagicMock()
    mock_json_response.status_code = 200
    mock_json_response.json.return_value = {
        "post_stream": {
            "posts": [
                {"username": "user1", "cooked": "<p>Original post</p>"},
                {"username": "user2", "cooked": "<p>Reply</p>"}
            ]
        }
    }

    # side_effect allows different returns for consecutive calls
    mock_session.get.side_effect = [mock_rss_response, mock_json_response]

    articles = fetcher.fetch_feed("https://forum.test.com/latest.rss", "forum-topic", is_discourse=True)

    assert len(articles) == 1
    assert articles[0].title == "Forum Post"
    assert "Original Post by user1:\nOriginal post" in articles[0].content
    assert "Reply by user2:\nReply" in articles[0].content
