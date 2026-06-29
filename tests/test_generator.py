from datetime import datetime, timezone
import os

from src.generator import RSSGenerator
from src.models import DigestEvent

def test_rss_generator(tmp_path):
    output_dir = tmp_path / "output"
    generator = RSSGenerator(output_dir=str(output_dir))
    
    topic_config = {
        "name": "Test Topic",
        "title": "Custom Title",
        "description": "Custom Description",
        "feeds": ["https://example.com/feed"]
    }
    
    now = datetime.now(timezone.utc)
    digest = DigestEvent(
        id="test-digest-1",
        title="Test Digest",
        summary_paragraph="This is a summary.",
        source_urls=["https://example.com/1"],
        topic="Test Topic",
        published_at=now,
        image_url="https://example.com/image.jpg"
    )
    
    generator.generate(topic_config, digests=[digest], all_past_digests=[])
    
    # Check if file was created
    expected_file = output_dir / "digest_test-topic.xml"
    assert expected_file.exists()
    
    # Verify content
    content = expected_file.read_text(encoding="utf-8")
    assert "Custom Title" in content
    assert "Custom Description" in content
    assert "Test Digest" in content
    assert "This is a summary." in content
    assert "https://example.com/1" in content
    assert "https://example.com/image.jpg" in content
