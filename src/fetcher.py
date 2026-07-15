import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

import feedparser
from bs4 import BeautifulSoup
from curl_cffi import requests

from src.models import Article

logger = logging.getLogger(__name__)

class Fetcher:
    """Fetches and parses RSS feeds and Discourse JSON APIs."""

    def __init__(self) -> None:
        """Initialize the Fetcher with custom headers. Session is created per request to allow browser rotation."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
            'Accept': 'application/rss+xml, application/rdf+xml, application/atom+xml, application/xml, text/xml, text/html, */*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def fetch_feed(self, feed_url: str, topic: str, is_discourse: bool = False, is_1point3acres: bool = False) -> List[Article]:
        """Fetches a feed and parses it into Article objects.

        Args:
            feed_url (str): The URL of the RSS feed.
            topic (str): The name of the topic being processed.
            is_discourse (bool): Whether the feed is from a Discourse forum.
            is_1point3acres (bool): Whether the feed is from 1point3acres.

        Returns:
            List[Article]: A list of parsed Article objects. Returns a system alert Article if the fetch fails.
        """
        logger.info(f"Fetching {feed_url} for topic '{topic}'...")
        if is_1point3acres:
            return self._scrape_1point3acres_hot(topic)

        try:
            # Try with chrome124 first
            with requests.Session(impersonate="chrome124") as session:
                resp = session.get(feed_url, timeout=15)
                if resp.status_code == 403:
                    # Fallback to Safari if Chrome fingerprint is blocked
                    logger.warning(f"Got 403 for {feed_url} with Chrome. Retrying with Safari...")
                    with requests.Session(impersonate="safari17_0") as fallback_session:
                        resp = fallback_session.get(feed_url, timeout=15)
                        resp.raise_for_status()
                else:
                    resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as e:
            err_msg = f"Failed to fetch {feed_url}: {str(e)}"
            logger.error(err_msg)
            alert = Article(
                id=f"sys-alert-{int(time.time())}-{feed_url}",
                title=f"[FeedMind Alert] Source Fetch Failed: {topic}",
                url=feed_url,
                content=err_msg,
                raw_content=f"<p>{err_msg}</p>",
                published_at=datetime.now(timezone.utc),
                topic=topic,
                feed_url=feed_url,
                image_url=None
            )
            return [alert]

        articles = []

        for entry in parsed.entries:
            # Safely get ID (guid or link)
            article_id = getattr(entry, 'id', getattr(entry, 'link', ''))
            if not article_id:
                continue

            title = getattr(entry, 'title', 'No Title')
            link = getattr(entry, 'link', article_id)

            # Extract content: prefer 'content', fallback to 'summary', then ''
            content_html = ''
            if hasattr(entry, 'content'):
                content_html = entry.content[0].value
            elif hasattr(entry, 'summary'):
                content_html = entry.summary

            content_text = self._html_to_text(content_html)

            # Extract image
            image_url = self._extract_image(entry, content_html)

            # Parse published date
            published_at = datetime.now(timezone.utc)
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))

            # If discourse mode, fetch additional context from JSON API
            if is_discourse:
                thread_content = self._fetch_discourse_thread(link)
                if thread_content:
                    content_text = thread_content

            article = Article(
                id=article_id,
                title=title,
                url=link,
                content=content_text,
                raw_content=content_html,
                published_at=published_at,
                topic=topic,
                feed_url=feed_url,
                image_url=image_url
            )
            articles.append(article)

        return articles

    def _scrape_1point3acres_hot(self, topic: str) -> List[Article]:
        """Scrape the 1point3acres hot guide directly to bypass RSSHub Cloudflare blocks."""
        url = "https://www.1point3acres.com/bbs/forum.php?mod=guide&view=hot"
        logger.info(f"Scraping 1point3acres hot guide for topic '{topic}'...")
        try:
            with requests.Session(impersonate="chrome124") as session:
                resp = session.get(url, timeout=15)
                if resp.status_code == 403:
                    with requests.Session(impersonate="safari17_0") as fallback_session:
                        resp = fallback_session.get(url, timeout=15)
                        resp.raise_for_status()
                else:
                    resp.raise_for_status()

            soup = BeautifulSoup(resp.content, "html.parser")
            articles = []
            threads = soup.find_all("th", class_="common")

            # Limit to top 30 to avoid getting banned when fetching threads
            for th in threads[:30]:
                a_tag = th.find("a", class_="xst")
                if not a_tag:
                    continue

                title = a_tag.text
                href = a_tag.get('href', '')
                if not href:
                    continue

                # Convert relative to absolute
                if not href.startswith("http"):
                    link = f"https://www.1point3acres.com/bbs/{href}"
                else:
                    link = href

                article_id = link
                published_at = datetime.now(timezone.utc)

                thread_content = self._fetch_1point3acres_thread(link)
                if not thread_content:
                    continue

                article = Article(
                    id=article_id,
                    title=title,
                    url=link,
                    content=thread_content,
                    raw_content=f"<p>{title}</p>", # Placeholder for raw html
                    published_at=published_at,
                    topic=topic,
                    feed_url=url,
                    image_url=None
                )
                articles.append(article)
            return articles
        except Exception as e:
            err_msg = f"Failed to scrape 1point3acres hot threads: {str(e)}"
            logger.error(err_msg)
            alert = Article(
                id=f"sys-alert-{int(time.time())}-{url}",
                title=f"[FeedMind Alert] Source Fetch Failed: {topic}",
                url=url,
                content=err_msg,
                raw_content=f"<p>{err_msg}</p>",
                published_at=datetime.now(timezone.utc),
                topic=topic,
                feed_url=url,
                image_url=None
            )
            return [alert]

    def _extract_image(self, entry: feedparser.FeedParserDict, content_html: str) -> Optional[str]:
        """Extract the best image URL from the RSS entry or HTML content.

        Args:
            entry (feedparser.FeedParserDict): The parsed RSS entry.
            content_html (str): The HTML content of the entry.

        Returns:
            Optional[str]: The URL of the extracted image, or None if no image is found.
        """
        # 1. Check HTML content for <img> tags first (usually more reliable than enclosures for actual content)
        if content_html:
            soup = BeautifulSoup(content_html, 'html.parser')
            for img in soup.find_all('img'):
                src = img.get('src')
                if not src:
                    continue

                # Filter out obvious tracking pixels (1x1)
                width = img.get('width', '')
                height = img.get('height', '')
                if width == '1' or height == '1':
                    continue

                # Skip known broken/proxy domains if possible
                if 'plink.anyfeeder.com' in src:
                    continue

                return src

        # 2. Check media_content or enclosures if no valid img tags found
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if 'url' in media and media.get('medium') == 'image':
                    return media['url']

        if hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if 'type' in enclosure and enclosure['type'].startswith('image/'):
                    return enclosure.get('href', '')

        return None

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text.

        Args:
            html (str): The HTML string to convert.

        Returns:
            str: The extracted plain text.
        """
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)

    def _fetch_discourse_thread(self, topic_url: str) -> str:
        """Attempt to fetch a Discourse topic's JSON and extract OP + replies.

        Args:
            topic_url (str): The URL of the Discourse topic.

        Returns:
            str: The concatenated text of the original post and top replies.
        """
        try:
            # Discourse API is available by appending .json to the topic URL
            json_url = f"{topic_url}.json"

            with requests.Session(impersonate="chrome124") as session:
                resp = session.get(json_url, timeout=10)
                if resp.status_code == 403:
                    with requests.Session(impersonate="safari17_0") as fallback_session:
                        resp = fallback_session.get(json_url, timeout=10)

            if resp.status_code != 200:
                return ""

            data = resp.json()
            post_stream = data.get('post_stream', {})
            posts = post_stream.get('posts', [])

            if not posts:
                return ""

            # Extract the original post and top a few replies to give context
            texts = []
            for i, post in enumerate(posts[:15]): # Limit to first 15 posts
                author = post.get('username', 'User')
                cooked = post.get('cooked', '')
                text = self._html_to_text(cooked)
                if i == 0:
                    texts.append(f"Original Post by {author}:\n{text}")
                else:
                    texts.append(f"Reply by {author}:\n{text}")

            return "\n\n---\n\n".join(texts)

        except Exception as e:
            logger.warning(f"Failed to fetch discourse thread for {topic_url}: {e}")
            return ""

    def _fetch_1point3acres_thread(self, topic_url: str) -> str:
        """Attempt to fetch a 1point3acres topic and extract OP + replies.

        Args:
            topic_url (str): The URL of the topic (e.g. instant.1point3acres.com/thread/xxx or bbs url).

        Returns:
            str: The concatenated text of the original post and top replies.
        """
        try:
            import re

            # Extract thread ID
            thread_id_match = re.search(r'thread[/-](\d+)', topic_url)
            if not thread_id_match:
                return ""

            thread_id = thread_id_match.group(1)
            bbs_url = f"https://www.1point3acres.com/bbs/thread-{thread_id}-1-1.html"

            with requests.Session(impersonate="chrome124") as session:
                resp = session.get(bbs_url, timeout=15)
                if resp.status_code == 403:
                    with requests.Session(impersonate="safari17_0") as fallback_session:
                        resp = fallback_session.get(bbs_url, timeout=15)

            if resp.status_code != 200:
                return ""

            soup = BeautifulSoup(resp.content, 'html.parser')
            posts = soup.find_all('td', class_='t_f')

            if not posts:
                return ""

            texts = []
            for i, post in enumerate(posts[:15]): # Limit to 15 posts
                text = post.get_text(separator='\n', strip=True)
                # Clean up login banner
                text = re.sub(r'注册一亩三分地论坛，查看更多干货！\n您需要\s*登录\s*才可以下载或查看附件。没有帐号？\s*注册账号\s*x\n', '', text)

                if i == 0:
                    texts.append(f"Original Post:\n{text}")
                else:
                    texts.append(f"Reply:\n{text}")

            return "\n\n---\n\n".join(texts)

        except Exception as e:
            logger.warning(f"Failed to fetch 1point3acres thread for {topic_url}: {e}")
            return ""
