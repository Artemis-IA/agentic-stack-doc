#!/usr/bin/env python3
"""Veille Hugging Face — Récupère les modèles et datasets trending."""

import asyncio
import re
import sys
from pathlib import Path

import httpx

HF_API = "https://huggingface.co/api"
OUTPUT_FILE = Path(__file__).parent.parent / "content" / "veille" / "github-hf.qmd"

RELEVANT_TAGS = [
    "text-generation", "text2text-generation", "code", "agent",
    "conversational", "feature-extraction", "embedding",
    "text-to-image", "multimodal",
]


async def fetch_models(client: httpx.AsyncClient) -> list[dict]:
    models = []
    for tag in RELEVANT_TAGS[:5]:
        resp = await client.get(
            f"{HF_API}/models",
            params={"sort": "likes", "direction": "-1", "limit": 10, "filter": tag},
        )
        if resp.status_code == 200:
            models.extend(resp.json())
    return models


async def fetch_datasets(client: httpx.AsyncClient) -> list[dict]:
    resp = await client.get(
        f"{HF_API}/datasets",
        params={"sort": "likes", "direction": "-1", "limit": 10},
    )
    if resp.status_code == 200:
        return resp.json()
    return []


def generate_models_md(models: list[dict]) -> str:
    seen = set()
    lines = []
    for m in models:
        mid = m.get("id", "")
        if mid in seen:
            continue
        seen.add(mid)
        downloads = m.get("downloads", 0)
        likes = m.get("likes", 0)
        tags = m.get("tags", [])
        lines.append(f"### {mid}")
        lines.append(f"- **Downloads** : {downloads:,}")
        lines.append(f"- **Likes** : {likes}")
        lines.append(f"- **Tags** : {', '.join(tags[:5])}")
        lines.append(f"- **Lien** : https://huggingface.co/{mid}")
        lines.append("")
    return "\n".join(lines)


def generate_datasets_md(datasets: list[dict]) -> str:
    lines = []
    for d in datasets:
        did = d.get("id", "")
        downloads = d.get("downloads", 0)
        likes = d.get("likes", 0)
        lines.append(f"### {did}")
        lines.append(f"- **Downloads** : {downloads:,}")
        lines.append(f"- **Likes** : {likes}")
        lines.append(f"- **Lien** : https://huggingface.co/datasets/{did}")
        lines.append("")
    return "\n".join(lines)


def update_qmd(models_md: str, datasets_md: str) -> None:
    content = OUTPUT_FILE.read_text(encoding="utf-8")

    pattern = r"(<!-- HF_FEED_START -->)(.*?)(<!-- HF_FEED_END -->)"
    replacement = rf"\1\n{models_md}\n\3"
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"Updated {OUTPUT_FILE}")


async def main() -> None:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        models = await fetch_models(client)
        datasets = await fetch_datasets(client)

    if not models and not datasets:
        print("No models or datasets found.")
        return

    models_md = generate_models_md(models)
    datasets_md = generate_datasets_md(datasets)
    combined = "## Modèles\n\n" + models_md + "\n## Datasets\n\n" + datasets_md
    update_qmd(combined, "")
    print(f"Found {len(models)} models, {len(datasets)} datasets.")


if __name__ == "__main__":
    asyncio.run(main())
