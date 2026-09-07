# field-agent

Research tool for field marketing. You type one question. The tool searches [Exa](https://exa.ai), checks the results, and writes a short report with sources. It does not contact anyone.

## What it answers

**Where do the competitors run events in EMEA? Where is the gap?**
Command: `events`. Report: [the events radar](out/sample-events-emea.md).
The run covered six competitors. It found dated sponsorships for three and no EMEA events for the other three. It found the gap: no competitor runs a small-room format in EMEA, and RAISE Summit Paris has C-level buyers and no competitor present.

**Which EMEA companies look like the current customers? Which cities have most of them?**
Command: `mirror`. Input: a list of current customers (`customers.txt` has seven public ones). Output: the EMEA companies that match, grouped by city, with one reason and one source each. Companies only. No people.

**Who already runs the room for AI developers in one city?**
Command: `cohosts`. Output: the meetups, demo nights and hackathon series that run more than once, with organiser, how often, how many people, and the last date seen. Organisations only. No people.

Each report ends with a list of what the research did not find. Treat each report as a starting point.

## How it works

Step 1. Exa collects pages that match the question, through `/search`, `/findSimilar` and `/answer`. Every page keeps its URL.
Step 2. Claude reads the pages. It keeps claims that the page text supports. It marks guesses as guesses. It removes junk.
Step 3. The tool writes one Markdown file to `out/`.

Personal data does not go into version control. Sample reports name companies and job titles, not people.

## Run it

```bash
git clone https://github.com/b1rdmania/field-agent && cd field-agent
export EXA_API_KEY=your-key
python3 field_agent.py events --competitors "Tavily, Firecrawl, Perplexity" --region EMEA
python3 field_agent.py mirror customers.txt --region EMEA
python3 field_agent.py cohosts London --audience "AI developers"
```

One Python file. No dependencies. You need Python 3, curl, and the [Claude Code CLI](https://claude.com/claude-code). One run costs a few cents of Exa credit.

`python3 field_agent.py --help` lists the older commands: narrative, sidebar, market, expand, guests, brief, venues, dinner, followup, playbook. Their sample reports are in `out/`.

## Why it exists

I ran the events programme for a technology company as the only hire. 35 to 40 events a year in Europe, Asia and the US, reported as pipeline. Most of the work was research: who to invite, why now, what the market is doing, what happens after. This tool does that part. The person who covers a continent then spends the time on the room. [Andy Bird](https://x.com/b1rdmania)

License: MIT
