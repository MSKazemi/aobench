#!/usr/bin/env python3
"""Verify the built docs site actually carries its discoverability surfaces.

Search engines and AI answer engines only see what ends up in `site/`. A template
override that silently stops rendering, a `robots.txt` that never gets copied, or a
sitemap missing half the pages are all invisible failures — the build stays green and
the traffic quietly does not arrive.

Run after `mkdocs build`::

    python scripts/seo_check.py            # check ./site
    python scripts/seo_check.py --site-dir some/other/site

Exits 1 on any failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent

#: Schema.org types the site is supposed to publish on every page.
REQUIRED_SCHEMA_TYPES = {
    "SoftwareSourceCode",
    "Dataset",
    "Person",
    "WebSite",
    "TechArticle",
    "BreadcrumbList",
}

#: Crawlers that must not be blocked. Being absent from robots.txt is fine (the
#: wildcard allows them); being explicitly disallowed is not.
MUST_NOT_BLOCK = [
    "Googlebot",
    "Bingbot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "ClaudeBot",
    "GPTBot",
]

#: Pages that carry the load for answer-engine queries. Missing one is a real
#: regression, not a nice-to-have.
KEY_PAGES = [
    "index.html",
    "getting-started/quickstart/index.html",
    "about/faq/index.html",
    "about/comparison/index.html",
    "about/limitations/index.html",
    "about/datasheet/index.html",
    "reference/task-catalog/index.html",
    "reference/glossary/index.html",
    "leaderboard/index.html",
]


class Checker:
    def __init__(self, site: Path) -> None:
        self.site = site
        self.failures: list[str] = []
        self.passes = 0

    def check(self, condition: bool, label: str, detail: str = "") -> None:
        if condition:
            self.passes += 1
        else:
            self.failures.append(f"{label}{f' — {detail}' if detail else ''}")

    # -- individual checks -------------------------------------------------

    def check_robots(self) -> None:
        path = self.site / "robots.txt"
        self.check(path.is_file(), "robots.txt is published")
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        self.check("Sitemap:" in text, "robots.txt declares a Sitemap")
        for agent in MUST_NOT_BLOCK:
            blocked = re.search(
                rf"User-agent:\s*{re.escape(agent)}\s*\nDisallow:\s*/\s*$",
                text,
                re.MULTILINE | re.IGNORECASE,
            )
            self.check(not blocked, f"robots.txt does not block {agent}")

    def check_sitemap(self) -> None:
        path = self.site / "sitemap.xml"
        self.check(path.is_file(), "sitemap.xml is published")
        if not path.is_file():
            return
        try:
            root = ElementTree.fromstring(path.read_bytes())
        except ElementTree.ParseError as exc:
            self.check(False, "sitemap.xml parses", str(exc))
            return
        locs = [e.text or "" for e in root.iter() if e.tag.endswith("loc")]
        self.check(len(locs) >= 20, "sitemap lists at least 20 URLs", f"found {len(locs)}")
        self.check(
            all(u.startswith("https://") for u in locs),
            "every sitemap URL is absolute https",
        )

    def check_llms_txt(self) -> None:
        path = self.site / "llms.txt"
        self.check(path.is_file(), "llms.txt is published")
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        self.check(text.startswith("# "), "llms.txt starts with an H1")
        self.check("## Links" in text, "llms.txt has a Links section")
        self.check(
            "Disambiguation:" in text,
            "llms.txt disambiguates from the ambient-occlusion `aobench`",
            "the name collides with syoyo/aobench; answer engines need this stated",
        )
        for name in ("llms.txt", "llms-full.txt"):
            root_copy = ROOT / name
            docs_copy = ROOT / "docs" / name
            if root_copy.is_file() and docs_copy.is_file():
                self.check(
                    root_copy.read_text(encoding="utf-8") == docs_copy.read_text(encoding="utf-8"),
                    f"root {name} matches docs/{name}",
                    "the two copies have drifted — they must stay identical",
                )

        full = self.site / "llms-full.txt"
        self.check(full.is_file(), "llms-full.txt is published")
        if full.is_file():
            n_bytes = len(full.read_text(encoding="utf-8"))
            self.check(
                n_bytes > 50_000,
                "llms-full.txt carries the full docs",
                f"only {n_bytes:,} bytes — did the concatenation break?",
            )

    def check_page(self, rel: str) -> None:
        path = self.site / rel
        if not path.is_file():
            self.check(False, f"{rel} exists")
            return
        self.passes += 1
        html = path.read_text(encoding="utf-8")

        # The minifier strips attribute quotes, so match loosely on purpose.
        self.check(re.search(r"rel=[\"']?canonical", html) is not None, f"{rel}: canonical link")
        self.check("og:title" in html, f"{rel}: Open Graph title")
        self.check("og:description" in html, f"{rel}: Open Graph description")
        self.check("twitter:card" in html, f"{rel}: Twitter card")
        self.check(
            re.search(r"<meta name=[\"']?description", html) is not None,
            f"{rel}: meta description",
        )

        blocks = re.findall(
            r'<script type=[\'"]?application/ld\+json[\'"]?>(.*?)</script>', html, re.DOTALL
        )
        self.check(bool(blocks), f"{rel}: has JSON-LD")
        types: set[str] = set()
        for block in blocks:
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                self.check(False, f"{rel}: JSON-LD parses", str(exc))
                continue
            for node in data.get("@graph", [data]):
                if isinstance(node, dict) and "@type" in node:
                    types.add(str(node["@type"]))
        missing = REQUIRED_SCHEMA_TYPES - types
        self.check(not missing, f"{rel}: JSON-LD schema types", f"missing {sorted(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "site")
    args = parser.parse_args()

    if not args.site_dir.is_dir():
        print(
            f"No built site at {args.site_dir}. Run `make docs-build` first.",
            file=sys.stderr,
        )
        return 1

    checker = Checker(args.site_dir)
    checker.check_robots()
    checker.check_sitemap()
    checker.check_llms_txt()
    for page in KEY_PAGES:
        checker.check_page(page)

    if checker.failures:
        print(f"SEO check FAILED — {len(checker.failures)} problem(s):\n", file=sys.stderr)
        for failure in checker.failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"SEO check passed — {checker.passes} assertions over {len(KEY_PAGES)} key pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
