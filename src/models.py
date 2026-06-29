from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Article:
    """Represents a single fetched article or forum thread."""
    id: str  # Unique identifier, usually the URL or GUID
    title: str
    url: str
    content: str  # Text content for AI summarization
    raw_content: str  # Raw HTML content for passthrough
    published_at: datetime
    topic: str  # The topic name (e.g., "China News", "US Card Forum Hot")
    feed_url: str
    image_url: Optional[str] = None

@dataclass
class DigestEvent:
    """Represents a grouped and summarized news event to be output as an RSS item."""
    id: str  # A unique ID for this digest event
    title: str  # AI generated title for the event
    summary_paragraph: str  # AI generated summary or raw HTML passthrough
    source_urls: List[Dict[str, str]]  # List of dicts with 'url' and 'title'
    topic: str
    published_at: datetime
    image_url: Optional[str] = None
    is_passthrough: bool = False
