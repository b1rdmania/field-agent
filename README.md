# field-agent

Ask a field-marketing question in one line. Agents research it on [Exa](https://exa.ai) and write back a sourced brief. It only researches. It never contacts anyone.

## Three questions, three runs

**Where do the competitors show up in EMEA, and where is the white space?**
[The events radar](out/sample-events-emea.md). Six competitors, one region. Dated sponsorships for three of them, a plainly stated zero for the other three, and the anchor calendar with who is present at each. The white space: nobody in the set runs a small-room format in EMEA, and RAISE Summit Paris draws C-level buyers with no competitor present.

**Which EMEA companies mirror the existing customer base, and where do they cluster?**
[The customer mirror](out/sample-mirror-emea.md). Seven public customers in, the EMEA companies that look like them out, grouped by city. Companies only, no people. The clusters decide where field activity concentrates first and which format fits each city.

**Who already runs the room in London?**
[The co-host map](out/sample-cohosts-london.md). The recurring meetups, demo nights and hackathon series for AI developers in one city, with organiser, cadence, size and last seen. Field marketing at a search-API company co-hosts with whoever owns the list. This finds them.

Each pack ends with a gaps section: what the research could not establish and what a human checks next. The verdicts are starting points, not settled calls.

## How it works

Two stages. Exa gathers sourced signals through `/search`, `/findSimilar` and `/answer`. Claude qualifies them: every claim grounded in source text, inference marked as inference, junk cut. Personal data stays out of version control. Committed samples name companies and roles, not people.

## Run it

```bash
git clone https://github.com/b1rdmania/field-agent && cd field-agent
export EXA_API_KEY=your-key
python3 field_agent.py events --competitors "Tavily, Firecrawl, Perplexity" --region EMEA
python3 field_agent.py mirror customers.txt --region EMEA
python3 field_agent.py cohosts London --audience "AI developers"
```

One file, stdlib only. Needs Python 3, curl, and the [Claude Code CLI](https://claude.com/claude-code). A run costs a few cents of Exa credit. `--help` lists the older commands (narrative, sidebar, market, expand, guests, brief, venues, dinner, followup, playbook); their samples are in `out/`.

## Why this exists

I ran a global events programme for a technology company as the only hire: 35 to 40 activations a year across Europe, Asia and the US, reported as pipeline. The research load is most of the job and almost none of the craft. This is that load, automated, so the person covering a continent spends their time on the room. [Andy Bird](https://x.com/b1rdmania)

License: MIT
