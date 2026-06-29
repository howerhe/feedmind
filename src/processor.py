import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import google.genai as genai

from src.models import Article, DigestEvent

logger = logging.getLogger(__name__)

# Define schema manually as a pure dictionary to avoid google-genai 0.3.0 SDK bugs
response_schema = {
    "type": "OBJECT",
    "properties": {
        "events": {
            "type": "ARRAY",
            "description": "List of grouped and summarized events.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING", "description": "A concise, engaging title for this grouped news event."},
                    "summary": {"type": "STRING", "description": "A comprehensive but concise paragraph summarizing the event. For forums, include key discussion points."},
                    "source_ids": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "The exact list of article IDs (from the provided input) that belong to this event."
                    }
                },
                "required": ["title", "summary", "source_ids"]
            }
        }
    },
    "required": ["events"]
}

class Processor:
    """Handles interaction with Gemini API for deduplication and summarization."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the Processor with a Gemini API key.

        Args:
            api_key (Optional[str]): The Gemini API key. If not provided, it will look for the GEMINI_API_KEY environment variable.

        Raises:
            ValueError: If the API key is not provided and not found in the environment variables.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it in .env")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-3.5-flash'

    def process(self, topic: str, new_articles: List[Article], past_digests: List[DigestEvent], aggregate: bool, summarize: bool, is_discourse: bool, prompt_instruction: Optional[str] = None) -> List[DigestEvent]:
        """Process new articles based on the topic mode.

        Args:
            topic (str): The name of the topic.
            new_articles (List[Article]): A list of newly fetched articles to process.
            past_digests (List[DigestEvent]): A list of recently generated digests to avoid duplication.
            aggregate (bool): Whether to group similar articles into a single digest event.
            summarize (bool): Whether to use AI for summarization. If False, a simple passthrough is used.
            is_discourse (bool): Whether the articles are from a Discourse forum.
            prompt_instruction (Optional[str]): Custom instructions for the LLM prompt.

        Returns:
            List[DigestEvent]: A list of generated digest events.
        """
        if not new_articles:
            return []

        if not summarize:
            return self._passthrough(new_articles)

        # AI Mode
        return self._ai_summarize(topic, new_articles, past_digests, aggregate, is_discourse, prompt_instruction)

    def _passthrough(self, articles: List[Article]) -> List[DigestEvent]:
        """Simple passthrough without AI summary.

        Args:
            articles (List[Article]): The list of articles to passthrough.

        Returns:
            List[DigestEvent]: A list of DigestEvents corresponding 1-to-1 with the input articles.
        """
        digests = []
        for a in articles:
            digests.append(DigestEvent(
                id=f"pt-{a.id}",
                title=a.title,
                summary_paragraph=a.content[:500] + "..." if len(a.content) > 500 else a.content,
                source_urls=[a.url],
                topic=a.topic,
                published_at=a.published_at,
                image_url=a.image_url
            ))
        return digests

    def _ai_summarize(self, topic: str, new_articles: List[Article], past_digests: List[DigestEvent], aggregate: bool, is_discourse: bool, prompt_instruction: Optional[str] = None) -> List[DigestEvent]:
        """Use AI to group, deduplicate, and summarize articles.

        Args:
            topic (str): The name of the topic.
            new_articles (List[Article]): A list of newly fetched articles.
            past_digests (List[DigestEvent]): A list of recently generated digests.
            aggregate (bool): Whether to group similar articles.
            is_discourse (bool): Whether the articles are from a Discourse forum.
            prompt_instruction (Optional[str]): Custom instructions for the LLM prompt.

        Returns:
            List[DigestEvent]: A list of AI-generated digest events.
        """

        # Bypass AI for system alerts
        alerts = []
        normal_articles = []
        for a in new_articles:
            if a.id.startswith('sys-alert-'):
                alerts.append(DigestEvent(
                    id=a.id,
                    title=a.title,
                    summary_paragraph=a.content,
                    source_urls=[a.url],
                    topic=a.topic,
                    published_at=a.published_at,
                    image_url=a.image_url
                ))
            else:
                normal_articles.append(a)

        if not normal_articles:
            return alerts

        prompt = self._build_prompt(topic, normal_articles, past_digests, aggregate, is_discourse, prompt_instruction)

        try:
            logger.info(f"Calling Gemini API for topic '{topic}' with {len(normal_articles)} new articles...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': response_schema,
                    'temperature': 0.3,
                },
            )

            result_json = json.loads(response.text)

            digests = []
            article_map = {a.id: a for a in new_articles}

            for item in result_json.get('events', []):
                # Ensure we only include valid source URLs
                urls = []
                image_url = None
                for sid in item['source_ids']:
                    if sid in article_map:
                        article = article_map[sid]
                        urls.append(article.url)
                        if article.image_url and not image_url:
                            image_url = article.image_url

                if not urls:
                    continue # Skip if AI hallucinated IDs or there are no sources

                digests.append(DigestEvent(
                    id=f"ai-{uuid.uuid4().hex[:8]}",
                    title=item['title'],
                    summary_paragraph=item['summary'],
                    source_urls=urls,
                    topic=topic,
                    published_at=datetime.now(timezone.utc),
                    image_url=image_url
                ))

            logger.info(f"Successfully generated {len(digests)} digest events for '{topic}'.")
            return alerts + digests

        except Exception as e:
            logger.error(f"Error calling Gemini API for '{topic}': {e}")
            return alerts

    def _build_prompt(self, topic: str, new_articles: List[Article], past_digests: List[DigestEvent], aggregate: bool, is_discourse: bool, prompt_instruction: Optional[str] = None) -> str:
        """Constructs the prompt for the LLM.

        Args:
            topic (str): The name of the topic.
            new_articles (List[Article]): A list of newly fetched articles.
            past_digests (List[DigestEvent]): A list of recently generated digests.
            aggregate (bool): Whether to group similar articles.
            is_discourse (bool): Whether the articles are from a Discourse forum.
            prompt_instruction (Optional[str]): Custom instructions for the LLM prompt.

        Returns:
            str: The constructed prompt string.
        """
        prompt = f"You are an expert news aggregator and summarizer. You are processing news for the topic: '{topic}'.\n\n"

        if past_digests and aggregate:
            prompt += "### RECENTLY PUBLISHED EVENTS (DO NOT REPEAT THESE)\n"
            prompt += "The following events were recently published in our digest. If a new article is just a minor follow-up or duplicate of these, IGNORE IT. Only report on it if there is a significant new development.\n"
            for d in past_digests:
                prompt += f"- TITLE: {d.title}\n  SUMMARY: {d.summary_paragraph}\n\n"

        prompt += "### NEW ARTICLES TO PROCESS\n"
        for a in new_articles:
            # Truncate content to avoid absurdly long prompts
            content_snippet = a.content[:3000]
            prompt += f"<article id=\"{a.id}\">\nTITLE: {a.title}\nCONTENT: {content_snippet}\n</article>\n\n"

        prompt += "### INSTRUCTIONS\n"
        if not aggregate:
            prompt += "1. DO NOT GROUP OR DEDUPLICATE articles. Treat every single NEW ARTICLE as a separate distinct event.\n"
        else:
            prompt += "1. Group the NEW ARTICLES into distinct events/stories.\n"
            prompt += "2. Ignore any articles that are duplicates of each other or duplicates/minor updates to the RECENTLY PUBLISHED EVENTS.\n"

        if prompt_instruction:
            prompt += f"3. {prompt_instruction}\n"
        else:
            prompt += "3. For each distinct event, write an engaging summary paragraph of approximately 300 words (adjust if the original text is very short). You MUST translate and write both the TITLE and SUMMARY strictly in Chinese (简体中文), regardless of the original language of the articles.\n"

        if is_discourse and not prompt_instruction:
            prompt += "4. Since these are forum threads, ensure your summary captures the original post's question/premise AND the general consensus or interesting points from the replies if any.\n"

        prompt += "5. Output a JSON object matching the provided schema, containing the events. Use the exact article `id` in the `source_ids` array.\n"

        return prompt
