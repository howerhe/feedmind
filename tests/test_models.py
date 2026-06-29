from datetime import datetime, timezone

from src.models import Article, DigestEvent


def test_article_creation():
    now = datetime.now(timezone.utc)
    article = Article(
        id="test-id",
        title="Test Title",
        url="https://example.com/test",
        content="Test content",
        published_at=now,
        topic="tech",
        feed_url="https://example.com/rss",
    )
    assert article.id == "test-id"
    assert article.title == "Test Title"
    assert article.topic == "tech"
    assert article.image_url is None

def test_digest_event_creation():
    now = datetime.now(timezone.utc)
    digest = DigestEvent(
        id="digest-id",
        title="Digest Title",
        summary_paragraph="Summary",
        source_urls=["https://example.com/1", "https://example.com/2"],
        topic="tech",
        published_at=now,
    )
    assert digest.id == "digest-id"
    assert len(digest.source_urls) == 2
