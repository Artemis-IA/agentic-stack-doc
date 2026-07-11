# Stack Agentic — Documentation Vivante

Documentation interactive et auto-mise-à-jour sur l'écosystème des systèmes agentic IA, en français, hébergée sur GitHub Pages.

## Structure

| Section | Contenu |
|---------|---------|
| Couche Matérielle | GPU, TPU, LPU, NPU, clusters, edge |
| Modèles & LLMs | Modèles propriétaires/ouverts, benchmarks, providers & APIs |
| Harnesses & IDEs IA | Claude Code, Cursor, Cline, Aider, comparatifs, télémétrie |
| Sandboxes & Exécution | Docker, Firecracker, WASM, cloud sandboxes |
| Skills & Outils | MCP, SKILL.md, function calling, écosystèmes d'outils |
| Frameworks Agentic | Multi-agent, recherche autonome, RAG/GraphRAG |
| Déploiement | Sécurité, télémétrie, coût, rate limiting |
| Veille Automatique | arXiv, GitHub trending, Hugging Face, blogs & newsletters |

## Automation

- **CI/CD** : `.github/workflows/deploy.yml` — build Quarto + publish GitHub Pages
- **Veille** : `.github/workflows/veille.yml` — exécute les scripts de veille 2×/jour, commit, et re-déploie
- **Scripts** : `scripts/veille_arxiv.py`, `scripts/veille_github.py`, `scripts/veille_hf.py`, `scripts/veille_blogs.py`

## Développement local

```bash
# Prévisualiser
quarto preview

# Builder
quarto render

# Lancer un script de veille manuellement
python scripts/veille_arxiv.py
python scripts/veille_blogs.py
```

## Stack technique

- [Quarto](https://quarto.org) — publishing system
- GitHub Pages — hosting
- GitHub Actions — CI/CD + veille auto
- Mermaid — diagrammes
- Python — scripts de veille (httpx, feedparser)
