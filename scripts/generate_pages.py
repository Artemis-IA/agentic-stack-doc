#!/usr/bin/env python3
"""Generate dynamic content pages from data/tools.json.

Reads the tools database and injects dynamic listings into:
- content/catalog.qmd — flagship catalog page (fully generated)
- content/harnesses/*.qmd — harness listings
- content/sandboxes/*.qmd — sandbox listings
- content/frameworks/*.qmd — framework listings
- content/llms/*.qmd — LLM/inference tool listings
- content/skills/*.qmd — MCP servers and skill tools
- content/veille/github-hf.qmd — trending repos
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "tools.json"

# ─── Helpers ────────────────────────────────────────────────────────────────

CATEGORY_LABELS = {
    "harness": "Harnesses & IDEs IA",
    "sandbox": "Sandboxes & Exécution",
    "framework": "Frameworks Agentic",
    "llm": "LLMs & Inference",
    "rag": "RAG & GraphRAG",
    "mcp": "MCP Servers",
    "skill": "Skills & Outils",
    "hardware": "Hardware & Accélérateurs",
}


def load_tools() -> dict:
    if not DATA_FILE.exists():
        print("tools.json not found. Run discover_tools.py first.")
        sys.exit(1)
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def tools_by_category(data: dict, category: str) -> list[dict]:
    return [t for t in data["tools"] if t["category"] == category]


def fmt_stars(n: int) -> str:
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def clean_desc(desc: str, max_len: int = 100) -> str:
    """Clean a description: strip markdown links, extra whitespace, limit length."""
    if not desc:
        return ""
    # Remove markdown links: [text](url) → text
    desc = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", desc)
    # Remove remaining markdown formatting
    desc = re.sub(r"\*\*([^*]*)\*\*", r"\1", desc)
    desc = re.sub(r"`([^`]*)`", r"\1", desc)
    # Collapse whitespace
    desc = re.sub(r"\s+", " ", desc).strip()
    # Truncate
    if len(desc) > max_len:
        desc = desc[:max_len-3] + "..."
    return desc


def generate_tool_table(tools: list[dict], limit: int = 50) -> str:
    """Generate a markdown table of tools."""
    if not tools:
        return "*Aucun outil trouvé dans cette catégorie. Le catalogue est mis à jour automatiquement.*"

    lines = [
        "| Outil | Description | Stars | Langage | Licence | Dernière MAJ |",
        "|-------|-------------|-------|---------|---------|-------------|",
    ]
    for t in tools[:limit]:
        raw_name = t["name"]
        # Clean name from markdown artifacts
        clean_name = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", raw_name)
        clean_name = clean_name.replace("**", "").strip()
        name = f"[{clean_name}]({t['url']})"
        desc = clean_desc(t.get("description", ""), 100).replace("|", "\\|")
        stars = fmt_stars(t.get("stars", 0))
        lang = t.get("language") or "—"
        license_ = t.get("license") or "—"
        updated = (t.get("updated_at") or "—")[:10]
        lines.append(f"| {name} | {desc} | {stars} | {lang} | {license_} | {updated} |")
    return "\n".join(lines)


def generate_tool_cards(tools: list[dict], limit: int = 30) -> str:
    """Generate detailed markdown cards for tools."""
    if not tools:
        return "*Aucun outil trouvé dans cette catégorie. Le catalogue est mis à jour automatiquement.*"

    lines = []
    for t in tools[:limit]:
        raw_name = t["name"]
        clean_name = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", raw_name)
        clean_name = clean_name.replace("**", "").strip()
        lines.append(f"### [{clean_name}]({t['url']})")
        desc = clean_desc(t.get("description", ""), 200)
        if desc:
            lines.append(desc)
        lines.append("")
        meta = []
        if t.get("stars", 0) > 0:
            meta.append(f"⭐ {fmt_stars(t['stars'])}")
        if t.get("language"):
            meta.append(f"`{t['language']}`")
        if t.get("license"):
            meta.append(f"Licence: {t['license']}")
        if t.get("updated_at"):
            meta.append(f"MAJ: {t['updated_at'][:10]}")
        if meta:
            lines.append(" | ".join(meta))
        if t.get("topics"):
            lines.append(f"**Tags** : {', '.join(f'`{tp}`' for tp in t['topics'][:8])}")
        lines.append("")
    return "\n".join(lines)


def inject_section(filepath: Path, marker: str, content: str) -> bool:
    """Inject content between <!-- MARKER_START --> and <!-- MARKER_END -->."""
    if not filepath.exists():
        print(f"  Skip (not found): {filepath}")
        return False
    text = filepath.read_text(encoding="utf-8")
    pattern = rf"(<!-- {marker}_START -->)(.*?)(<!-- {marker}_END -->)"
    if not re.search(pattern, text, re.DOTALL):
        print(f"  Skip (no marker {marker}): {filepath}")
        return False
    replacement = rf"\1\n{content}\n\3"
    updated = re.sub(pattern, replacement, text, flags=re.DOTALL)
    filepath.write_text(updated, encoding="utf-8")
    print(f"  Updated: {filepath}")
    return True


# ─── Catalog page (flagship) ────────────────────────────────────────────────

def generate_catalog(data: dict) -> None:
    """Generate the flagship catalog page."""
    catalog_path = ROOT / "content" / "catalog.qmd"
    lines = [
        "---",
        'title: "Catalogue des Outils & Frameworks"',
        "date: today",
        'date-format: "YYYY-MM-DD"',
        "---",
        "",
        "# Catalogue des Outils & Frameworks",
        "",
        f"> **{data['total_tools']} outils** recensés automatiquement le {data['generated_at'][:10]}.",
        "> Ce catalogue est mis à jour automatiquement par les scripts de veille.",
        "",
    ]

    # Summary table by category
    lines.append("## Vue d'ensemble par catégorie")
    lines.append("")
    lines.append("| Catégorie | Nombre d'outils | |")
    lines.append("|-----------|----------------|-|")
    for cat in data["categories"]:
        count = sum(1 for t in data["tools"] if t["category"] == cat)
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"| [{label}](#cat-{cat}) | {count} | |")
    lines.append("")

    # Top 20 overall
    lines.append("## Top 20 — Tous catégories")
    lines.append("")
    lines.append(generate_tool_table(data["tools"], limit=20))
    lines.append("")

    # Per category sections
    for cat in data["categories"]:
        tools = tools_by_category(data, cat)
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"## {label} {{#cat-{cat}}}")
        lines.append("")
        lines.append(f"**{len(tools)} outils** dans cette catégorie.")
        lines.append("")
        lines.append(generate_tool_table(tools, limit=50))
        lines.append("")

    catalog_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Generated: {catalog_path}")


# ─── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    data = load_tools()
    print(f"Loaded {data['total_tools']} tools from {DATA_FILE}")
    print(f"Categories: {data['categories']}")
    print()

    # Generate flagship catalog
    print("Generating catalog.qmd...")
    generate_catalog(data)

    # Inject into existing pages
    print("\nInjecting into existing pages...")

    # Harnesses
    harness_tools = tools_by_category(data, "harness")
    inject_section(
        ROOT / "content" / "harnesses" / "proprietary.qmd",
        "TOOLS_HARNESS_PROP",
        generate_tool_cards(harness_tools, limit=20),
    )
    inject_section(
        ROOT / "content" / "harnesses" / "open-source.qmd",
        "TOOLS_HARNESS_OSS",
        generate_tool_cards(harness_tools, limit=20),
    )

    # Sandboxes
    sandbox_tools = tools_by_category(data, "sandbox")
    inject_section(
        ROOT / "content" / "sandboxes" / "containers.qmd",
        "TOOLS_SANDBOX",
        generate_tool_cards(sandbox_tools, limit=20),
    )

    # Frameworks
    framework_tools = tools_by_category(data, "framework")
    inject_section(
        ROOT / "content" / "frameworks" / "multi-agent.qmd",
        "TOOLS_FRAMEWORK",
        generate_tool_cards(framework_tools, limit=30),
    )

    # RAG
    rag_tools = tools_by_category(data, "rag")
    inject_section(
        ROOT / "content" / "frameworks" / "rag.qmd",
        "TOOLS_RAG",
        generate_tool_cards(rag_tools, limit=20),
    )

    # MCP
    mcp_tools = tools_by_category(data, "mcp")
    inject_section(
        ROOT / "content" / "skills" / "mcp.qmd",
        "TOOLS_MCP",
        generate_tool_cards(mcp_tools, limit=30),
    )

    # LLMs
    llm_tools = tools_by_category(data, "llm")
    inject_section(
        ROOT / "content" / "llms" / "open-models.qmd",
        "TOOLS_LLM",
        generate_tool_cards(llm_tools, limit=20),
    )

    # Hardware
    hw_tools = tools_by_category(data, "hardware")
    inject_section(
        ROOT / "content" / "hardware" / "accelerators.qmd",
        "TOOLS_HARDWARE",
        generate_tool_cards(hw_tools, limit=15),
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
