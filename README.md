# field-agent

Four research tools for a field marketing team, built on [Exa](https://exa.ai). Three of them answer a question with a sourced report. The fourth turns a guest list into a tracked spreadsheet. None of them contact anyone.

Each tool starts from the sales team's target list and customer list. It does not replace that list. If no list exists yet, the same tools can help build one.

## 1. Events radar

Where do the competitors run events in a region, and where is the gap?

Input: a list of competitors and a region.
Output: one row per competitor with the events found, the format, the place and the source. Then the region's event calendar with who is present at each. Then the gap: formats, cities and audiences nobody in the set covers.

Report: [the events radar, EMEA](out/sample-events-emea.md). Six competitors. Dated sponsorships for three, no EMEA events for the other three. The gap: no competitor runs a small-room format in EMEA, and RAISE Summit Paris has C-level buyers and no competitor present.

```bash
python3 field_agent.py events --competitors "Tavily, Firecrawl, Perplexity" --region EMEA
```

## 2. Customer mirror

Which companies in a region look like the current customers, and which cities have most of them?

This tool needs the sales team's customer list and US target list as input. The sample uses seven public customers (`customers.txt`) because that is what is public.

Input: a list of customers or target accounts, and a region.
Output: the companies in the region that match, with city, the customer they mirror, what they build, why they fit and the source. Then the count per city. Then where the mirror breaks: customer types with no local match, and local clusters with no US precedent. Companies only. No people.

Report: [the customer mirror, EMEA](out/sample-mirror-emea.md). Twenty-four companies across Munich, Berlin, London, Paris and Zürich. The break: no EMEA twin for Cursor. The report flags one profile that looks out of date.

```bash
python3 field_agent.py mirror customers.txt --region EMEA
```

## 3. Co-host map

Who already runs the room for an audience in a city?

Input: a city and an audience.
Output: the meetups, demo nights and hackathon series that run more than once, with the organisation that runs them, how often, how many people, the audience and the last date seen. Then which of these rooms hold the list a partner would want. Organisations only. No people.

Report: [the co-host map, London AI developers](out/sample-cohosts-london.md). Six recurring rooms and nine one-offs. Two communities hold the list a partner would want, and the report says which slots are paid sponsorship rather than co-host.

```bash
python3 field_agent.py cohosts London --audience "AI developers"
```

## 4. Attendees and ledger

This tool records who came, which target accounts were in the room, and what the event cost.

It is a working draft. It reads a Luma guest export because every field team has one. The last three columns of the ledger belong to the sales system. They stay blank until that system is known.

Input: a Luma guest export (CSV, or the Luma API with a key), the target account list, and the event facts (date, format, city, cost, invited).
Output: one workbook with two sheets. Attendees: name, company, title, target account matched, registered, attended, what the company builds, source, seller owner, next step. The seller fills the last two. Event ledger: one row with invited, registered, attended, target accounts on the list, target accounts attended, meetings booked, opportunities, pipeline sourced. The tool fills the first five from the list. Sales fills the last three. The row also appends to `out/ledger.csv`, so every event lands in one table.

Exa looks up companies, not people. The sample run uses made-up guests at real companies (`sample-guests.csv`, `sample-targets.txt`): [the workbook](out/sample-attendees-demo-night.xlsx) and [the ledger](out/sample-ledger.csv).

```bash
python3 field_agent.py attendees sample-guests.csv --accounts sample-targets.txt \
  --event "Demo night, London" --date 2026-10-15 --format "demo night" --city London --cost 2400 --invited 40
```

## How each tool works

1. Exa collects pages that match the question, through `/search`, `/findSimilar` and `/answer`. Every page keeps its URL.
2. Claude reads the pages. It keeps the claims the page text supports. It marks guesses as guesses. It removes junk.
3. The tool writes one Markdown report to `out/`. The last section lists what the research did not find. The attendees tool skips step 2 and writes a workbook instead.

One Python file, no dependencies. Needs Python 3, curl, the [Claude Code CLI](https://claude.com/claude-code) and `EXA_API_KEY`. One run costs a few cents.

Sample reports name companies and job titles, not people. `--help` lists older commands (narrative, sidebar, market, expand, guests, brief, venues, dinner, followup, playbook); their samples are in `out/`. The newest is [the fringe map for Slush 2026](out/sample-sidebar-slush-2026.md).

License: MIT
