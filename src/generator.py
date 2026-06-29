import logging
import os
from datetime import timezone
from typing import Any, Dict, List, Optional

from feedgen.feed import FeedGenerator

from src.models import DigestEvent

logger = logging.getLogger(__name__)

class RSSGenerator:
    """Generates standard RSS XML feeds from DigestEvents."""

    def __init__(self, output_dir: str = "output_feeds") -> None:
        """Initialize the RSSGenerator.

        Args:
            output_dir (str): The directory where the generated XML feeds will be saved. Defaults to "output_feeds".
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, topic_config: Dict[str, Any], digests: List[DigestEvent], all_past_digests: Optional[List[DigestEvent]] = None) -> None:
        """Generates an RSS XML file for the given topic.

        Args:
            topic_config (Dict[str, Any]): The configuration dictionary for the topic.
            digests (List[DigestEvent]): The new digest events to include in the feed.
            all_past_digests (Optional[List[DigestEvent]]): Past digest events to combine for history.
        """
        fg = FeedGenerator()
        topic = topic_config["name"]
        topic_slug = topic.lower().replace(' ', '-')

        fg.id(f"feedmind-{topic_slug}")

        # Custom or Default Title/Description
        title = topic_config.get("title", f"FeedMind: {topic}")
        desc = topic_config.get("description", f"AI-generated digest for {topic}")
        fg.title(title)
        fg.description(desc)
        fg.author({'name': 'FeedMind AI'})

        # Link Fallback Logic
        link = topic_config.get("link")
        feeds = topic_config.get("feeds", [])
        if not link:
            link = feeds[0] if len(feeds) == 1 else "https://github.com/howerhe/feedmind"
        fg.link(href=link, rel='alternate')

        # Logo/Icon
        logo = topic_config.get("logo")
        if logo:
            fg.logo(logo)

        icon = topic_config.get("icon")
        if icon:
            fg.icon(icon)

        fg.language('en')

        # Combine past digests with new ones for the RSS feed, so it has history
        feed_items = []
        if all_past_digests:
            feed_items.extend(all_past_digests)
        feed_items.extend(digests)

        # Sort by published date descending (newest first)
        feed_items.sort(key=lambda x: x.published_at, reverse=True)

        # Limit to the most recent 50 items in the feed
        for digest in feed_items[:50]:
            fe = fg.add_entry()
            fe.id(digest.id)
            fe.title(digest.title)

            # Format the summary and source links as HTML for the RSS reader
            html_content = ""
            if digest.image_url:
                html_content += f'<img src="{digest.image_url}" style="max-width:100%; height:auto;"/><br/><br/>'

            html_content += f"<p>{digest.summary_paragraph}</p>"
            if digest.source_urls:
                html_content += "<ul>"
                for url in digest.source_urls:
                    html_content += f'<li><a href="{url}">Source</a></li>'
                html_content += "</ul>"

            fe.content(html_content, type='html')

            # Make datetime timezone-aware (UTC) for feedgen
            pub_date = digest.published_at.replace(tzinfo=timezone.utc)
            fe.published(pub_date)

            if digest.source_urls:
                fe.link(href=digest.source_urls[0]) # Main link

        filename = f"digest_{topic_slug}.xml"
        filepath = os.path.join(self.output_dir, filename)
        fg.rss_file(filepath)
        logger.info(f"Generated RSS feed: {filepath}")
