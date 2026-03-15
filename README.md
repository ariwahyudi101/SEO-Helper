# SEO Helper / `seo-audit`

Production-ready Python CLI for technical SEO + GEO (AI search optimization) audits.

## Features

- Same-host BFS crawler with robots.txt evaluation, sitemap discovery/parsing, deduped URL queue, redirect tracking, and partial completion on failures.
- Per-page SEO signal extraction (metadata, headings, content quality, links, images, schema).
- SQLite persistence for sites, audits, pages, issues, reports, and AI simulations.
- AI provider fallback chain (OpenAI primary -> DeepSeek fallback) with retries and timeout support.
- GEO scoring and AI citation-likelihood simulation.
- Markdown reporting with transparent score components.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
# optional dev deps
pip install -e '.[dev]'
```

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key (primary AI provider).
- `DEEPSEEK_API_KEY`: DeepSeek API key (fallback provider).
- `SEO_AUDIT_DB_PATH`: SQLite file path (default: `seo_audit.db`).
- `OPENAI_MODEL`: OpenAI model name (default: `gpt-4o-mini`).
- `DEEPSEEK_MODEL`: DeepSeek model name (default: `deepseek-chat`).
- `SEO_AUDIT_TIMEOUT`: HTTP timeout in seconds for crawl + AI calls (default: `15`).

## Usage

Run an audit:

```bash
seo-audit https://example.com --output reports --max-pages 80 --rate-limit 0.2
```

Show audit history:

```bash
seo-audit history
```

Show persisted report markdown:

```bash
seo-audit show-report 1
```

List audited sites:

```bash
seo-audit list-sites
```

## Output

- Markdown reports are saved to `--output` directory as `audit_<id>_<domain>.md`.
- The same markdown is persisted in SQLite table `reports`.
- Crawl/page/issues/simulation records are persisted for historical analysis.

## Testing

```bash
pytest
```
