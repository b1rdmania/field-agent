#!/usr/bin/env python3
"""field-agent: field marketing research on Exa search.

Ask one question. Exa gathers sourced signals. Claude qualifies them and
writes one markdown pack to out/. Nothing ever contacts anyone.

The three main commands:

  events    where competitors show up in a region, and the white space
  mirror    the region's mirror of the existing customer base, by city
  cohosts   who already runs recurring rooms for an audience in a city
  attendees a Luma guest list matched to the target list, as a workbook

Usage:
  python3 field_agent.py events --competitors "Tavily, Firecrawl, Perplexity" --region EMEA
  python3 field_agent.py mirror customers.txt --region EMEA
  python3 field_agent.py cohosts London --audience "AI developers"
  python3 field_agent.py attendees guests.csv --accounts targets.txt --event "Demo night"

Other commands (narrative, sidebar, market, competitors, expand, guests,
brief, venues, dinner, followup, playbook) are listed by --help.
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
    prompt += ("\n\nWriting rules. Plain English. Sentences of 20 words or fewer. "
               "Active voice. One idea per sentence. No semicolons, no dashes as "
               "punctuation, no brackets in prose. No hedging words: say what the "
               "source shows or say the research did not find it. Table cells are "
               "one short phrase or one sentence. Keep every fact, date, number and "
               "source URL.\n\n"
               "Return the complete markdown pack as your reply text, "
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
    clean = ("".join(c if c.isalnum() or c == " " else " " for c in p) for p in parts if p)
    return "-".join("-".join(p.lower().split())[:24] for p in clean)


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


def cmd_competitors(key, args):
    t = args.target
    queries = [
        ("peers", f"company competing directly with {t}", "company", 8, None),
        ("comparisons", f"{t} vs alternatives comparison", None, 4, "2025-06-01"),
        ("moves", f"{t} competitor funding round, product launch or partnership announcement", "news", 6, "2025-09-01"),
        ("positioning", f"how {t} is positioned against its competitors", None, 3, "2025-06-01"),
    ]
    pool = gather(key, queries)
    answers = ask(key, [
        f"Who are {t}'s main competitors and how do they differ?",
        f"What has changed in {t}'s competitive market in the last six months?",
    ])
    print(f"  {len(pool)} signals gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: competitive landscape for {t}, written for a GTM team deciding where to
press and what to say in market. Analyst tone: factual, sourced, no trash talk.

Produce markdown with exactly these sections:

## Competitive set
A table: Player | What they actually do | Most recent move | Overlap with {t}.
Only players the research supports; separate direct competitors from adjacent
players. Cut directories and listicles.

## Recent moves
The five most consequential dated events in this market from the research,
newest first, each with its source URL and a one-line "so what".

## Positioning read
Three short paragraphs: where {t} is differentiated, where competitors have
the better story right now, and the claim {t} can make that rivals cannot.
Ground every claim; mark inference as inference.

## White space
Two or three underserved segments or unanswered narratives the research
suggests, each with the evidence that points at it.

## Gaps
What this research could not establish and where a human should dig next.

Cited answers from Exa's answer API:
{json.dumps(answers, indent=1)}

Raw search research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("competitors", t), f"Competitive landscape - {t}", synthesise(prompt))


def cmd_events(key, args):
    comps = [c.strip() for c in args.competitors.split(",") if c.strip()]
    region = args.region
    queries = []
    for comp in comps:
        queries.append((comp, f"{comp} hosted dinner, roundtable, meetup, hackathon or conference sponsorship {region}", None, 4, "2026-01-01"))
    queries += [
        ("calendar", f"AI infrastructure and developer platform conferences {region} 2026 sponsors exhibitors", None, 6, "2026-01-01"),
        ("formats", f"AI company executive dinner or roundtable series for enterprise buyers {region}", None, 4, "2025-10-01"),
    ]
    pool = gather(key, queries)
    answers = ask(key, [
        f"What events have {', '.join(comps)} run, hosted or sponsored in {region} in 2026, and in what formats?",
        f"Which {region} conferences in 2026 attract enterprise AI platform buyers, and which AI infrastructure vendors are visibly present?",
    ])
    print(f"  {len(pool)} signals gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: a competitor events radar for {region}, written for a field marketer
deciding where to show up next. The competitive set: {', '.join(comps)}.
Analyst tone: factual, sourced, no trash talk.

Produce markdown with exactly these sections:

## The radar
A table: Competitor | Event footprint found | Format | Where | Source.
One row per competitor in the set. "No public event footprint found in this
research" is a real finding - state it plainly rather than padding. Only
events the research actually supports, each with a date where the source
gives one.

## The calendar
The {region} anchor events this research surfaced, dated, newest first,
each with who from the competitive set is visibly present and its source
URL. Conferences only count if the research shows the buyer audience, not
just the name.

## The read
Two short paragraphs: what the set's event behaviour says about how this
category does field marketing in {region}, and where the white space is -
formats, cities or audiences nobody in the set occupies. Ground every claim;
mark inference as inference. If the footprints are thin, say what THAT
means rather than inventing presence.

## Gaps
What this research could not establish and where a human should dig next.

Cited answers from Exa's answer API:
{json.dumps(answers, indent=1)}

Raw search research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("events", region), f"Competitor events radar - {region}", synthesise(prompt))


def cmd_mirror(key, args):
    """EMEA companies that mirror the existing (US) customer base."""
    seeds = read_lines(args.seeds)
    region = args.region
    stems = ["".join(c for c in a.lower() if c.isalnum()) for a in seeds]
    pool, seen = [], set()

    def keep(seed, r, how):
        url = r.get("url") or ""
        domain = url.split("//")[-1].split("/")[0]
        if not url or url in seen or any(d in domain for d in DIRECTORY_DOMAINS + SELF_NOISE):
            return
        if any(st and st in domain.replace("-", "") for st in stems):
            return
        seen.add(url)
        pool.append({"mirrors": seed, "how": how, "title": r.get("title"), "url": url,
                     "text": (r.get("text") or "")[:700]})

    for seed in seeds:
        q = f"company like {seed} headquartered in {region}: same kind of product, same kind of buyer"
        print(f"  exa search: [{seed}] {q}")
        try:
            for r in exa_search(key, q, args.per_seed, "company"):
                keep(seed, r, "search")
        except Exception as e:
            print(f"  ! search failed for {seed}: {e}")
        try:
            url = resolve_homepage(key, seed)
            print(f"  exa findSimilar: {seed} ({url})")
            for r in exa_similar(key, url, args.per_seed):
                keep(seed, r, "findSimilar")
        except Exception as e:
            print(f"  ! findSimilar failed for {seed}: {e}")
    answers = ask(key, [
        f"Which {region} cities have the densest clusters of companies building AI agents, AI coding tools, or AI-native software in 2026?",
        f"Which {region} startups and scale-ups building AI products publicly use web search or retrieval APIs in their agents?",
    ])
    print(f"  {len(pool)} candidates gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: the existing customer base is mostly US software companies. Seeds:
{', '.join(seeds)}. Find the {region} mirror of that base: the companies
here that look like those customers - same kind of product, same kind of
buyer. Companies only. Never name an individual.

Produce markdown with exactly these sections:

## The mirror
A table: Company | City | Mirrors | What they build | Why they fit | Source.
Only companies the research supports as {region}-based (HQ or a real
engineering office) and plausible buyers of a search API for agents. Cut
consultancies, directories, media and junk hits, with no commentary.
City must come from the source text; write "unconfirmed" if it does not.

## Clusters
A table: City | Companies in the mirror | Dominant type | Read.
Then two or three sentences on what the clustering says about where field
activity concentrates first and what format fits each cluster (developer
room vs vertical room).

## Where the mirror breaks
Two short lists. Seed types with no {region} twin found in this research.
{region} clusters with no seed precedent (a local pattern the US base
does not show). Ground both in the research; mark inference as inference.

## Gaps
What this research could not establish and what a human checks next.

Cited answers from Exa's answer API:
{json.dumps(answers, indent=1)}

Raw research as JSON (the "mirrors" field = the seed it was found from):
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("mirror", region), f"Customer mirror - {region}", synthesise(prompt))


def cmd_cohosts(key, args):
    """Who already runs recurring rooms for an audience in a city."""
    city, audience = args.city, args.audience
    queries = [
        ("luma", f"{audience} meetup {city}", None, 10, "2026-01-01"),
        ("luma-2", f"{city} AI builders monthly event", None, 10, "2026-01-01"),
        ("meetup", f"{audience} {city} recurring meetup group", None, 6, "2025-09-01"),
        ("hack", f"{city} AI hackathon evening community organisers 2026", None, 6, "2026-01-01"),
        ("series", f"{audience} {city} event series sponsors partners 2026", None, 6, "2026-01-01"),
    ]
    # Luma and Meetup pages carry the cadence and the sizes; pull them directly.
    pool = []
    for label, q, cat, num, since in queries:
        domains = ["lu.ma", "luma.com"] if label.startswith("luma") else (["meetup.com"] if label == "meetup" else None)
        print(f"  exa search: [{label}] {q}")
        try:
            body = {"query": q, "numResults": num, "startPublishedDate": since,
                    "contents": {"text": {"maxCharacters": 1200}}}
            if domains:
                body["includeDomains"] = domains
            for r in exa_post(key, "/search", body)["results"]:
                if r.get("url") in {x["url"] for x in pool}:
                    continue
                pool.append({"for": label, "title": r.get("title"), "url": r.get("url"),
                             "published": r.get("publishedDate"), "text": (r.get("text") or "")[:1200]})
        except Exception as e:
            print(f"  ! search failed, skipping: {e}")
    answers = ask(key, [
        f"Which recurring meetups, demo nights or hackathon series for {audience} run in {city} in 2026, who organises them, and how often?",
        f"Which AI companies co-host or sponsor community events for {audience} in {city} in 2026?",
    ])
    print(f"  {len(pool)} signals gathered, synthesising...")
    prompt = f"""{EXA_CONTEXT}

Task: a field marketer wants to co-host in {city} with whoever already owns
the room for {audience}, rather than build a list from zero. Map the
recurring formats. Name organisations and formats, never individuals -
write "the organiser" where a source names a person.

Produce markdown with exactly these sections:

## Recurring rooms
A table: Format | Run by (organisation) | Cadence | Typical size | Audience | Last seen | Source.
Only formats the research shows running more than once, or announced as a
series. Size and cadence from the source text; write "not stated" otherwise.

## One-offs worth knowing
A short list of single events in the research that show who can pull
{audience} in {city}: format, organiser (organisation), date, size if stated.

## Partner read
Two short paragraphs. Which rooms hold the list a search-API company would
want, and why. Which formats fit a partner slot (a demo, a track, a
sponsor) versus a room that already has a vendor attached. Ground every
claim; mark inference as inference.

## Gaps
What this research could not establish and what a human checks next.

Cited answers from Exa's answer API:
{json.dumps(answers, indent=1)}

Raw research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("cohosts", city), f"Co-host map - {audience}, {city}", synthesise(prompt))


def cmd_narrative(key, args):
    """Which words a category is putting on stage, and who owns them."""
    themes = [t.strip() for t in args.themes.split(",") if t.strip()] if args.themes else []
    comps = [c.strip() for c in args.competitors.split(",") if c.strip()] if args.competitors else []
    cat, region = args.category, args.region  # category defaults to Exa's
    queries = [
        ("agendas", f"{cat} conference 2026 {region} agenda keynote session titles", None, 8, "2025-11-01"),
        ("stages", f"{cat} keynote speaker announcement {region} 2026", None, 6, "2025-11-01"),
        ("emerging", f"what is changing in {cat} 2026 analysts and operators", None, 6, "2026-01-01"),
    ]
    for t in themes:
        queries.append((t, f'"{t}" {cat} conference panel keynote 2026', None, 5, "2025-11-01"))
    for comp in comps:
        queries.append((comp, f"{comp} positioning messaging what they say they are 2026", None, 3, "2025-11-01"))
    pool = gather(key, queries)
    qs = [f"Which themes and phrases dominate {cat} conference agendas in {region} in 2026?"]
    if themes:
        qs.append(f"Who is publicly associated with the phrases {', '.join(themes)} in {cat}, and where have they said it?")
    answers = ask(key, qs)
    print(f"  {len(pool)} signals gathered, synthesising...")
    seeded = f"Themes to test specifically: {', '.join(themes)}." if themes else "No themes seeded - surface them from the research."
    watched = f"Companies to watch: {', '.join(comps)}." if comps else ""
    prompt = f"""{EXA_CONTEXT}

Task: a narrative radar for {cat} in {region}. Not where competitors show up -
what the category is SAYING, and who has annexed which words. Written for a
field marketer deciding what a room should be about. {seeded} {watched}
Analyst tone: factual, sourced. Language is cheap and vendors repeat each
other, so be hard about the difference between a phrase with buyers and
evidence behind it and a phrase that is only vendor marketing.

Produce markdown with exactly these sections:

## The themes
A table: Theme | Who is putting it on stage | Where and when | Rising, steady
or fading | Source. Only themes the research supports, each with a dated
instance. Rising/fading is an inference - mark it as one.

## Who owns what
Which company has effectively annexed which phrase, and how firmly. A phrase
one vendor says once is not owned. A phrase carried by a named recurring
format, a keynote slot or a series is. Say which of the two each case is,
and name the format doing the work.

## Unclaimed
Themes that show up in operator, analyst or buyer conversation in the
research but are absent from stages - or present on stages with nobody
credible attached. This is the section that matters most. For each, say what
evidence suggests demand, and what would have to be true for it to carry a
room rather than a panel.

## The read
Two short paragraphs: where this category's language is actually moving, and
the honest risk that a theme is vendor noise rather than buyer pull. If the
research cannot separate the two, say so rather than picking.

## Gaps
What this could not establish and where a human digs next.

Cited answers from the answer API:
{json.dumps(answers, indent=1)}

Raw search research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("narrative", cat, region), f"Narrative radar - {cat}, {region}", synthesise(prompt))


def cmd_sidebar(key, args):
    """The unofficial programme around one anchor conference."""
    ev, city = args.event, args.city
    comps = [c.strip() for c in args.competitors.split(",") if c.strip()] if args.competitors else []
    queries = [
        ("side", f"{ev} side events satellite parties fringe programme {city}", None, 8, "2025-11-01"),
        ("hosts", f"who hosts private dinners and invite-only events during {ev}", None, 6, "2025-11-01"),
        ("venues", f"private event venues walking distance from {ev} venue {city}", None, 5, None),
        ("attendees", f"{ev} who attends seniority buyer profile agenda", None, 4, "2025-11-01"),
    ]
    for c in comps:
        queries.append((c, f"{c} {ev} side event dinner party breakfast", None, 3, "2025-11-01"))
    pool = gather(key, queries)
    answers = ask(key, [
        f"What unofficial side events, private dinners and fringe programming happen around {ev} in {city}?",
        f"Who actually attends {ev}, and at what seniority?",
    ])
    print(f"  {len(pool)} signals gathered, synthesising...")
    watched = f"Competitors to check for: {', '.join(comps)}." if comps else ""
    prompt = f"""{EXA_CONTEXT}

Task: map the unofficial programme around {ev} in {city} - the week, not the
floor. Written for a field marketer who is already going and wants the week to
produce meetings rather than badge scans. {watched}
Analyst tone: factual, sourced. Do not invent events.

Produce markdown with exactly these sections:

## The fringe
A table: What | Who runs it | Format | When in the week | Source. Everything
the research supports that happens around the conference but is not on the
official agenda. Dated where a source gives a date.

## The shape of the week
When the buyer's attention is actually available. Which slots are contested
(everyone runs a party), which are open. Ground this in what the research
shows about the official agenda's rhythm - keynote mornings, expo hours,
the night the big party happens - rather than assuming. Mark inference.

## Where a room fits
Two or three specific slots worth taking, each with the reason it is open and
the format that suits it. Be concrete about time of day. If the honest answer
is that every good slot is taken, say that instead of inventing a gap.

## Logistics that decide it
Venue proximity, walking distance, the practical constraints the research
surfaced. Cost anchors only if a source gives one - never estimate a price.

## The read
One paragraph: whether this conference rewards a fringe play at all, or
whether the attention is genuinely on the floor.

## Gaps
What this could not establish and where a human digs next.

Cited answers from the answer API:
{json.dumps(answers, indent=1)}

Raw search research as JSON:
{json.dumps(pool, indent=1)}"""
    write_pack(slugify("sidebar", ev), f"Fringe map - {ev}, {city}", synthesise(prompt))


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

def read_luma_csv(path):
    """Rows from a Luma guest export. Column names vary, so match by meaning."""
    import csv
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit(f"no rows in {path}")

    def col(*needles):
        for k in rows[0].keys():
            lk = k.lower()
            if all(n in lk for n in needles):
                return k
        return None

    c_name, c_email = col("name"), col("email")
    c_company = col("company") or col("organi")
    c_title = col("title") or col("role") or col("job")
    c_status = col("approval") or col("status")
    c_checkin = col("check")
    out = []
    for r in rows:
        email = (r.get(c_email) or "").strip() if c_email else ""
        company = (r.get(c_company) or "").strip() if c_company else ""
        if not company and "@" in email:
            domain = email.split("@", 1)[1].lower()
            if domain not in FREEMAIL:
                company = domain.split(".")[0]
        status = (r.get(c_status) or "").strip().lower() if c_status else ""
        checked = bool((r.get(c_checkin) or "").strip()) if c_checkin else False
        out.append({
            "name": (r.get(c_name) or "").strip() if c_name else "",
            "company": company,
            "title": (r.get(c_title) or "").strip() if c_title else "",
            "registered": status in ("", "approved", "going", "registered", "yes"),
            "attended": checked,
        })
    return out


def read_luma_api(event_id):
    """Guests from the Luma API. Needs LUMA_API_KEY (Luma Plus)."""
    key = os.environ.get("LUMA_API_KEY")
    if not key:
        sys.exit("set LUMA_API_KEY, or export the guest list as CSV")
    out, cursor = [], None
    while True:
        url = f"https://api.lu.ma/public/v1/event/get-guests?event_api_id={event_id}"
        if cursor:
            url += f"&pagination_cursor={cursor}"
        r = subprocess.run(["curl", "-s", "--fail-with-body", url,
                            "-H", f"x-luma-api-key: {key}"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            sys.exit(f"luma api failed: {r.stdout[:300]}")
        data = json.loads(r.stdout)
        for e in data.get("entries", []):
            g = e.get("guest", e)
            answers = {a.get("label", "").lower(): a.get("answer", "")
                       for a in g.get("registration_answers", [])}
            company = next((v for k, v in answers.items() if "company" in k), "")
            title = next((v for k, v in answers.items() if "title" in k or "role" in k), "")
            email = g.get("email", "") or ""
            if not company and "@" in email:
                domain = email.split("@", 1)[1].lower()
                if domain not in FREEMAIL:
                    company = domain.split(".")[0]
            out.append({"name": g.get("name", ""), "company": company, "title": title,
                        "registered": g.get("approval_status", "approved") == "approved",
                        "attended": bool(g.get("checked_in_at"))})
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            break
    return out


FREEMAIL = ("gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com",
            "icloud.com", "me.com", "proton.me", "protonmail.com", "live.com")


def stem(name):
    return "".join(c for c in name.lower() if c.isalnum())


def match_account(company, accounts):
    """The target account a company name matches, or empty."""
    cs = stem(company)
    if not cs:
        return ""
    for a in accounts:
        a_s = stem(a)
        if a_s and (a_s in cs or cs in a_s):
            return a
    return ""


def enrich_companies(key, companies):
    """One Exa company search per unique company. What they build, where, source."""
    found = {}
    for c in companies:
        if not c or c in found:
            continue
        print(f"  exa search: [company] {c}")
        try:
            hits = exa_search(key, f"{c} company: what it builds and where it is based", 1, "company")
        except Exception as e:
            print(f"  ! search failed for {c}: {e}")
            hits = []
        if hits:
            h = hits[0]
            lines = [l for l in (h.get("text") or "").splitlines() if l.strip() and not l.lstrip().startswith("#")]
            text = " ".join(" ".join(lines).split())
            found[c] = {"about": text[:160], "url": h.get("url", "")}
        else:
            found[c] = {"about": "", "url": ""}
    return found


def write_xlsx(path, sheets):
    """Minimal .xlsx writer. sheets = [(name, rows)], rows = lists of cells."""
    import zipfile
    from xml.sax.saxutils import escape

    def sheet_xml(rows):
        body = []
        for i, row in enumerate(rows, 1):
            cells = []
            for j, v in enumerate(row):
                ref = f"{chr(65 + j) if j < 26 else 'A' + chr(65 + j - 26)}{i}"
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    cells.append(f'<c r="{ref}"><v>{v}</v></c>')
                else:
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(v))}</t></is></c>')
            body.append(f'<row r="{i}">{"".join(cells)}</row>')
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<sheetData>{"".join(body)}</sheetData></worksheet>')

    ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          f'xmlns:r="{ns_r}"><sheets>']
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    ctypes = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
              '<Default Extension="xml" ContentType="application/xml"/>',
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>']
    for n, (name, _) in enumerate(sheets, 1):
        wb.append(f'<sheet name="{escape(name)}" sheetId="{n}" r:id="rId{n}"/>')
        rels.append(f'<Relationship Id="rId{n}" Type="{ns_r}/worksheet" Target="worksheets/sheet{n}.xml"/>')
        ctypes.append(f'<Override PartName="/xl/worksheets/sheet{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
    wb.append('</sheets></workbook>')
    rels.append('</Relationships>')
    ctypes.append('</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ctypes))
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        for n, (_, rows) in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{n}.xml", sheet_xml(rows))


def cmd_attendees(key, args):
    """Luma guest list in. Companies matched to the target list. Workbook out."""
    guests = read_luma_api(args.luma_event) if args.luma_event else read_luma_csv(args.source)
    accounts = read_lines(args.accounts) if args.accounts else []
    companies = sorted({g["company"] for g in guests if g["company"]})
    info = enrich_companies(key, companies)

    header = ["Name", "Company", "Title", "Target account", "Registered", "Attended",
              "What the company builds", "Source", "Seller owner", "Next step"]
    rows = [header]
    hit_accounts = set()
    for g in guests:
        acct = match_account(g["company"], accounts)
        if acct and g["attended"]:
            hit_accounts.add(acct)
        i = info.get(g["company"], {})
        rows.append([g["name"], g["company"], g["title"], acct,
                     "yes" if g["registered"] else "no", "yes" if g["attended"] else "no",
                     i.get("about", ""), i.get("url", ""), "", ""])

    registered = sum(1 for g in guests if g["registered"])
    attended = sum(1 for g in guests if g["attended"])
    ledger_header = ["Event", "Date", "Format", "City", "Cost", "Invited", "Registered", "Attended",
                     "Target accounts on list", "Target accounts attended", "Meetings booked",
                     "Opportunities", "Pipeline sourced"]
    ledger_row = [args.event, args.date, args.format, args.city, args.cost, args.invited,
                  registered, attended, len(accounts), len(hit_accounts), "", "", ""]

    OUT.mkdir(exist_ok=True)
    path = OUT / f"{slugify('attendees', args.event)}.xlsx"
    write_xlsx(path, [("Attendees", rows), ("Event ledger", [ledger_header, ledger_row])])

    ledger = OUT / "ledger.csv"
    import csv
    new = not ledger.exists()
    with open(ledger, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(ledger_header)
        w.writerow(ledger_row)

    print(f"  {len(guests)} guests, {registered} registered, {attended} attended, "
          f"{len(hit_accounts)} of {len(accounts)} target accounts in the room")
    print(f"  wrote {path}")
    print(f"  ledger row appended to {ledger}")


def main():
    ap = argparse.ArgumentParser(description="field marketing on Exa search")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("market", help="rank cities for the next event")
    m.add_argument("segment")
    m.add_argument("--cities", default="London,Paris,Amsterdam,Munich,Berlin,Stockholm")

    c = sub.add_parser("competitors", help="competitive landscape for a company or space")
    c.add_argument("target")

    ev = sub.add_parser("events", help="competitor events radar for a region")
    ev.add_argument("--competitors", required=True, help='comma list: "Tavily, Firecrawl, Perplexity"')
    ev.add_argument("--region", default="EMEA")

    mi = sub.add_parser("mirror", help="the region's mirror of the existing customer base")
    mi.add_argument("seeds", help="file: one existing customer per line")
    mi.add_argument("--region", default="EMEA")
    mi.add_argument("--per-seed", type=int, default=8)

    ch = sub.add_parser("cohosts", help="who already runs recurring rooms for an audience in a city")
    ch.add_argument("city")
    ch.add_argument("--audience", default="AI developers")

    nr = sub.add_parser("narrative", help="what the category says on stage, and who owns which words")
    nr.add_argument("--category", default="AI search and retrieval infrastructure")
    nr.add_argument("--region", default="EMEA")
    nr.add_argument("--themes", default="", help='comma list of phrases to test')
    nr.add_argument("--competitors", default="", help="comma list whose messaging to read")

    sb = sub.add_parser("sidebar", help="the unofficial programme around one anchor conference")
    sb.add_argument("event", help='e.g. "AI Summit London"')
    sb.add_argument("--city", required=True)
    sb.add_argument("--competitors", default="", help="comma list to check for in the fringe")

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

    at = sub.add_parser("attendees", help="Luma guest list to a tracked attendee sheet and an event ledger row")
    at.add_argument("source", nargs="?", help="Luma guest export (.csv)")
    at.add_argument("--luma-event", help="Luma event api id (needs LUMA_API_KEY)")
    at.add_argument("--accounts", help="file: one target account per line")
    at.add_argument("--event", required=True)
    at.add_argument("--date", default="")
    at.add_argument("--format", default="", help="dinner, demo night, coffee morning, hackathon")
    at.add_argument("--city", default="")
    at.add_argument("--cost", default="")
    at.add_argument("--invited", default="")

    p = sub.add_parser("playbook", help="synthesise a market's packs into the inheritable doc")
    p.add_argument("market")
    p.add_argument("--all", action="store_true", help="use every pack in out/")

    args = ap.parse_args()
    key = load_key()
    print(f"field-agent {args.cmd}")
    {"market": cmd_market, "competitors": cmd_competitors, "events": cmd_events, "mirror": cmd_mirror, "cohosts": cmd_cohosts, "expand": cmd_expand,
     "guests": cmd_guests, "brief": cmd_brief, "venues": cmd_venues, "dinner": cmd_dinner,
     "followup": cmd_followup, "playbook": cmd_playbook,
     "narrative": cmd_narrative, "sidebar": cmd_sidebar, "attendees": cmd_attendees}[args.cmd](key, args)


if __name__ == "__main__":
    main()
