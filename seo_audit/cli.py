from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from seo_audit.analyzer import ProviderError, analyze_with_fallback
from seo_audit.config import load_settings
from seo_audit.crawler import crawl_site
from seo_audit.database import (
    create_audit,
    create_site,
    get_connection,
    get_history,
    get_report,
    insert_ai_simulation,
    insert_issue,
    insert_page,
    list_sites,
    migrate,
    store_report,
)
from seo_audit.geo_analyzer import compute_geo_scores, simulate_ai_answers
from seo_audit.parser import parse_page
from seo_audit.reporter import generate_markdown_report
from seo_audit.utils import extract_root_domain, normalize_url

console = Console()
admin_app = typer.Typer(add_completion=False, help="SEO and GEO audit CLI")


def run_audit(
    url: str = typer.Argument(..., help="URL to audit"),
    output: Path = typer.Option(Path("reports"), "--output", help="Report output directory"),
    max_pages: int = typer.Option(50, "--max-pages", min=1),
    rate_limit: float = typer.Option(0.0, "--rate-limit", min=0.0),
) -> None:
    settings = load_settings()
    normalized_url = normalize_url(url)
    root_domain = extract_root_domain(normalized_url)

    conn = get_connection(settings.db_path)
    migrate(conn)
    site_id = create_site(conn, root_domain)
    audit_id = create_audit(conn, site_id, normalized_url, max_pages, rate_limit)

    crawl = crawl_site(normalized_url, max_pages=max_pages, rate_limit=rate_limit, timeout=settings.request_timeout)

    signals = []
    for page in crawl.crawled_pages:
        if not page.html:
            if page.error:
                insert_issue(conn, audit_id, page.url, "crawl_error", page.error)
            continue

        parsed = parse_page(page.final_url or page.url, page.html, page.status_code)
        signals.append(parsed)
        insert_page(
            conn,
            audit_id,
            {
                "url": parsed.url,
                "status_code": page.status_code,
                "title": parsed.title,
                "meta_description": parsed.meta_description,
                "canonical": parsed.canonical,
                "robots_meta": parsed.robots_meta,
                "word_count": parsed.word_count,
                "paragraph_count": parsed.paragraph_count,
                "thin_content": parsed.thin_content,
                "internal_links": parsed.internal_links,
                "external_links": parsed.external_links,
                "image_count": parsed.image_count,
                "missing_alt_count": parsed.missing_alt_count,
                "indexable": parsed.indexable,
                "canonical_conflict": parsed.canonical_conflict,
                "schema_types": parsed.schema_types,
            },
        )
        for issue in parsed.issues:
            insert_issue(conn, audit_id, parsed.url, "seo_issue", issue)

    geo_scores = compute_geo_scores(signals)
    ai_simulations = simulate_ai_answers(signals)

    ai_metadata = "heuristic-only"
    prompt = f"Summarize high-priority SEO/GEO fixes for {normalized_url} based on {len(signals)} pages."
    try:
        ai_result = analyze_with_fallback(
            prompt,
            openai_key=settings.openai_api_key,
            deepseek_key=settings.deepseek_api_key,
            openai_model=settings.openai_model,
            deepseek_model=settings.deepseek_model,
            timeout=settings.request_timeout,
        )
        ai_metadata = ai_result.provider_used
    except ProviderError:
        pass

    for row in ai_simulations:
        insert_ai_simulation(conn, audit_id, row)

    markdown, scores = generate_markdown_report(
        start_url=normalized_url,
        crawl_summary={
            "discovered": len(crawl.discovered_urls),
            "crawled": len(crawl.crawled_pages),
            "blocked": len(crawl.blocked_urls),
            "failed": len(crawl.failed_urls),
        },
        signals=signals,
        geo_scores=geo_scores,
        ai_simulations=ai_simulations,
    )
    store_report(conn, audit_id, markdown, provider_used=ai_metadata)

    output.mkdir(parents=True, exist_ok=True)
    report_path = output / f"audit_{audit_id}_{root_domain.replace('.', '_')}.md"
    report_path.write_text(markdown, encoding="utf-8")

    console.print(f"[green]Audit complete[/green] id={audit_id} overall={scores.overall} report={report_path}")


@admin_app.command("history")
def history() -> None:
    settings = load_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    rows = get_history(conn)
    table = Table(title="Audit History")
    table.add_column("Audit ID")
    table.add_column("Site")
    table.add_column("Start URL")
    table.add_column("Created")
    for row in rows[:25]:
        table.add_row(str(row["id"]), row["root_domain"], row["start_url"], row["created_at"])
    console.print(table)


@admin_app.command("show-report")
def show_report(audit_id: int) -> None:
    settings = load_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    row = get_report(conn, audit_id)
    if not row:
        console.print(f"[red]No report for audit {audit_id}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[bold]Report for audit {audit_id}[/bold] (provider={row['provider_used']})")
    console.print(row["markdown"])


@admin_app.command("list-sites")
def list_sites_cmd() -> None:
    settings = load_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    rows = list_sites(conn)
    table = Table(title="Audited Sites")
    table.add_column("Root Domain")
    table.add_column("Audits")
    table.add_column("Last Audit")
    for row in rows:
        table.add_row(row["root_domain"], str(row["audit_count"]), str(row["last_audit"] or "-"))
    console.print(table)


def app() -> None:
    subcommands = {"history", "show-report", "list-sites"}
    if len(sys.argv) > 1 and sys.argv[1] in subcommands:
        admin_app(prog_name="seo-audit")
    else:
        typer.run(run_audit)


if __name__ == "__main__":
    app()
