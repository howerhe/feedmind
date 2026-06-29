from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Article:
    """Represents a single fetched article or forum thread."""
    id: str  # Unique identifier, usually the URL or GUID
    title: str
    url: str
    content: str  # The original content fetched from RSS or API
    published_at: datetime
    topic: str  # The topic name (e.g., "China News", "US Card Forum Hot")
    feed_url: str
    image_url: Optional[str] = None

@dataclass
class DigestEvent:
    """Represents a grouped and summarized news event to be output as an RSS item."""
    id: str  # A unique ID for this digest event
    title: str  # AI generated title for the event
    summary_paragraph: str  # AI generated summary
    source_urls: List[str]  # List of original article URLs that formed this event
    topic: str
    published_at: datetime
    image_url: Optional[str] = None
