#!/usr/bin/env python3
"""Veille GitHub Trending — Récupère les repos IA populaires sur GitHub."""

import asyncio
import datetime
import re
import sys
from pathlib import Path

import httpx

GITHUB_API = "https://api.github.com"
TOPICS = ["llm", "ai-agent", "rag", "mcp", "language-model"]
LANGUAGES = ["python", "typescript", "rust", "go"]
MIN_STARS = 100
OUTPUT_FILE = Path(__file__).parent.parent / "content" / "veille" / "github-hf.qmd"


async def search_repos(client: httpx.AsyncClient, topic: str, language: str) -> list[dict]:
    params = {
        "q": f"topic:{topic} language:{language} stars:>={MIN_STARS}",
        "sort": "stars",
        "order": "desc",
        "per_page": 10,
    }
    resp = await client.get(f"{GITHUB_API}/search/repositories", params=params)
    if resp.status_code != 200:
        return []
    data = resp.json()
    return data.get("items", [])


def generate_markdown(repos: list[dict]) -> str:
    seen = set()
    lines = []
    for repo in repos:
        full_name = repo["full_name"]
        if full_name in seen:
            continue
        seen.add(full_name)

        lines.append(f"### {repo['name']}")
        lines.append(f"- **GitHub** : {full_name}")
        lines.append(f"- **Stars** : {repo['stargazers_count']:,}")
        lines.append(f"- **Langage** : {repo.get('language', 'N/A')}")
        lines.append(f"- **Licence** : {repo.get('license', {}).get('spdx_id', 'N/A') if repo.get('license') else 'N/A'}")
        lines.append(f"- **Description** : {repo.get('description', 'N/A')}")
        lines.append(f"- **Lien** : {repo['html_url']}")
        lines.append("")
    return "\n".join(lines)


def update_qmd(feed_content: str) -> None:
    content = OUTPUT_FILE.read_text(encoding="utf-8")
    pattern = r"(<!-- GITHUB_FEED_START -->)(.*?)(<!-- GITHUB_FEED_END -->)"
    replacement = rf"\1\n{feed_content}\n\3"
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)
    OUTPUT_FILE.write_text(updated, encoding="utf-8")
    print(f"Updated {OUTPUT_FILE}")


async def main() -> None:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = sys.argv[1] if len(sys.argv) > 1 else None
    if token:
        headers["Authorization"] = f"token {token}"

    all_repos = []
    async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True) as client:
        for topic in TOPICS:
            for lang in LANGUAGES:
                repos = await search_repos(client, topic, lang)
                all_repos.extend(repos)

    all_repos.sort(key=lambda r: r["stargazers_count"], reverse=True)
    unique = []
    seen = set()
    for r in all_repos:
        if r["full_name"] not in seen:
            seen.add(r["full_name"])
            unique.append(r)

    top = unique[:30]
    if not top:
        print("No repos found.")
        return

    feed_md = generate_markdown(top)
    update_qmd(feed_md)
    print(f"Found {len(top)} repos.")


if __name__ == "__main__":
    asyncio.run(main())
