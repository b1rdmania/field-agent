# field-agent

Field marketing for one person covering a continent. Give it an audience and a city; it uses [Exa](https://exa.ai) — the search engine for AIs — to build a qualified guest list for an executive dinner, then drafts the personalised invites and the run of show. One command, one markdown briefing pack.

```
python3 field_agent.py "platform engineering leaders" --market London
python3 field_agent.py "heads of AI at insurers" --market Munich
```

Output: [sample brief from a real London run](out/sample-brief-london.md) — guest list with a why-this-seat line per person, three personalised invites, a timed run of show starting with the 4pm checks, and a section on what a human must verify before anything sends.

## How it works

Three Exa searches (LinkedIn-profile and company categories) build a candidate pool with source text. Claude qualifies the pool, writes the invites against each profile, and generates the run of show. A London run costs about two cents of Exa credit.

## Setup

```
export EXA_API_KEY=your-key   # or put it in .env
python3 field_agent.py "your audience" --market YourCity
```

Needs Python 3, curl, and the [Claude Code CLI](https://claude.com/claude-code). No other dependencies.

## Data handling

Research pulls public-source data with citations. Names and personal links never enter version control — real run output is gitignored, the committed sample is redacted, and every brief ends with the verification and consent checks a human owes the guest list before an invite goes out.
