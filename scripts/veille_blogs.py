#!/usr/bin/env python3
"""Veille Blogs & Newsletters — Récupère les articles via flux RSS."""

import asyncio
import re
import sys
from pathlib import Path

import feedparser
import httpx

OUTPUT_FILE = Path(__file__).parent.parent / "content" / "veille" / "blogs.qmd"

FEEDS = [
    ("latent.space", "https://latent.space/feed"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("Anthropic Blog", "https://www.anthropic.com/news/rss.xml"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("TLDR AI", "https://tldr.tech/ai/rss"),
    ("The Batch", "https://deeplearning.ai/the-batch/feed/"),
    ("Last Week in AI", "https://lastweekin.ai/feed"),
]

KEYWORDS = [
    "agent", "agentic", "LLM", "GPT", "Claude", "Gemini", "Llama",
    "Mistral", "Qwen", "DeepSeek", "RAG", "GraphRAG", "MCP",
    "model context protocol", "sandbox", "code agent", "benchmark",
    "vLLM", "Ollama", "inference", "GPU", "tool calling",
]


def score_article(title: str, summary: str) -> int:
    text = (title + " " + summary).lower()
    score = 0
    for kw in KEYWORDS:
        if kw.lower() in text:
            score += 1
    return score


async def fetch_feed(client: httpx.AsyncClient, name: str, url: str) -> list[dict]:
    try:
        resp = await client.get(url, follow_redirects=True)
        feed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return []

    articles = []
    for entry in feed.entries[:10]:
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))[:300]
        link = entry.get("link", "")
        published = entry.get("published", entry.get("updated", ""))[:16]

        score = score_article(title, summary)
        if score > 0:
            articles.append({
                "source": name,
                "title": title,
                "summary": re.sub(r"<[^>]+>", "", summary).strip()[:200],
                "link": link,
                "date": published,
                "score": score,
            })
    return articles


def generate_markdown(articles: list[dict]) -> str:
    articles.sort(key=lambda x: x["score"], reverse=True)
    lines = []
    for a in articles[:25]:
        lines.append(f"### {a['title']}")
        lines.append(f"- **Source** : {a['source']}")
        lines.append(f"- **Date** : {a['date']}")
        lines.append(f"- **Score** : {a['score']}")
        lines.append(f"- **Résumé** : {a['summary']}...")
        lines.append(f"- **Lien** : {a['link']}")
        lines.append("")
    return "\n".join(lines)


def update_qmd(feed_content: str) -> None:
    content = OUTPUT_FILE.read_text(encoding="utf-8")
    pattern = r"(<!-- BLOG_FEED_START -->)(.*?)(<!-- BLOG_FEED_END -->)"
    replacement = rf"\1\n{feed_content}\n\3"
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)
    OUTPUT_FILE.write_text(updated, encoding="utf-8")
    print(f"Updated {OUTPUT_FILE}")


async def main() -> None:
    all_articles = []
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [fetch_feed(client, name, url) for name, url in FEEDS]
        results = await asyncio.gather(*tasks)
        for articles in results:
            all_articles.extend(articles)

    if not all_articles:
        print("No relevant articles found.")
        return

    feed_md = generate_markdown(all_articles)
    update_qmd(feed_md)
    print(f"Found {len(all_articles)} relevant articles.")


if __name__ == "__main__":
    asyncio.run(main())
