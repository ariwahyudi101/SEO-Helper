from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_domain TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    start_url TEXT NOT NULL,
    max_pages INTEGER,
    rate_limit REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(site_id) REFERENCES sites(id)
);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER,
    title TEXT,
    meta_description TEXT,
    canonical TEXT,
    robots_meta TEXT,
    word_count INTEGER,
    paragraph_count INTEGER,
    thin_content INTEGER,
    internal_links INTEGER,
    external_links INTEGER,
    image_count INTEGER,
    missing_alt_count INTEGER,
    indexable INTEGER,
    canonical_conflict INTEGER,
    schema_types TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id)
);

CREATE TABLE IF NOT EXISTS seo_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL,
    page_url TEXT,
    issue_type TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER UNIQUE NOT NULL,
    markdown TEXT NOT NULL,
    provider_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id)
);

CREATE TABLE IF NOT EXISTS ai_simulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    citation_probability REAL,
    likely_page TEXT,
    snippet TEXT,
    content_gap TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id)
);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def create_site(conn: sqlite3.Connection, root_domain: str) -> int:
    conn.execute("INSERT OR IGNORE INTO sites(root_domain) VALUES (?)", (root_domain,))
    row = conn.execute("SELECT id FROM sites WHERE root_domain = ?", (root_domain,)).fetchone()
    conn.commit()
    return int(row["id"])


def create_audit(conn: sqlite3.Connection, site_id: int, start_url: str, max_pages: int, rate_limit: float) -> int:
    cur = conn.execute(
        "INSERT INTO audits(site_id, start_url, max_pages, rate_limit) VALUES (?, ?, ?, ?)",
        (site_id, start_url, max_pages, rate_limit),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_page(conn: sqlite3.Connection, audit_id: int, page: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO pages(
            audit_id, url, status_code, title, meta_description, canonical, robots_meta,
            word_count, paragraph_count, thin_content, internal_links, external_links,
            image_count, missing_alt_count, indexable, canonical_conflict, schema_types
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            page.get("url"),
            page.get("status_code"),
            page.get("title"),
            page.get("meta_description"),
            page.get("canonical"),
            page.get("robots_meta"),
            page.get("word_count"),
            page.get("paragraph_count"),
            int(bool(page.get("thin_content"))),
            page.get("internal_links"),
            page.get("external_links"),
            page.get("image_count"),
            page.get("missing_alt_count"),
            int(bool(page.get("indexable", True))),
            int(bool(page.get("canonical_conflict"))),
            json.dumps(page.get("schema_types", [])),
        ),
    )
    conn.commit()


def insert_issue(conn: sqlite3.Connection, audit_id: int, page_url: str, issue_type: str, details: str = "") -> None:
    conn.execute(
        "INSERT INTO seo_issues(audit_id, page_url, issue_type, details) VALUES (?, ?, ?, ?)",
        (audit_id, page_url, issue_type, details),
    )
    conn.commit()


def store_report(conn: sqlite3.Connection, audit_id: int, markdown: str, provider_used: str | None = None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO reports(audit_id, markdown, provider_used) VALUES (?, ?, ?)",
        (audit_id, markdown, provider_used),
    )
    conn.commit()


def insert_ai_simulation(conn: sqlite3.Connection, audit_id: int, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO ai_simulations(audit_id, question, citation_probability, likely_page, snippet, content_gap)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            row.get("question"),
            row.get("citation_probability"),
            row.get("likely_page"),
            row.get("snippet"),
            row.get("content_gap"),
        ),
    )
    conn.commit()


def get_history(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT audits.id, sites.root_domain, audits.start_url, audits.created_at
        FROM audits
        JOIN sites ON sites.id = audits.site_id
        ORDER BY audits.created_at DESC
        """
    ).fetchall()


def get_report(conn: sqlite3.Connection, audit_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT audit_id, markdown, provider_used, created_at FROM reports WHERE audit_id = ?",
        (audit_id,),
    ).fetchone()


def list_sites(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT sites.root_domain, COUNT(audits.id) AS audit_count, MAX(audits.created_at) AS last_audit
        FROM sites LEFT JOIN audits ON audits.site_id = sites.id
        GROUP BY sites.id
        ORDER BY last_audit DESC
        """
    ).fetchall()
