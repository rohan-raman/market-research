#!/usr/bin/env python
import json
import os
from typing import List, Dict
from pydantic import BaseModel, Field
from crewai import LLM
from crewai.flow.flow import Flow, listen, start
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource
from market_research_flow.crews.content_crew.content_crew import ContentCrew
from market_research_flow.crews.article_scraper_crew.article_scraper_crew import ArticleScraperCrew
from market_research_flow.tools.fetch_rss_tool import FetchRSSTool
import feedparser

def fetch_article_urls(feed_url: str, limit: int) -> List[str]:
    """
    Procedurally fetch the latest `limit` article URLs from an RSS feed.

    Args:
        feed_url: The RSS feed URL.
        limit: Number of article URLs to return.

    Returns:
        A list of article URLs as strings.
    """
    parsed_feed = feedparser.parse(feed_url)
    urls = [entry.link for entry in parsed_feed.entries[:limit]]
    return urls

# Define our models for structured data
class Section(BaseModel):
    title: str = Field(description="Title of the section")
    description: str = Field(description="Brief description of what the section should cover")
    content: str = Field(description="Content of the section")

# Define our flow state
class ReportCreatorState(BaseModel):
    topic: str = ""
    audience_level: str = ""
    introduction: str = ""
    articles_per_feed: int = 1
    sections: List[Section] = []
    collected_articles: str = ""

class ReportCreatorFlow(Flow[ReportCreatorState]):
    """Flow for creating a comprehensive report on any industry"""

    @start()
    def get_report_input(self):
        print("\n=== Create Your Comprehensive Report ===\n")

        # Load JSON from file
        with open("./knowledge/report_meta.json", "r") as f:
            report_meta = json.load(f)
        sections_dict = {
            section["title"]: section["description"]
            for section in report_meta.get("sections", [])
        }

        # Access the topic field
        self.state.topic = report_meta.get("topic", "AI LLMs")
        self.state.audience_level = report_meta.get("audience_level", "Beginner")
        self.state.introduction = report_meta.get("introduction", "A report")
        self.state.articles_per_feed = report_meta.get("articles_per_feed", "1")
        self.state.sections = [
            Section(
                title=section.get("title", ""),
                description=section.get("description", ""),
                content=""
            )
            for section in report_meta.get("sections", [])
        ]

        print(f"\nCreating a report on {self.state.topic} for {self.state.audience_level} audience...\n")

        return self.state

    @listen(get_report_input)
    def gather_articles(self, state):
        # load feeds
        with open("./knowledge/feeds.json", "r") as f:
            feeds = json.load(f)["rss_feeds"]

        all_articles_text = []

        # step 1: fetch articles for each feed
        for feed_url in feeds:
            article_urls = fetch_article_urls(feed_url, self.state.articles_per_feed)
            # article_urls should be a list
            for article_url in article_urls:
                # step 2: scrape each article
                article_text = ArticleScraperCrew().crew().kickoff(inputs={
                    "url": article_url
                })
                all_articles_text.append(article_text.raw)

        # you can store combined text in state for writing
        state.collected_articles = all_articles_text
        print(state.collected_articles)
        return state


    
    @listen(gather_articles)
    def write_and_compile_report(self, state):
        """Write all sections and compile the report guide"""
        print("Writing report sections and compiling...")
        combined_text = "\n".join(state.collected_articles)

        # Loop through each Section object in the state
        for section in state.sections:
            print(f"Processing section: {section.title}")
            # Kick off your content crew
            result = ContentCrew().crew().kickoff(inputs={
                "section_title": section.title,
                "section_description": section.description,
                "audience_level": state.audience_level,
                "source_text": combined_text
            })

            # ✅ Update the content field on the Section object
            section.content = result.raw
        
            
            # Track completion
            print(f"Section completed: {section.title}")

        report_content = f"# {state.topic}\n\n"
        report_content += f"## Introduction\n\n{state.introduction}\n\n"

        for section in state.sections:
            report_content += f"## {section.title}\n\n{section.content}\n\n"

        # Save the guide
        with open("output/complete_report.md", "w") as f:
            f.write(report_content)

        print("\nComplete report compiled and saved to output/complete_report.md")
        for section in state.sections:
            print(section.content + "\n")
        return "Report creation completed successfully"

def kickoff():
    """Run the report creator flow"""
    ReportCreatorFlow().kickoff()
    print("\n=== Flow Complete ===")
    print("Your comprehensive guide is ready in the output directory.")
    print("Open output/complete_report.md to view it.")

def plot():
    """Generate a visualization of the flow"""
    flow = ReportCreatorFlow()
    flow.plot("report_creator_flow")
    print("Flow visualization saved to report_creator_flow.html")

if __name__ == "__main__":
    kickoff()