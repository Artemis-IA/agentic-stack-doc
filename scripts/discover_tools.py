#!/usr/bin/env python3
"""Discover AI tools and frameworks from multiple sources dynamically.

Sources:
- GitHub: topic-based search (ai-agent, llm, mcp, rag, sandbox, coding-assistant, etc.)
- Hugging Face: trending models, spaces
- Awesome lists: parse curated GitHub awesome-lists
- PyPI: AI-related packages
- npm: AI-related packages

Output: data/tools.json — a structured database of discovered tools.
"""

import asyncio
import datetime
import json
import re
import sys
from pathlib import Path

import httpx

DATA_FILE = Path(__file__).parent.parent / "data" / "tools.json"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─── GitHub Discovery ───────────────────────────────────────────────────────

GITHUB_API = "https://api.github.com"

GITHUB_TOPICS = {
    "harness": ["ai-coding", "coding-assistant", "ai-ide", "code-agent", "pair-programming"],
    "sandbox": ["sandbox", "code-sandbox", "microvm", "wasm-runtime", "code-execution"],
    "framework": ["ai-agent", "multi-agent", "agent-framework", "llm-framework", "agentic"],
    "llm": ["llm", "language-model", "text-generation", "inference-engine", "llm-serving"],
    "rag": ["rag", "graphrag", "retrieval-augmented-generation", "knowledge-graph-rag"],
    "mcp": ["mcp", "model-context-protocol", "mcp-server", "mcp-client"],
    "skill": ["tool-use", "function-calling", "ai-tools", "agent-tools"],
    "hardware": ["gpu", "inference", "llm-inference", "tensor-compiler", "gpu-kernel"],
}

AWESOME_LISTS = {
    "framework": [
        "https://raw.githubusercontent.com/e2b-dev/awesome-ai-agents/main/README.md",
        "https://raw.githubusercontent.com/kyrolabs/awesome-agents/main/README.md",
    ],
    "llm": [
        "https://raw.githubusercontent.com/Hannibal046/awesome-llm/main/README.md",
        "https://raw.githubusercontent.com/mallorbc/awesome-llm/main/README.md",
    ],
    "mcp": [
        "https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/main/README.md",
        "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/README.md",
    ],
    "rag": [
        "https://raw.githubusercontent.com/jamesmartinelli/awesome_rag/main/README.md",
    ],
    "harness": [
        "https://raw.githubusercontent.com/sdmonti/awesome-ai-coding-assistants/main/README.md",
    ],
}

PYPI_SEARCH_TERMS = ["ai-agent", "llm-framework", "mcp-server", "rag", "code-sandbox"]
NPM_SEARCH_TERMS = ["ai-agent", "llm", "mcp-server", "ai-coding"]


async def github_search(client: httpx.AsyncClient, topic: str, category: str, token: str | None = None) -> list[dict]:
    """Search GitHub repos by topic."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "q": f"topic:{topic} stars:>=50",
        "sort": "stars",
        "order": "desc",
        "per_page": 15,
    }
    resp = await client.get(f"{GITHUB_API}/search/repositories", params=params, headers=headers)
    if resp.status_code != 200:
        return []
    items = resp.json().get("items", [])
    tools = []
    for item in items:
        tools.append({
            "name": item["name"],
            "full_name": item["full_name"],
            "description": item.get("description", ""),
            "url": item["html_url"],
            "stars": item["stargazers_count"],
            "language": item.get("language"),
            "license": item.get("license", {}).get("spdx_id") if item.get("license") else None,
            "topics": item.get("topics", []),
            "updated_at": item.get("updated_at", ""),
            "category": category,
            "source": "github",
        })
    return tools


def parse_awesome_list(markdown: str, category: str) -> list[dict]:
    """Parse an awesome-list markdown to extract GitHub repos."""
    tools = []
    # Match lines starting with - or * that contain a GitHub link
    pattern = r"^[-*]\s+\[([^\]]+)\]\(https://github\.com/([^/)]+/[^/)]+)\)(.*)$"
    for match in re.finditer(pattern, markdown, re.MULTILINE):
        link_text = match.group(1).strip()
        full_name = match.group(2).strip()
        rest = match.group(3).strip()
        # Use the repo name (second part of full_name) as the tool name
        # unless the link text is more descriptive
        repo_name = full_name.split("/")[-1]
        # If link text is generic (GitHub, Repo, etc.), use repo name
        if link_text.lower() in ("github", "repo", "repository", "source", "home", "project"):
            name = repo_name
        else:
            name = link_text
        # Clean description: remove additional markdown links from rest
        desc = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", rest)
        desc = re.sub(r"^[—\-:]\s*", "", desc).strip()
        # Skip if description is just more link texts
        if desc and len(desc) < 3:
            desc = ""
        tools.append({
            "name": name,
            "full_name": full_name,
            "description": desc,
            "url": f"https://github.com/{full_name}",
            "stars": 0,
            "language": None,
            "license": None,
            "topics": [],
            "updated_at": "",
            "category": category,
            "source": "awesome-list",
        })
    return tools


async def fetch_awesome_lists(client: httpx.AsyncClient) -> list[dict]:
    """Fetch and parse awesome lists."""
    all_tools = []
    for category, urls in AWESOME_LISTS.items():
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    tools = parse_awesome_list(resp.text, category)
                    all_tools.extend(tools)
                    print(f"  awesome-list: {url} → {len(tools)} tools")
            except Exception as e:
                print(f"  awesome-list error: {url} → {e}")
    return all_tools


async def search_pypi(client: httpx.AsyncClient, term: str) -> list[dict]:
    """Search PyPI for AI-related packages."""
    try:
        resp = await client.get(
            "https://pypi.org/simple/",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            params={"q": term},
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        projects = data.get("projects", [])[:10]
        tools = []
        for p in projects:
            name = p.get("name", "")
            if name:
                tools.append({
                    "name": name,
                    "full_name": name,
                    "description": "",
                    "url": f"https://pypi.org/project/{name}/",
                    "stars": 0,
                    "language": "Python",
                    "license": None,
                    "topics": [],
                    "updated_at": "",
                    "category": "framework",
                    "source": "pypi",
                })
        return tools
    except Exception:
        return []


async def search_npm(client: httpx.AsyncClient, term: str) -> list[dict]:
    """Search npm for AI-related packages."""
    try:
        resp = await client.get(
            "https://registry.npmjs.org/-/v1/search",
            params={"text": term, "size": 10},
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        tools = []
        for obj in data.get("objects", []):
            pkg = obj.get("package", {})
            name = pkg.get("name", "")
            desc = pkg.get("description", "")
            if name and any(kw in (name + desc).lower() for kw in ["ai", "llm", "agent", "mcp", "rag"]):
                tools.append({
                    "name": name,
                    "full_name": name,
                    "description": desc,
                    "url": pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{name}"),
                    "stars": 0,
                    "language": "TypeScript",
                    "license": pkg.get("license"),
                    "topics": pkg.get("keywords", []),
                    "updated_at": pkg.get("date", ""),
                    "category": "framework",
                    "source": "npm",
                })
        return tools
    except Exception:
        return []


async def enrich_with_github_stars(client: httpx.AsyncClient, tools: list[dict], token: str | None = None) -> list[dict]:
    """Enrich awesome-list tools with GitHub stars if they're GitHub repos."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    sem = asyncio.Semaphore(10)

    async def fetch_one(tool: dict) -> dict:
        if tool.get("source") != "awesome-list" or not tool.get("full_name") or "/" not in tool["full_name"]:
            return tool
        async with sem:
            try:
                resp = await client.get(
                    f"{GITHUB_API}/repos/{tool['full_name']}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tool["stars"] = data.get("stargazers_count", 0)
                    tool["language"] = data.get("language")
                    tool["license"] = data.get("license", {}).get("spdx_id") if data.get("license") else None
                    tool["updated_at"] = data.get("updated_at", "")
                    tool["topics"] = data.get("topics", [])
                    if not tool["description"]:
                        tool["description"] = data.get("description", "")
            except Exception:
                pass
            return tool

    return await asyncio.gather(*[fetch_one(t) for t in tools])


def deduplicate(tools: list[dict]) -> list[dict]:
    """Deduplicate tools by full_name or name, keeping the one with most info."""
    seen = {}
    for tool in tools:
        key = tool.get("full_name", tool["name"]).lower()
        if key not in seen:
            seen[key] = tool
        else:
            existing = seen[key]
            if tool["stars"] > existing["stars"]:
                seen[key] = tool
            elif tool["description"] and not existing["description"]:
                seen[key]["description"] = tool["description"]
    return list(seen.values())


def categorize_by_topics(tools: list[dict]) -> list[dict]:
    """Refine category based on topics."""
    topic_map = {
        "harness": {"coding-assistant", "ai-ide", "code-agent", "pair-programming", "ai-coding"},
        "sandbox": {"sandbox", "code-sandbox", "microvm", "wasm", "code-execution"},
        "framework": {"ai-agent", "multi-agent", "agent-framework", "llm-framework", "agentic"},
        "llm": {"llm", "language-model", "text-generation", "inference", "llm-serving"},
        "rag": {"rag", "graphrag", "retrieval-augmented", "knowledge-graph"},
        "mcp": {"mcp", "model-context-protocol"},
        "skill": {"tool-use", "function-calling", "ai-tools"},
        "hardware": {"gpu", "inference", "tensor", "cuda"},
    }
    for tool in tools:
        topics_lower = {t.lower() for t in tool.get("topics", [])}
        for cat, cat_topics in topic_map.items():
            if topics_lower & cat_topics:
                tool["category"] = cat
                break
    return tools


async def main() -> None:
    token = sys.argv[1] if len(sys.argv) > 1 else None
    all_tools = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # GitHub topic search
        print("Fetching from GitHub topics...")
        tasks = []
        for category, topics in GITHUB_TOPICS.items():
            for topic in topics:
                tasks.append(github_search(client, topic, category, token))
        results = await asyncio.gather(*tasks)
        for batch in results:
            all_tools.extend(batch)
        print(f"  GitHub: {len(all_tools)} tools found")

        # Awesome lists
        print("Fetching awesome lists...")
        awesome_tools = await fetch_awesome_lists(client)
        print(f"  Awesome lists: {len(awesome_tools)} tools found")

        # Enrich awesome-list tools with GitHub stars
        print("Enriching with GitHub metadata...")
        awesome_tools = await enrich_with_github_stars(client, awesome_tools, token)
        all_tools.extend(awesome_tools)

        # PyPI
        print("Searching PyPI...")
        for term in PYPI_SEARCH_TERMS:
            pypi_tools = await search_pypi(client, term)
            all_tools.extend(pypi_tools)
        print(f"  PyPI: {len(all_tools)} total tools")

        # npm
        print("Searching npm...")
        for term in NPM_SEARCH_TERMS:
            npm_tools = await search_npm(client, term)
            all_tools.extend(npm_tools)
        print(f"  npm: {len(all_tools)} total tools")

    # Deduplicate and categorize
    all_tools = deduplicate(all_tools)
    all_tools = categorize_by_topics(all_tools)

    # Quality filter: remove tools with 0 stars AND no description
    all_tools = [t for t in all_tools if t.get("stars", 0) > 0 or t.get("description", "").strip()]

    # Limit per category to avoid huge pages (keep top by stars)
    MAX_PER_CATEGORY = 100
    by_cat = {}
    for t in all_tools:
        by_cat.setdefault(t["category"], []).append(t)
    filtered = []
    for cat, tools in by_cat.items():
        tools.sort(key=lambda x: x.get("stars", 0), reverse=True)
        filtered.extend(tools[:MAX_PER_CATEGORY])
    all_tools = filtered

    # Sort by stars descending
    all_tools.sort(key=lambda x: x.get("stars", 0), reverse=True)

    # Save
    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_tools": len(all_tools),
        "categories": sorted(set(t["category"] for t in all_tools)),
        "tools": all_tools,
    }
    DATA_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(all_tools)} tools to {DATA_FILE}")
    by_cat = {}
    for t in all_tools:
        by_cat.setdefault(t["category"], 0)
        by_cat[t["category"]] += 1
    for cat, count in sorted(by_cat.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
