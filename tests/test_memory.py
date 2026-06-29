from datetime import datetime, timezone

import pytest

from src.memory import MemoryDB
from src.models import Article, DigestEvent


@pytest.fixture
def db(temp_db_path):
    return MemoryDB(db_path=temp_db_path)

def test_init_db(db):
    assert db is not None

def test_article_exists(db):
    assert db.article_exists("non-existent-id") is False

    now = datetime.now(timezone.utc)
    article = Article(
        id="article-1",
        title="Title",
        url="https://test.com",
        content="Content",
        published_at=now,
        topic="test-topic",
        feed_url="https://test.com/rss"
    )
    db.save_articles([article])

    assert db.article_exists("article-1") is True
    assert db.article_exists("article-2") is False

def test_save_and_get_digests(db):
    now = datetime.now(timezone.utc)
    digest = DigestEvent(
        id="digest-1",
        title="Digest Title",
        summary_paragraph="Summary",
        source_urls=["https://test.com"],
        topic="test-topic",
        published_at=now,
        image_url="https://test.com/img.jpg"
    )
    db.save_digests([digest])

    recent = db.get_recent_digests("test-topic", days=1)
    assert len(recent) == 1
    assert recent[0].id == "digest-1"
    assert recent[0].title == "Digest Title"
    assert recent[0].image_url == "https://test.com/img.jpg"
    assert recent[0].source_urls == [{"url": "https://test.com", "title": "Source"}]

    other_topic = db.get_recent_digests("other-topic", days=1)
    assert len(other_topic) == 0
