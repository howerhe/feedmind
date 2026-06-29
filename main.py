import argparse
import logging
import os
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from src.fetcher import Fetcher
from src.generator import RSSGenerator
from src.memory import MemoryDB
from src.processor import Processor


def load_config(config_path: str) -> Dict[str, Any]:
    """Load the YAML configuration file.

    Args:
        config_path (str): The path to the YAML configuration file.

    Returns:
        Dict[str, Any]: The parsed configuration data.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main() -> None:
    """Main entry point for the FeedMind AI RSS Aggregator."""
    parser = argparse.ArgumentParser(description="FeedMind AI RSS Aggregator")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Run without calling AI or saving to DB")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    logger = logging.getLogger("FeedMind")

    load_dotenv()

    config = load_config(args.config)
    output_dir = os.environ.get("OUTPUT_DIR", "output_feeds")
    db_path = os.environ.get("DB_PATH", "rss_memory.db")

    if args.dry_run:
        logger.info("--- DRY RUN MODE ---")
        db_path = "dry_run.db" # Use temporary DB for dry run
        if os.path.exists(db_path):
            os.remove(db_path)
        output_dir = "dry_run_output"

    memory = MemoryDB(db_path=db_path)
    fetcher = Fetcher()

    # Initialize processor if not dry run or if API key is provided anyway
    processor = None
    if not args.dry_run or os.environ.get("GEMINI_API_KEY"):
        processor = Processor()

    generator = RSSGenerator(output_dir=output_dir)

    for topic_config in config.get("topics", []):
        topic = topic_config["name"]
        aggregate = topic_config.get("aggregate", True)
        summarize = topic_config.get("summarize", True)
        is_discourse = topic_config.get("is_discourse", False)
        feeds = topic_config["feeds"]

        logger.info(f"========== Processing Topic: {topic} (aggregate={aggregate}, summarize={summarize}) ==========")

        new_articles = []
        for feed_url in feeds:
            articles = fetcher.fetch_feed(feed_url, topic, is_discourse)

            # Deduplicate locally against DB
            for article in articles:
                if not memory.article_exists(article.id):
                    new_articles.append(article)

        logger.info(f"Found {len(new_articles)} new, unprocessed articles.")

        if not new_articles:
            logger.info("Skipping AI processing. Generating feed from history...")
            past_digests = memory.get_recent_digests(topic, days=30) # Fetch up to 30 days for the RSS feed
            generator.generate(topic_config, [], past_digests)
            continue

        if args.dry_run:
            logger.info("[Dry Run] Would process these articles:")
            for a in new_articles:
                logger.info(f" - {a.title}")
            continue

        # Get recent digests for AI context (deduplication)
        past_digests_context = memory.get_recent_digests(topic, days=3) if aggregate else []

        prompt_instruction = topic_config.get("prompt")

        # Process and summarize
        new_digests = processor.process(topic, new_articles, past_digests_context, aggregate, summarize, is_discourse, prompt_instruction)

        if new_digests:
            # Save state
            memory.save_articles(new_articles)
            memory.save_digests(new_digests)

            # Fetch longer history for full RSS generation (this now includes the newly saved digests)
            all_past_digests = memory.get_recent_digests(topic, days=30)

            # Generate RSS (pass [] for new_digests since they are already in all_past_digests)
            generator.generate(topic_config, [], all_past_digests)

    logger.info("FeedMind process completed successfully.")

if __name__ == "__main__":
    main()
