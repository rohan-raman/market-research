from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import feedparser
import json

class FetchRSSInput(BaseModel):
    """Input schema for FetchRSSTool."""
    feed_url: str = Field(..., description="The URL of the RSS feed to parse.")
    limit: int = Field(..., description="How many latest articles to retrieve from the feed.")

class FetchRSSTool(BaseTool):
    name: str = "FetchRSSTool"
    description: str = (
        "Fetches the latest N article URLs from a given RSS feed. "
        "Use this tool to gather a list of article links for further scraping."
    )
    args_schema: Type[BaseModel] = FetchRSSInput

    def _run(self, feed_url: str, limit: int) -> str:
        """Fetches latest article URLs from the RSS feed."""
        parsed_feed = feedparser.parse(feed_url)
        # Extract up to 'limit' links
        urls = [entry.link for entry in parsed_feed.entries[:limit]]
        # Return as JSON string
        return json.dumps(urls)