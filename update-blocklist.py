#!/usr/bin/env python3
"""
=============================================================================
AI-SHIELD: update-blocklist.py  (GitHub Pages + Cloudflare edition)

This site is static GitHub Pages, fronted by Cloudflare. There is no PHP,
Apache, or nginx to generate config for — so this script's job is now:

  1. Maintain one source-of-truth blocklist (blocklist.json)
  2. Regenerate robots.txt from it
  3. Generate a Cloudflare WAF custom rule expression you can paste directly
     into Security > WAF > Custom Rules, for the generic scraping libraries
     that Cloudflare's AI Crawl Control doesn't specifically target (it
     focuses on bots that self-identify as AI; curl/python-requests/Scrapy
     etc. are just common tools determined scrapers reach for).

USAGE:
  python3 update-blocklist.py generate          # regenerate robots.txt + WAF rule
  python3 update-blocklist.py stats             # show blocklist stats
  python3 update-blocklist.py check-ua "MyBot/1.0"
  python3 update-blocklist.py add-ua "NewAIBot" --company "SomeCo"

CRON EXAMPLE (weekly, via GitHub Actions — see .github/workflows/):
  0 3 * * 0 python3 update-blocklist.py generate

CONTRIBUTING / source for new bot signatures:
  https://github.com/ai-robots-txt/ai.robots.txt
=============================================================================
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Master blocklist (source of truth — robots.txt and the WAF rule are both
# regenerated from this single list, so they never drift out of sync)
# ---------------------------------------------------------------------------

BLOCKLIST: dict = {
    "version": "2.0.0",
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    "user_agents": [
        {"name": "GPTBot",               "company": "OpenAI",      "category": "ai"},
        {"name": "ChatGPT-User",         "company": "OpenAI",      "category": "ai"},
        {"name": "OAI-SearchBot",        "company": "OpenAI",      "category": "ai"},
        {"name": "ClaudeBot",            "company": "Anthropic",   "category": "ai"},
        {"name": "Claude-Web",           "company": "Anthropic",   "category": "ai"},
        {"name": "anthropic-ai",         "company": "Anthropic",   "category": "ai"},
        {"name": "Google-Extended",      "company": "Google",      "category": "ai"},
        {"name": "Google-CloudVertexBot","company": "Google",      "category": "ai"},
        {"name": "Bard",                 "company": "Google",      "category": "ai"},
        {"name": "Gemini",               "company": "Google",      "category": "ai"},
        {"name": "FacebookBot",          "company": "Meta",        "category": "ai"},
        {"name": "Meta-ExternalAgent",   "company": "Meta",        "category": "ai"},
        {"name": "Meta-ExternalFetcher", "company": "Meta",        "category": "ai"},
        {"name": "Applebot-Extended",    "company": "Apple",       "category": "ai"},
        {"name": "Amazonbot",            "company": "Amazon",      "category": "ai"},
        {"name": "PerplexityBot",        "company": "Perplexity",  "category": "ai"},
        {"name": "cohere-ai",            "company": "Cohere",      "category": "ai"},
        {"name": "CCBot",                "company": "CommonCrawl", "category": "ai"},
        {"name": "Diffbot",              "company": "Diffbot",     "category": "ai"},
        {"name": "Bytespider",           "company": "ByteDance",   "category": "ai"},
        {"name": "PetalBot",             "company": "Huawei",      "category": "ai"},
        {"name": "DataForSeoBot",        "company": "DataForSeo",  "category": "ai"},
        {"name": "ImagesiftBot",         "company": "Unknown",     "category": "ai"},
        {"name": "omgili",               "company": "Webz.io",     "category": "ai"},
        {"name": "omgilibot",            "company": "Webz.io",     "category": "ai"},
        {"name": "AI2Bot",               "company": "AI2",         "category": "ai"},
        # Generic scraping tools/libraries — robots.txt + WAF only, since
        # Cloudflare's AI Crawl Control targets self-identifying AI bots,
        # not generic HTTP clients that any scraper (AI or not) might use.
        {"name": "Scrapy",               "company": "generic", "category": "generic"},
        {"name": "python-requests",      "company": "generic", "category": "generic"},
        {"name": "python-urllib",        "company": "generic", "category": "generic"},
        {"name": "Go-http-client",       "company": "generic", "category": "generic"},
        {"name": "curl/",                "company": "generic", "category": "generic"},
        {"name": "Wget/",                "company": "generic", "category": "generic"},
        {"name": "libwww-perl",          "company": "generic", "category": "generic"},
        {"name": "HeadlessChrome",       "company": "generic", "category": "generic"},
        {"name": "Puppeteer",            "company": "generic", "category": "generic"},
        {"name": "Playwright",           "company": "generic", "category": "generic"},
        {"name": "PhantomJS",            "company": "generic", "category": "generic"},
        {"name": "Selenium",             "company": "generic", "category": "generic"},
        {"name": "SemrushBot",           "company": "Semrush", "category": "generic"},
    ],
    "allowed_search_bots": ["Googlebot", "Bingbot", "DuckDuckBot", "Applebot"],
}

BLOCKLIST_FILE = Path(__file__).parent / "blocklist.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_blocklist() -> dict:
    if BLOCKLIST_FILE.exists():
        with open(BLOCKLIST_FILE) as f:
            return json.load(f)
    return BLOCKLIST


def save_blocklist(bl: dict) -> None:
    bl["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(BLOCKLIST_FILE, "w") as f:
        json.dump(bl, f, indent=2)
    print(f"[+] Saved blocklist to {BLOCKLIST_FILE}")


def check_ua(ua_string: str, bl: dict) -> tuple[bool, str]:
    ua_lower = ua_string.lower()
    for entry in bl["user_agents"]:
        if entry["name"].lower() in ua_lower:
            return True, entry["name"]
    return False, ""


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_robots_txt(bl: dict) -> str:
    lines = [
        "# accordanalyst.com — robots.txt (auto-generated by update-blocklist.py)",
        f"# Updated: {bl['updated']}",
        "# Backed by Cloudflare AI Crawl Control + WAF — see CLOUDFLARE_AI_BLOCKING.md",
        "",
    ]
    for entry in bl["user_agents"]:
        if entry.get("category") == "generic":
            continue  # generic HTTP libraries don't honor robots.txt anyway
        lines.append(f"User-agent: {entry['name']}")
        lines.append("Disallow: /")
        lines.append("")

    lines.append("# Generic scraping libraries (handled by Cloudflare WAF instead —")
    lines.append("# robots.txt is meaningless to tools that don't read it):")
    for entry in bl["user_agents"]:
        if entry.get("category") == "generic":
            lines.append(f"#   {entry['name']}")
    lines.append("")
    lines += [
        "# Allow human search engines",
    ]
    for bot in bl["allowed_search_bots"]:
        lines.append(f"User-agent: {bot}")
        lines.append("Allow: /")
        lines.append("")
    lines.append("Sitemap: https://accordanalyst.com/sitemap.xml")
    return "\n".join(lines)


def generate_cloudflare_waf_expression(bl: dict) -> str:
    """Generates a paste-ready Cloudflare Custom Rule expression covering the
    generic scraping libraries — the gap AI Crawl Control's toggle doesn't
    cover, since those tools don't self-identify as AI."""
    generic = [e["name"] for e in bl["user_agents"] if e.get("category") == "generic"]
    clauses = [f'(http.user_agent contains "{name}")' for name in generic]
    expr = " or ".join(clauses)
    return (
        "# Paste into Cloudflare > Security > WAF > Custom Rules\n"
        "# Action: Block. Place AFTER a verified-bot Skip rule (see CLOUDFLARE_AI_BLOCKING.md)\n"
        "# so Googlebot/Bingbot are never affected.\n\n"
        f"{expr}\n"
    )


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_generate(args) -> None:
    bl = load_blocklist()
    base = Path(__file__).parent

    (base / "robots.txt").write_text(generate_robots_txt(bl))
    print("[+] Generated robots.txt")

    (base / "cloudflare-waf-rule.txt").write_text(generate_cloudflare_waf_expression(bl))
    print("[+] Generated cloudflare-waf-rule.txt")

    save_blocklist(bl)
    print("\n[✓] Done. Review both files, then update Cloudflare's Custom Rule manually")
    print("    (Cloudflare has no public API write-access on the free plan for this).")


def cmd_check_ua(args) -> None:
    bl = load_blocklist()
    blocked, pattern = check_ua(args.ua, bl)
    print(f"[BLOCKED] Matches '{pattern}'" if blocked else "[ALLOWED] No match found.")


def cmd_add_ua(args) -> None:
    bl = load_blocklist()
    existing = [e["name"].lower() for e in bl["user_agents"]]
    if args.name.lower() in existing:
        print(f"[!] '{args.name}' already in blocklist.")
        return
    bl["user_agents"].append({
        "name": args.name,
        "company": args.company or "unknown",
        "category": args.category or "ai",
    })
    save_blocklist(bl)
    print(f"[+] Added '{args.name}'. Run `generate` to apply.")


def cmd_stats(args) -> None:
    bl = load_blocklist()
    uas = bl["user_agents"]
    by_cat = {}
    for e in uas:
        c = e.get("category", "unknown")
        by_cat[c] = by_cat.get(c, 0) + 1
    print(f"\nAI-SHIELD Blocklist Stats (updated {bl['updated']})")
    print(f"  Total UA entries: {len(uas)}")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"    {cat:<10} {count}")


def main():
    parser = argparse.ArgumentParser(description="AI-SHIELD blocklist manager (GitHub Pages + Cloudflare)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("generate", help="Regenerate robots.txt + Cloudflare WAF rule from blocklist.json")
    sub.add_parser("stats", help="Show blocklist statistics")

    p_check = sub.add_parser("check-ua", help="Test if a UA string would be blocked")
    p_check.add_argument("ua")

    p_add = sub.add_parser("add-ua", help="Add a new user-agent to the blocklist")
    p_add.add_argument("name")
    p_add.add_argument("--company", "-c")
    p_add.add_argument("--category", "-t", choices=["ai", "generic"], default="ai")

    args = parser.parse_args()
    dispatch = {"generate": cmd_generate, "stats": cmd_stats, "check-ua": cmd_check_ua, "add-ua": cmd_add_ua}
    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
