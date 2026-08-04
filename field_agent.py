#!/usr/bin/env python3
"""field-agent: a field marketing job spec, implemented.

Eight commands covering the field-marketing loop for one person running a
region, all built on Exa search (/search, /findSimilar, /answer):

  market    which cities deserve the next event, with evidence
  expand    seller gives five accounts; findSimilar returns the lookalikes
  guests    account-based guest mapping: target accounts in, seat map out
  brief     pre-event dossier on one guest or account
  venues    private-dining shortlist and negotiation notes for a city
  dinner    cold-start discovery when no account list exists yet
  followup  post-event: per-attendee brief, draft follow-up, handoff note
  playbook  synthesise every pack for a market into the doc the next hire inherits

Each command writes one markdown pack to out/. Nothing ever sends.

Usage:
  python3 field_agent.py market "AI platform buyers" --cities London,Paris,Munich
  python3 field_agent.py expand accounts.txt --market EMEA
  python3 field_agent.py guests accounts.txt --market London
  python3 field_agent.py brief "Jane Doe, Checkout.com"
  python3 field_agent.py venues London --seats 14
  python3 field_agent.py dinner "platform engineering leaders" --market London
  python3 field_agent.py followup attendees.txt --event "London infra dinner, 12 Aug"
  python3 field_agent.py playbook london
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "out"

EXA = "https://api.exa.ai"

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


def exa_post(key, path, body):
    r = subprocess.run(
        ["curl", "-s", "--fail-with-body", "-X", "POST", EXA + path,
         "-H", f"x-api-key: {key}", "-H", "Content-Type: application/json",
         "-d", json.dumps(body)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stdout[:300] or r.stderr[:300])
    return json.loads(r.stdout)


def exa_search(key, query, num, category=None, since=None):
    body = {"query": query, "numResults": num,
            "contents": {"text": {"maxCharacters": 1200}}}
    if category:
        body["category"] = category
    if since:
        body["startPublishedDate"] = since
    return exa_post(key, "/search", body)["results"]


def exa_similar(key, url, num):
    body = {"url": url, "numResults": num, "excludeSourceDomain": True,
            "contents": {"text": {"maxCharacters": 600}}}
    return exa_post(key, "/findSimilar", body)["results"]


def exa_answer(key, query):
    out = exa_post(key, "/answer", {"query": query, "text": False})
    cites = [c.get("url", "") for c in out.get("citations", [])][:5]
    return {"question": query, "answer": out.get("answer", ""), "citations": cites}


def gather(key, queries):
    """Run (label, query, category, num, since) tuples, dedupe by URL."""
    seen, pool = set(), []
    for label, q, cat, num, since in queries:
        print(f"  exa search: [{label}] {q}")
        try:
            results = exa_search(key, q, num, cat, since)
        except Exception as e:
            print(f"  ! search failed, skipping: {e}")
            continue
        for r in results:
            url = r.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            pool.append({"for": label, "title": r.get("title"), "url": url,
                         "text": (r.get("text") or "")[:1200]})
    return pool


def ask(key, questions):
    out = []
    for q in questions:
        print(f"  exa answer: {q}")
        try:
            out.append(exa_answer(key, q))
        except Exception as e:
            print(f"  ! answer failed, skipping: {e}")
    return out


def synthesise(prompt):
    prompt += ("\n\nReturn the complete markdown pack as your reply text, "
               "starting at the first section heading. Do not write files, "
               "run tools, or describe what you produced.")
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


def read_lines(path):
    return [l.strip() for l in pathlib.Path(path).read_text().splitlines() if l.strip()]


# ---------------------------------------------------------------- commands

def cmd_market(key, args):
    cities = [c.strip() for c in args.cities.split(",")]
    queries = []
    for city in cities:
        queries.append((city, f"{args.segment} at companies headquartered in {city}", "linkedin profile", 5, None))
        queries.append((city, f"major AI and developer infrastructure conferences in {city} 2026", None, 3, "2026-01-01"))
    pool = gather(key, queries)
    answers = ask(key, [
        f"Which European cities have the strongest enterprise buyer community for {args.segment}?",
        "How do corporate event attendance norms differ between UK, DACH, France and the Nordics?",
    ])
    print(f"  {len(pool)} signals gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: recommend where the next quarter of EMEA field events should go for this
segment: {args.segment}. Cities under consideration: {', '.join(cities)}.

Produce a markdown memo with exactly these sections:

## Ranking
A table: City | Buyer density signal | Event landscape | Local norms | Verdict.
Rank all cities. Ground every cell in the research; where the research is thin
for a city, say so rather than inventing.

## Recommendation
Which one or two cities get investment this quarter and what format fits each
(hosted dinner vs conference presence vs roundtable), with a pipeline rationale
a sales leader would accept. Three short paragraphs maximum.

## What would change this call
Two or three lines: the evidence that would reorder the ranking.

Cited answers from Exa's answer API:
{json.dumps(answers, indent=1)}

Raw search research as JSON (the "for" field = the city a hit was gathered for):
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("market", args.segment), f"Market memo - {args.segment}", synthesise(prompt))


DIRECTORY_DOMAINS = ("linkedin.com", "crunchbase.com", "pitchbook.com",
                     "cbinsights.com", "leadiq.com", "wikipedia.org",
                     "glassdoor.", "indeed.", "bloomberg.com", "thepaypers.com")


def resolve_homepage(key, account):
    """Homepage for an account: given domain > exact-match search hit > {name}.com."""
    if "." in account:
        return "https://" + account.lower().removeprefix("https://").removeprefix("http://")
    stem = "".join(c for c in account.lower() if c.isalnum())
    try:
        for h in exa_search(key, f"{account} official company website", 8, "company"):
            domain = (h.get("url") or "").split("//")[-1].split("/")[0].removeprefix("www.")
            if domain.split(".")[0] == stem:
                return h["url"]
    except Exception:
        pass
    return f"https://{stem}.com"


SELF_NOISE = ("play.google.", "apps.apple.", "ycombinator.com")


def cmd_expand(key, args):
    accounts = read_lines(args.accounts)
    stems = ["".join(c for c in a.lower() if c.isalnum()) for a in accounts]
    pool, seen = [], set()

    def keep(acc, r):
        url = r.get("url") or ""
        domain = url.split("//")[-1].split("/")[0]
        if url in seen or any(d in domain for d in DIRECTORY_DOMAINS + SELF_NOISE):
            return
        if any(s and s in domain.replace("-", "") for s in stems):
            return  # the seed's own properties and clones are not lookalikes
        seen.add(url)
        pool.append({"for": acc, "title": r.get("title"), "url": url,
                     "text": (r.get("text") or "")[:600]})

    for acc in accounts:
        q = f"company like {acc}: a direct competitor or peer operating in {args.market}"
        print(f"  exa search: [{acc}] {q}")
        try:
            for r in exa_search(key, q, args.per_account, "company"):
                keep(acc, r)
        except Exception as e:
            print(f"  ! search failed for {acc}: {e}")
        try:
            url = resolve_homepage(key, acc)
            print(f"  exa findSimilar: {acc} ({url})")
            for r in exa_similar(key, url, args.per_account):
                keep(acc, r)
        except Exception as e:
            print(f"  ! findSimilar failed for {acc}: {e}")
    print(f"  {len(pool)} lookalikes gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: sellers named these seed accounts: {', '.join(accounts)}. Exa's
findSimilar API returned the lookalike companies below. Build the expanded
target list for {args.market}.

Produce markdown with exactly these sections:

## Expanded account list
A table: Company | Similar to | Why it fits | Region check. Keep only
companies that plausibly buy AI search infrastructure and operate in
{args.market}; cut consultancies, media sites and junk hits. Note where the
region is unconfirmed.

## Tiering
Tier 1 / Tier 2 with one line of reasoning each - which expanded accounts
deserve a seat at the next event vs a nurture touch.

## Gaps
What the account owner must confirm before any of these enter the programme.

Raw findSimilar research as JSON (the "for" field = the seed account):
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("expand", args.market), f"Account expansion - {len(accounts)} seeds, {args.market}", synthesise(prompt))


def cmd_guests(key, args):
    accounts = read_lines(args.accounts)
    queries = []
    for acc in accounts:
        queries.append((acc, f"{args.audience} at {acc} in {args.market}", "linkedin profile", 4, None))
        queries.append((acc, f"{acc} engineering blog or announcement about AI, search or platform infrastructure", None, 2, "2025-06-01"))
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

Raw research as JSON (the "for" field = the account):
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("guests", args.market), f"Guest map - {len(accounts)} accounts, {args.market}", synthesise(prompt))


def cmd_brief(key, args):
    target = args.target
    queries = [
        ("profile", f"{target} professional profile and role", "linkedin profile", 2, None),
        ("signals", f"{target} recent talk, writing, interview or announcement", None, 4, "2025-08-01"),
        ("company", f"{target.split(',')[-1].strip() if ',' in target else target} AI and platform strategy", None, 2, "2025-06-01"),
    ]
    pool = gather(key, queries)
    print(f"  {len(pool)} signals gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: one guest is confirmed for an upcoming event: {target}. Write the
pre-event dossier the host reads in the taxi. One page maximum.

Produce markdown with exactly these sections:

## Who they are
Three lines: role, remit, trajectory. Grounded in the research only.

## Live signals
The two or three most recent things they have said, written or shipped, each
with its source URL and a one-line "why it matters to this conversation".

## Openers
Three specific conversation openers built from the live signals. No flattery,
no generic industry questions.

## Handle with care
What not to raise, what is unverified, and where the research is stale.

Raw research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("brief", target), f"Guest dossier - {target}", synthesise(prompt))


def cmd_venues(key, args):
    queries = [
        ("venues", f"best private dining room {args.city} corporate dinner {args.seats} guests", None, 6, None),
        ("venues", f"restaurants with private rooms for business dinners in {args.city}", None, 4, None),
    ]
    pool = gather(key, queries)
    answers = ask(key, [
        f"What is a typical minimum spend for a private dining room for {args.seats} in {args.city}?",
        f"What should you check on a venue walkthrough before hosting a corporate dinner in {args.city}?",
    ])
    print(f"  {len(pool)} venue signals gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: shortlist venues for a {args.seats}-seat executive dinner in {args.city}.
The host has hospitality experience; write for a professional, not a tourist.

Produce markdown with exactly these sections:

## Shortlist
A table: Venue | Room | Capacity | Read of the room | Source. Five or six
options from the research, honest about what the sources do and do not say.
Cut listicle filler that gives no private-room specifics.

## Negotiation notes
Minimum spend expectations, what is usually negotiable (room fee vs spend,
midweek rates, wine corkage), grounded in the cited answers where possible.

## Walkthrough checklist
Ten lines the operator checks on the site visit, dinner-specific.

## Gaps
What only a phone call will settle.

Cited answers from Exa's answer API:
{json.dumps(answers, indent=1)}

Raw search research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("venues", args.city), f"Venue shortlist - {args.city}, {args.seats} seats", synthesise(prompt))


def cmd_dinner(key, args):
    queries = [
        ("people", f"{args.audience} based in {args.market}", "linkedin profile", args.results, None),
        ("people", f"senior {args.audience} at a company headquartered in {args.market}", "linkedin profile", args.results, None),
        ("companies", f"{args.market} companies hiring {args.audience} or investing in AI search infrastructure", "company", args.results, None),
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

Raw research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("dinner", args.audience, args.market), f"Dinner brief - {args.audience}, {args.market}", synthesise(prompt))


def cmd_followup(key, args):
    attendees = read_lines(args.attendees)
    queries = [(att, f"{att} recent work, announcements or writing", None, 2, "2025-08-01") for att in attendees]
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

Raw research as JSON (the "for" field = the attendee):
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("followup", args.event), f"Follow-up pack - {args.event}", synthesise(prompt))


def cmd_playbook(key, args):
    packs = sorted(OUT.glob("*.md")) if args.all else sorted(OUT.glob(f"*{args.market.lower()}*.md"))
    packs = [p for p in packs if not p.name.startswith("playbook")]
    if not packs:
        sys.exit(f"no packs in out/ matching '{args.market}' - run the other commands first")
    print(f"  synthesising playbook from {len(packs)} packs: {', '.join(p.name for p in packs)}")
    corpus = "\n\n---PACK---\n\n".join(f"[{p.name}]\n{p.read_text()[:6000]}" for p in packs)
    prompt = f"""{EXA_CONTEXT}

Task: write the {args.market} field playbook - the document the next European
hire inherits so they are faster than the person who wrote it. Source material
is every research pack produced for this market so far, included below.

Produce markdown with exactly these sections:

## What we know about this market
Buyer landscape, live accounts and signals, venue and format notes - only
what the packs actually established, with the pack name cited in brackets.

## What worked, what to repeat
Formats, angles and choreography the packs support.

## Open questions
What the packs flagged as unverified, gathered in one place with owners
(seller / marketing / legal).

## Standing checklists
The reusable lists: pre-event verification, GDPR consent steps, walkthrough
checks, follow-up cadence - deduplicated across packs.

Source packs:
{corpus}"""
    write_pack(slugify("playbook", args.market), f"Field playbook - {args.market}", synthesise(prompt))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="field marketing on Exa search")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("market", help="rank cities for the next event")
    m.add_argument("segment")
    m.add_argument("--cities", default="London,Paris,Amsterdam,Munich,Berlin,Stockholm")

    e = sub.add_parser("expand", help="findSimilar lookalikes from seed accounts")
    e.add_argument("accounts", help="file: one account name per line")
    e.add_argument("--market", default="EMEA")
    e.add_argument("--per-account", type=int, default=8)

    g = sub.add_parser("guests", help="account-based guest map from a target list")
    g.add_argument("accounts", help="file: one account name per line")
    g.add_argument("--market", default="London")
    g.add_argument("--audience", default="engineering and AI platform leadership")

    b = sub.add_parser("brief", help="pre-event dossier on one guest or account")
    b.add_argument("target", help='"Name, Company" or a company name')

    v = sub.add_parser("venues", help="private-dining shortlist for a city")
    v.add_argument("city")
    v.add_argument("--seats", type=int, default=12)

    d = sub.add_parser("dinner", help="cold-start discovery guest list")
    d.add_argument("audience")
    d.add_argument("--market", default="London")
    d.add_argument("--results", type=int, default=10)

    f = sub.add_parser("followup", help="post-event follow-up pack")
    f.add_argument("attendees", help="file: one 'Name - role, company' per line")
    f.add_argument("--event", required=True)

    p = sub.add_parser("playbook", help="synthesise a market's packs into the inheritable doc")
    p.add_argument("market")
    p.add_argument("--all", action="store_true", help="use every pack in out/")

    args = ap.parse_args()
    key = load_key()
    print(f"field-agent {args.cmd}")
    {"market": cmd_market, "expand": cmd_expand, "guests": cmd_guests,
     "brief": cmd_brief, "venues": cmd_venues, "dinner": cmd_dinner,
     "followup": cmd_followup, "playbook": cmd_playbook}[args.cmd](key, args)


if __name__ == "__main__":
    main()
