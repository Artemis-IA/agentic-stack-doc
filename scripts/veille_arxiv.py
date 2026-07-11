#!/usr/bin/env python3
"""Veille arXiv — Récupère les derniers papers pertinents pour l'écosystème agentic."""

import asyncio
import datetime
import re
import sys
from pathlib import Path

import httpx

ARXIV_API = "https://export.arxiv.org/api/query"
CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.MA", "cs.SE", "stat.ML"]
KEYWORDS_HIGH = [
    "agent", "agentic", "autonomous", "tool-use", "tool calling",
    "LLM", "language model", "MCP", "model context protocol",
    "RAG", "retrieval augmented", "GraphRAG", "knowledge graph",
    "sandbox", "code agent", "coding assistant",
]
KEYWORDS_MEDIUM = [
    "benchmark", "evaluation", "leaderboard", "GPT", "Claude",
    "Gemini", "Llama", "Mistral", "Qwen", "DeepSeek",
    "vLLM", "SGLang", "Ollama", "inference",
    "GPU", "H100", "B200", "TPU", "Groq",
]
MAX_RESULTS = 50
OUTPUT_FILE = Path(__file__).parent.parent / "content" / "veille" / "arxiv.qmd"


def score_paper(title: str, summary: str) -> int:
    text = (title + " " + summary).lower()
    score = 0
    for kw in KEYWORDS_HIGH:
        if kw.lower() in text:
            score += 3
    for kw in KEYWORDS_MEDIUM:
        if kw.lower() in text:
            score += 1
    return score


def extract_papers(xml_text: str) -> list[dict]:
    papers = []
    entries = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL)
    for entry in entries:
        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        published = re.search(r"<published>(.*?)</published>", entry)
        arxiv_id = re.search(r"<id>http://arxiv.org/abs/(.*?)</id>", entry)
        authors = re.findall(r"<name>(.*?)</name>", entry)

        if not title or not summary:
            continue

        paper = {
            "title": re.sub(r"\s+", " ", title.group(1)).strip(),
            "summary": re.sub(r"\s+", " ", summary.group(1)).strip()[:300],
            "date": published.group(1)[:10] if published else "",
            "arxiv_id": arxiv_id.group(1) if arxiv_id else "",
            "authors": ", ".join(authors[:5]),
            "score": 0,
        }
        paper["score"] = score_paper(paper["title"], paper["summary"])
        if paper["score"] > 0:
            papers.append(paper)

    papers.sort(key=lambda x: x["score"], reverse=True)
    return papers[:20]


def generate_markdown(papers: list[dict]) -> str:
    lines = []
    for p in papers:
        lines.append(f"### {p['title']}")
        lines.append(f"- **arXiv** : {p['arxiv_id']}")
        lines.append(f"- **Date** : {p['date']}")
        lines.append(f"- **Auteurs** : {p['authors']}")
        lines.append(f"- **Score** : {p['score']}")
        lines.append(f"- **Résumé** : {p['summary']}...")
        lines.append(f"- **Lien** : https://arxiv.org/abs/{p['arxiv_id']}")
        lines.append("")
    return "\n".join(lines)


def update_qmd(feed_content: str) -> None:
    content = OUTPUT_FILE.read_text(encoding="utf-8")
    pattern = r"(<!-- ARXIV_FEED_START -->)(.*?)(<!-- ARXIV_FEED_END -->)"
    replacement = rf"\1\n{feed_content}\n\3"
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)
    OUTPUT_FILE.write_text(updated, encoding="utf-8")
    print(f"Updated {OUTPUT_FILE}")


async def main() -> None:
    cat_query = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    params = {
        "search_query": cat_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": MAX_RESULTS,
    }

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(ARXIV_API, params=params)
        resp.raise_for_status()

    papers = extract_papers(resp.text)
    if not papers:
        print("No relevant papers found.")
        return

    feed_md = generate_markdown(papers)
    update_qmd(feed_md)
    print(f"Found {len(papers)} relevant papers.")


if __name__ == "__main__":
    asyncio.run(main())
