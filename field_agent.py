#!/usr/bin/env python3
"""field-agent: one person covering a continent.

Four commands mirroring the field-marketing loop, all built on Exa search:

  market   which EMEA cities deserve the next event, with evidence
  guests   account-based guest mapping: seller's target accounts in, seats out
  dinner   cold-start discovery when no account list exists yet
  followup post-event: per-attendee brief, draft follow-up, handoff note

Each command writes one markdown pack to out/. Nothing ever sends.

Usage:
  python3 field_agent.py market "AI platform buyers" --cities London,Paris,Munich,Amsterdam
  python3 field_agent.py guests accounts.txt --market London
  python3 field_agent.py dinner "platform engineering leaders" --market London
  python3 field_agent.py followup attendees.txt --event "London infra dinner, 12 Aug"
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

EXA_CONTEXT = """You are a field marketing operator at Exa (the search engine for AIs;
customers include Cursor, Cognition, HubSpot, Monday.com), building the EMEA
programme from a blank page. Raw research below was gathered with Exa's own
search API - source URLs and page text included. Some hits will be junk;
qualify hard and ground every claim in the source text."""


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


def gather(key, queries):
    """Run (label, query, category, num) tuples, dedupe by URL, tag by label."""
    seen, pool = set(), []
    for label, q, cat, num in queries:
        print(f"  exa: [{label}] {q}")
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
                    "for": label,
                    "title": r.get("title"),
                    "url": url,
                    "text": (r.get("text") or "")[:1200],
                }
            )
    return pool


def synthesise(prompt):
    r = subprocess.run(
        ["claude", "-p", prompt, "--model", "sonnet"],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        sys.exit(f"claude failed: {r.stderr[:500]}")
    return r.stdout


def write_pack(slug, title, body):
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{slug}.md"
    header = f"# {title}\n\nBuilt with Exa search + Claude. Research is a starting point, not a send list.\n\n"
    path.write_text(header + body)
    print(f"  wrote {path}")


def slugify(*parts):
    return "-".join("-".join(p.lower().split())[:24] for p in parts if p)


# ---------------------------------------------------------------- commands

def cmd_market(key, args):
    cities = [c.strip() for c in args.cities.split(",")]
    queries = []
    for city in cities:
        queries.append((city, f"{args.segment} at companies headquartered in {city}", "linkedin profile", 5))
        queries.append((city, f"major AI and developer infrastructure conferences in {city} 2026", None, 3))
    pool = gather(key, queries)
    print(f"  {len(pool)} signals gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: recommend where the next quarter of EMEA field events should go for this
segment: {args.segment}. Cities under consideration: {', '.join(cities)}.

Produce a markdown memo with exactly these sections:

## Ranking
A table: City | Buyer density signal | Event landscape | Verdict. Rank all
cities. Ground every cell in the research; where the research is thin for a
city, say so rather than inventing.

## Recommendation
Which one or two cities get investment this quarter and what format fits each
(hosted dinner vs conference presence vs roundtable), with a pipeline rationale
a sales leader would accept. Three short paragraphs maximum.

## What would change this call
Two or three lines: the evidence that would reorder the ranking.

Raw research follows as JSON (the "for" field = the city a hit was gathered for):

{json.dumps(pool, indent=1)}"""
    write_pack(slugify("market", args.segment), f"Market memo - {args.segment}", synthesise(prompt))


def cmd_guests(key, args):
    accounts = [a.strip() for a in pathlib.Path(args.accounts).read_text().splitlines() if a.strip()]
    queries = []
    for acc in accounts:
        queries.append((acc, f"{args.audience} at {acc} in {args.market}", "linkedin profile", 4))
        queries.append((acc, f"{acc} engineering blog or announcement about AI, search or platform infrastructure", None, 2))
    pool = gather(key, queries)
    print(f"  {len(pool)} signals across {len(accounts)} accounts, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: sellers have named these target accounts for {args.market}:
{', '.join(accounts)}. Build the guest map for an account-based executive
dinner. Audience: {args.audience}.

Produce a markdown pack with exactly these sections:

## Account briefs
One short block per account: what the research says they are doing that makes
an Exa conversation timely (their AI/search/platform moves), grounded in the
source text. If the research shows nothing timely, say "no live signal found".

## Seat map
A table: Account | Name | Role | Why this seat | Source. The strongest one or
two people per account. "Why this seat" ties the person to the account brief,
never generic.

## In-deal choreography
For the three accounts with the strongest live signal: the seating and
conversation move that turns dinner into a next meeting, one line each,
written for the seller who owns the account.

## Gaps
What must be verified with the account owner before invites go out: role
currency, existing relationships, open opportunities this could collide with.

Raw research follows as JSON (the "for" field = the account):

{json.dumps(pool, indent=1)}"""
    write_pack(slugify("guests", args.market), f"Guest map - {len(accounts)} accounts, {args.market}", synthesise(prompt))


def cmd_dinner(key, args):
    queries = [
        ("people", f"{args.audience} based in {args.market}", "linkedin profile", args.results),
        ("people", f"senior {args.audience} at a company headquartered in {args.market}", "linkedin profile", args.results),
        ("companies", f"{args.market} companies hiring {args.audience} or investing in AI search infrastructure", "company", args.results),
    ]
    pool = gather(key, queries)
    print(f"  {len(pool)} candidates gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: cold-start mode - no seller account list exists for {args.market} yet.
Build a discovery guest list for an executive dinner. Audience: {args.audience}.

Produce a markdown pack with exactly these sections:

## Guest list
A table: Name | Role & company | Why this seat | Source. The 8-10 strongest
qualified candidates only. "Why this seat" is one concrete line grounded in
the profile text, never generic.

## Invites
Three personalised invite emails (subject + <=120 word body) for the three
strongest guests, each referencing something specific from their profile text.
Tone: direct, warm, no hype, no exclamation marks. Host is "the Exa team in {args.market}".

## Run of show
A timed run of show for a 6:30pm dinner for 12 (arrival to close), including
the 4pm pre-checks. Practical, not aspirational.

## Gaps
Two or three lines: what this research could not verify and what a human must
check before invites go out (seniority, current role, GDPR-clean sourcing).

Raw research follows as JSON:

{json.dumps(pool, indent=1)}"""
    write_pack(slugify("dinner", args.audience, args.market), f"Dinner brief - {args.audience}, {args.market}", synthesise(prompt))


def cmd_followup(key, args):
    attendees = [a.strip() for a in pathlib.Path(args.attendees).read_text().splitlines() if a.strip()]
    queries = []
    for att in attendees:
        queries.append((att, f"{att} recent work, announcements or writing", None, 2))
    pool = gather(key, queries)
    print(f"  {len(pool)} signals for {len(attendees)} attendees, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: the event happened - {args.event}. These people attended:
{chr(10).join('- ' + a for a in attendees)}

Build the follow-up pack. Nothing sends automatically; every draft goes to a
human. Produce markdown with exactly these sections:

## Follow-up queue
A table: Attendee | Signal since research | Draft angle | Owner. Owner is
"seller" if the research suggests an account conversation, "marketing" if it
is nurture. Priority order: hottest first.

## Drafts
A <=100 word follow-up email per attendee, referencing the event naturally and
one specific thing from their research. Subject included. No hype, no
exclamation marks.

## Handoff notes
One line per seller-owned attendee, written for the CRM: what was discussed,
suggested next step, timing.

## Consent check
Two lines: the lawful-basis note for this follow-up under GDPR (these are
people who attended our event) and what must not happen to this list.

Raw research follows as JSON (the "for" field = the attendee):

{json.dumps(pool, indent=1)}"""
    write_pack(slugify("followup", args.event), f"Follow-up pack - {args.event}", synthesise(prompt))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="field marketing on Exa search")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("market", help="rank cities for the next event")
    m.add_argument("segment")
    m.add_argument("--cities", default="London,Paris,Amsterdam,Munich,Berlin,Stockholm")

    g = sub.add_parser("guests", help="account-based guest map from a target list")
    g.add_argument("accounts", help="file: one account name per line")
    g.add_argument("--market", default="London")
    g.add_argument("--audience", default="engineering and AI platform leadership")

    d = sub.add_parser("dinner", help="cold-start discovery guest list")
    d.add_argument("audience")
    d.add_argument("--market", default="London")
    d.add_argument("--results", type=int, default=10)

    f = sub.add_parser("followup", help="post-event follow-up pack")
    f.add_argument("attendees", help="file: one 'Name - role, company' per line")
    f.add_argument("--event", required=True)

    args = ap.parse_args()
    key = load_key()
    print(f"field-agent {args.cmd}")
    {"market": cmd_market, "guests": cmd_guests, "dinner": cmd_dinner, "followup": cmd_followup}[args.cmd](key, args)


if __name__ == "__main__":
    main()
