import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List

from src.models import Article, DigestEvent


class MemoryDB:
    """SQLite wrapper for storing fetched articles and past digests."""

    def __init__(self, db_path: str = "rss_memory.db") -> None:
        """Initialize the MemoryDB.

        Args:
            db_path (str): Path to the SQLite database file. Defaults to "rss_memory.db".
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Articles table to track what we've already fetched and processed
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    published_at TIMESTAMP NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Digests table to give AI context on what was already summarized recently
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS digests (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_urls TEXT NOT NULL,
                    published_at TIMESTAMP NOT NULL,
                    image_url TEXT
                )
            ''')

            # Migration to add image_url column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE digests ADD COLUMN image_url TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists

            conn.commit()

    def article_exists(self, article_id: str) -> bool:
        """Check if an article has already been processed.

        Args:
            article_id (str): The unique ID of the article to check.

        Returns:
            bool: True if the article exists in the database, False otherwise.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM articles WHERE id = ?', (article_id,))
            return cursor.fetchone() is not None

    def save_articles(self, articles: List[Article]) -> None:
        """Save new articles to the database.

        Args:
            articles (List[Article]): The list of articles to save.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for article in articles:
                cursor.execute('''
                    INSERT OR IGNORE INTO articles (id, title, url, topic, published_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (article.id, article.title, article.url, article.topic, article.published_at.isoformat()))
            conn.commit()

    def save_digests(self, digests: List[DigestEvent]) -> None:
        """Save generated digests to the database.

        Args:
            digests (List[DigestEvent]): The list of digest events to save.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for digest in digests:
                source_urls_json = json.dumps(digest.source_urls)
                cursor.execute('''
                    INSERT OR IGNORE INTO digests (id, topic, title, summary, source_urls, published_at, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (digest.id, digest.topic, digest.title, digest.summary_paragraph, source_urls_json, digest.published_at.isoformat(), digest.image_url))
            conn.commit()

    def get_recent_digests(self, topic: str, days: int = 3) -> List[DigestEvent]:
        """Fetch recent digests for a specific topic to provide context to the LLM.

        Args:
            topic (str): The topic to fetch digests for.
            days (int): The number of days to look back. Defaults to 3.

        Returns:
            List[DigestEvent]: A list of recent digest events for the given topic.
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, summary, source_urls, published_at, image_url
                FROM digests
                WHERE topic = ? AND published_at >= ?
                ORDER BY published_at DESC
            ''', (topic, cutoff_date))

            results = []
            for row in cursor.fetchall():
                raw_sources = json.loads(row[3])
                parsed_sources = []
                for src in raw_sources:
                    if isinstance(src, str):
                        parsed_sources.append({"url": src, "title": "Source"})
                    else:
                        parsed_sources.append(src)

                results.append(DigestEvent(
                    id=row[0],
                    title=row[1],
                    summary_paragraph=row[2],
                    source_urls=parsed_sources,
                    topic=topic,
                    published_at=datetime.fromisoformat(row[4]),
                    image_url=row[5] if len(row) > 5 else None
                ))
            return results
