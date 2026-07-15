import argparse
import logging
import os
import shutil
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
        is_1point3acres = topic_config.get("is_1point3acres", False)
        feeds = topic_config["feeds"]

        logger.info(f"========== Processing Topic: {topic} (aggregate={aggregate}, summarize={summarize}) ==========")

        new_articles = []
        for feed_url in feeds:
            articles = fetcher.fetch_feed(feed_url, topic, is_discourse=is_discourse, is_1point3acres=is_1point3acres)

            # Deduplicate locally against DB
            for article in articles:
                if not memory.article_exists(article.id):
                    new_articles.append(article)

        alerts_count = len([a for a in new_articles if a.id.startswith("sys-alert-")])
        normal_count = len(new_articles) - alerts_count
        logger.info(f"Found {len(new_articles)} new items ({normal_count} normal articles, {alerts_count} system alerts).")

        if not new_articles:
            logger.info("Skipping AI processing. Generating feed from history...")
            past_digests = memory.get_recent_digests(topic, days=30) # Fetch up to 30 days for the RSS feed
            generator.generate(topic_config, [], past_digests)
            continue

        if args.dry_run:
            logger.info("[Dry Run] Would process these articles:")
            for a in new_articles:
                logger.info(f" - TITLE: {a.title}")
                snippet = a.content.replace('\n', ' ')[:200]
                logger.info(f"   CONTENT PREVIEW: {snippet}...\n")
            continue

        # Get recent digests for AI context (deduplication)
        past_digests_context = memory.get_recent_digests(topic, days=3) if aggregate else []

        prompt_instruction = topic_config.get("prompt")

        # Process and summarize
        new_digests, successful_articles = processor.process(topic, new_articles, past_digests_context, aggregate, summarize, is_discourse or is_1point3acres, prompt_instruction)

        if new_digests:
            # Save state
            memory.save_articles(successful_articles)
            memory.save_digests(new_digests)

            # Fetch longer history for full RSS generation (this now includes the newly saved digests)
            all_past_digests = memory.get_recent_digests(topic, days=30)

            # Generate RSS (pass [] for new_digests since they are already in all_past_digests)
            generator.generate(topic_config, [], all_past_digests)

    # Ensure assets directory exists in output_feeds
    assets_src = "assets"
    assets_dest = os.path.join(output_dir, "assets")
    if os.path.exists(assets_src):
        os.makedirs(assets_dest, exist_ok=True)
        for item in os.listdir(assets_src):
            s = os.path.join(assets_src, item)
            d = os.path.join(assets_dest, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)

    # Generate Landing Page
    topics_html = ""
    for topic_config in config.get("topics", []):
        topic_name = topic_config["name"]
        topic_slug = topic_name.lower().replace(' ', '-')
        xml_file = f"digest_{topic_slug}.xml"
        topics_html += f'''
            <a href="{xml_file}" class="feed-card">
                <h2>{topic_name}</h2>
                <p>{topic_config.get('description', '')}</p>
                <div class="rss-link">Subscribe to RSS</div>
            </a>
        '''

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FeedMind - AI RSS Aggregator</title>
    <link rel="icon" href="assets/favicon.jpg">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --text-color: #f8fafc;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --accent: #3b82f6;
            --accent-hover: #60a5fa;
        }}
        body {{
            margin: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }}
        .container {{
            max-width: 800px;
            width: 90%;
            margin: 4rem auto;
            text-align: center;
        }}
        .logo {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            margin-bottom: 1rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        p.subtitle {{
            font-size: 1.2rem;
            color: #94a3b8;
            margin-bottom: 3rem;
        }}
        .feeds-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
        }}
        .feed-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            text-decoration: none;
            color: inherit;
            text-align: left;
            transition: transform 0.2s, box-shadow 0.2s, background 0.2s;
            backdrop-filter: blur(10px);
        }}
        .feed-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0,0,0,0.4);
            background: rgba(45, 55, 72, 0.9);
            border-color: var(--accent);
        }}
        .feed-card h2 {{
            margin-top: 0;
            margin-bottom: 0.5rem;
            font-size: 1.25rem;
        }}
        .feed-card p {{
            color: #cbd5e1;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }}
        .rss-link {{
            display: inline-block;
            background: var(--accent);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 600;
        }}
        .feed-card:hover .rss-link {{
            background: var(--accent-hover);
        }}
    </style>
</head>
<body>
    <div class="container">
        <img src="assets/logo.jpg" alt="FeedMind Logo" class="logo">
        <h1>FeedMind</h1>
        <p class="subtitle">An intelligent, AI-powered RSS aggregator and summarizer.</p>

        <div class="feeds-grid">
            {topics_html}
        </div>
    </div>
</body>
</html>
"""
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_template)
    logger.info("Generated landing page index.html")

    logger.info("FeedMind process completed successfully.")

if __name__ == "__main__":
    main()
