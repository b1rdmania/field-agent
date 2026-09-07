# field-agent

Field marketing research on [Exa](https://exa.ai). Three tools. Each one takes a question, searches Exa, checks the results, and writes a report with sources. None of them contact anyone.

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

Input: a list of current customers (`customers.txt` has seven public ones) and a region.
Output: the companies in the region that match, with city, the customer they mirror, what they build, why they fit and the source. Then the count per city. Then where the mirror breaks: customer types with no local match, and local clusters with no US precedent. Companies only. No people.

```bash
python3 field_agent.py mirror customers.txt --region EMEA
```

## 3. Co-host map

Who already runs the room for an audience in a city?

Input: a city and an audience.
Output: the meetups, demo nights and hackathon series that run more than once, with the organisation that runs them, how often, how many people, the audience and the last date seen. Then which of these rooms hold the list a partner would want. Organisations only. No people.

```bash
python3 field_agent.py cohosts London --audience "AI developers"
```

## How each tool works

1. Exa collects pages that match the question, through `/search`, `/findSimilar` and `/answer`. Every page keeps its URL.
2. Claude reads the pages. It keeps the claims the page text supports. It marks guesses as guesses. It removes junk.
3. The tool writes one Markdown report to `out/`. The last section lists what the research did not find.

One Python file, no dependencies. Needs Python 3, curl, the [Claude Code CLI](https://claude.com/claude-code) and `EXA_API_KEY`. One run costs a few cents.

Sample reports name companies and job titles, not people. `--help` lists older commands (narrative, sidebar, market, expand, guests, brief, venues, dinner, followup, playbook); their samples are in `out/`.

License: MIT
