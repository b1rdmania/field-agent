#!/usr/bin/env python3
"""field-agent: one person covering a continent.

Takes a target audience and a market, uses Exa to build a qualified guest
list for an executive dinner, then drafts personalised invites and a run of
show. Output is a single markdown briefing pack.

Usage:
  python3 field_agent.py "platform engineering leaders" --market London
  python3 field_agent.py "heads of AI at insurers" --market Munich --results 8
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "out"

EXA_SEARCH = "https://api.exa.ai/search"


def load_key():
    if os.environ.get("EXA_API_KEY"):
        return os.environ["EXA_API_KEY"]
    for env in (ROOT / ".env", ROOT.parent / "exa.env"):
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("EXA_API_KEY="):
                    return line.split("=", 1)[1].strip()
    sys.exit("set EXA_API_KEY or put it in .env")


def exa_search(key, query, num, category=None):
    body = {
        "query": query,
        "numResults": num,
        "contents": {"text": {"maxCharacters": 1200}},
    }
    if category:
        body["category"] = category
    r = subprocess.run(
        ["curl", "-s", "--fail-with-body", "-X", "POST", EXA_SEARCH,
         "-H", f"x-api-key: {key}", "-H", "Content-Type: application/json",
         "-d", json.dumps(body)],
        capture_output=True, text=True, timeout=90,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stdout[:300] or r.stderr[:300])
    return json.loads(r.stdout)["results"]


def gather(key, audience, market, num):
    queries = [
        (f"{audience} based in {market}", "linkedin profile"),
        (f"senior {audience} at a company headquartered in {market}", "linkedin profile"),
        (f"{market} companies hiring {audience} or investing in AI search infrastructure", "company"),
    ]
    seen, pool = set(), []
    for q, cat in queries:
        print(f"  exa: {q} [{cat}]")
        try:
            results = exa_search(key, q, num, cat)
        except Exception as e:
            print(f"  ! search failed, skipping: {e}")
            continue
        for r in results:
            url = r.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            pool.append(
                {
                    "title": r.get("title"),
                    "url": url,
                    "text": (r.get("text") or "")[:1200],
                }
            )
    return pool


def synthesise(audience, market, pool):
    prompt = f"""You are a field marketing operator at Exa (the search engine for AIs;
customers include Cursor, Cognition, HubSpot, Monday.com). You are planning an
executive dinner in {market} for: {audience}.

Below is raw research gathered with Exa's own search API - candidate people and
companies with source URLs and profile text. Some hits will be junk; qualify hard.

Produce a markdown briefing pack with exactly these sections:

## Guest list
A table: Name | Role & company | Why this seat | Source. Pick the 8-10 strongest
qualified candidates only. "Why this seat" is one concrete line grounded in the
profile text, never generic.

## Invites
Three personalised invite emails (subject + <=120 word body) for the three
strongest guests. Each must reference something specific from their profile text.
Tone: direct, warm, no hype, no exclamation marks. Host is "the Exa team in {market}".

## Run of show
A timed run of show for a 6:30pm dinner for 12 (arrival to close), including the
4pm pre-checks. Practical, not aspirational.

## Gaps
Two or three lines: what this research could not verify and what a human must
check before invites go out (seniority, current role, GDPR-clean sourcing).

Raw research follows as JSON:

{json.dumps(pool, indent=1)}"""
    r = subprocess.run(
        ["claude", "-p", prompt, "--model", "sonnet"],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        sys.exit(f"claude failed: {r.stderr[:500]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audience")
    ap.add_argument("--market", default="London")
    ap.add_argument("--results", type=int, default=10)
    args = ap.parse_args()

    key = load_key()
    print(f"field-agent: {args.audience} / {args.market}")
    pool = gather(key, args.audience, args.market, args.results)
    print(f"  {len(pool)} candidates gathered, synthesising...")
    brief = synthesise(args.audience, args.market, pool)

    OUT.mkdir(exist_ok=True)
    slug = "-".join(args.audience.lower().split()[:4]) + "-" + args.market.lower()
    path = OUT / f"brief-{slug}.md"
    header = f"# Executive dinner brief - {args.audience}, {args.market}\n\nBuilt with Exa search + Claude. Research is a starting point, not a send list.\n\n"
    path.write_text(header + brief)
    print(f"  wrote {path}")


if __name__ == "__main__":
    main()
