import logging
import os
from collections import defaultdict
from datetime import timedelta, timezone
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
        logo = topic_config.get("logo", "https://howerhe.xyz/feedmind/assets/logo.jpg")
        fg.logo(logo)

        icon = topic_config.get("icon", "https://howerhe.xyz/feedmind/assets/logo.jpg")
        fg.icon(icon)

        fg.language('en')

        # Combine past digests with new ones for the RSS feed, so it has history
        feed_items = []
        if all_past_digests:
            feed_items.extend(all_past_digests)
        feed_items.extend(digests)

        # Group items by PST date and morning/evening run
        grouped_items = defaultdict(list)
        for digest in feed_items:
            pst_time = digest.published_at - timedelta(hours=8)
            date_str = pst_time.strftime('%Y-%m-%d')
            time_label = "早间摘要" if pst_time.hour < 12 else "晚间摘要"
            group_key = f"{date_str}-{time_label}"
            grouped_items[group_key].append(digest)

        # Sort the groups by the most recent article's date descending
        sorted_groups = sorted(
            grouped_items.items(),
            key=lambda item: max(d.published_at for d in item[1]),
            reverse=True
        )

        # Limit to the most recent 50 runs in the feed
        for group_key, digests_in_group in sorted_groups[:50]:
            fe = fg.add_entry()

            date_str, time_label = group_key.rsplit('-', 1)
            fe.title(f"{title} - {date_str} {time_label}")
            fe.id(f"feedmind-{topic_slug}-{group_key}")

            # Concatenate HTML for the group
            html_content = ""
            for digest in digests_in_group:
                html_content += f"<h3>{digest.title}</h3>"
                html_content += f"<p>{digest.summary_paragraph}</p>"

                if digest.image_url:
                    html_content += f'<img src="{digest.image_url}" referrerpolicy="no-referrer" style="max-width:100%; height:auto;"/><br/><br/>'

                if digest.source_urls:
                    html_content += "<ul>"
                    for src in digest.source_urls:
                        if isinstance(src, str):
                            html_content += f'<li><a href="{src}">Source</a></li>'
                        else:
                            html_content += f'<li><a href="{src["url"]}">{src["title"]}</a></li>'
                    html_content += "</ul>"
                html_content += "<hr/>"

            fe.content(html_content, type='html')

            # Make datetime timezone-aware (UTC) for feedgen
            max_pub_date = max(d.published_at for d in digests_in_group)
            fe.published(max_pub_date.replace(tzinfo=timezone.utc))

            if digests_in_group and digests_in_group[0].source_urls:
                first_src = digests_in_group[0].source_urls[0]
                fe.link(href=first_src if isinstance(first_src, str) else first_src["url"]) # Main link fallback

        filename = f"digest_{topic_slug}.xml"
        filepath = os.path.join(self.output_dir, filename)
        fg.rss_file(filepath)
        logger.info(f"Generated RSS feed: {filepath}")
