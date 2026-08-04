# Guest map - 3 accounts, London

> Sample output from a real run against three named accounts. People's names and profile links are redacted: the tool works with public-source data, but personal data stays out of version control.

Built with Exa search + Claude. Research is a starting point, not a send list.

# EMEA Exec Dinner — Guest Map: Revolut, Monzo, Checkout.com

## Account briefs

**Revolut** — Live signal: strong. [redacted] (Group Head of ML Engineering) spoke publicly at RAAIS 2026 about running "AI at scale" inside a regulated bank — his framing was explicit that the hard problem has moved from the model to the surrounding control plane: gateway, governance layer, fallback measurement, cost controls, human review layers, all wrapped around an AI assistant (AIR) sitting in the path of >1 trillion dollars of transactions across 200+ products. That's a company actively wrestling with retrieval/grounding, governance, and reliability at the infrastructure layer — the exact conversation Exa's API is built for. Engineering leadership is also in flux/expansion: [redacted] was promoted into a new Group-level ML role in Apr 2026, and a separate Head of Engineering (Retail) hire ([redacted]) explicitly frames their remit as "building AI-enabled products, platforms." Timely because there's a live, named architectural gap (control plane / governance around models) and fresh leadership mandate to fill it.

**Monzo** — Live signal: moderate, real but earlier-stage. A June 2026 engineering blog post ("Engineering the Future of Customer Operations: The Monzo Ops Agent") states Monzo has "recently begun exploring how Generative AI can elevate the customer experience," building on existing classical ML in fraud/credit/personalisation, with initial focus on customer support and fraud/financial-crime investigation workflows — both of which depend on pulling together customer context, product knowledge, and "real-time context" reliably in a regulated environment. This is genuinely early (they flag reliability/validation standards as the open problem), which makes it a good moment to shape their retrieval approach before it calcifies, but it's less mature than Revolut's or Checkout's live builds.

**Checkout.com** — Live signal: strong and concrete. Two engineering blog posts in mid-2026: "How Agent HAL has become a core part of how Checkout.com ships software" (June 2026) reports their in-house AI coding agent generates 18% of all PRs, deliberately scoped to narrow, bounded tasks embedded in existing process rather than flashy zero-to-one generation; and "Operationalizing AI in Engineering and beyond" (July 2026) frames AI as core to their SDLC performance culture ("No Room for Approximation"). There's also a dedicated Data & AI Engineering platform team (LangChain/LangGraph, stream processing) building internal AI infrastructure. Timely because they're already shipping agentic tooling in production and have a data/AI platform team actively building the plumbing underneath it — a direct fit for a search/retrieval infrastructure conversation.

## Seat map

| Account | Name | Role | Why this seat | Source |
|---|---|---|---|---|
| Revolut | [redacted] | Group Head of Machine Learning Engineering | Owns the exact "control plane around the model" problem he described publicly at RAAIS — governance, gateway, grounding/fallback at trillion-dollar transaction scale; newly promoted (Apr 2026) with a broadened mandate | talk write-up redacted ; profile redacted |
| Revolut | [redacted] | Head of Engineering (Retail) | Explicitly frames his current remit as "building AI-enabled products, platforms" — fresh into the seat (Jan 2026), a buyer shaping new architecture rather than defending an existing one | profile redacted |
| Monzo | [redacted] | VP Product & Tech General Manager | Most senior AI-adjacent exec found — self-describes as "working on AI/ML products," owns the customer support/fraud/fincrime P&L that the Ops Agent blog names as GenAI's first application area | profile redacted |
| Monzo | [redacted] | Software Engineering Manager | Directly builds "Monzo's customer service AI agent" — the same GenAI ops workstream described in the June 2026 blog post; the most concrete technical owner of the live signal | profile redacted ; https://monzo.com/blog/engineering-the-future-of-customer-operations-the-monzo-ops-agent |
| Checkout.com | [redacted] | VP of Engineering | Most senior engineering exec identified; sits above the teams shipping Agent HAL and the AI/SDLC push described in both 2026 blog posts | profile redacted |
| Checkout.com | [redacted] | Senior Data Engineer, Data & AI Engineering | Hands-on owner of the Data & AI Platform team (stream processing, LangChain/LangGraph) — the infrastructure layer a search API conversation would actually plug into | profile redacted |

## In-deal choreography

- **Revolut** — Seat [redacted] next to your most technical Exa voice, not a generalist AE; open with governance/fallback-measurement (his own RAAIS language), and close the table by proposing a working session with his platform team on grounding/retrieval inside their gateway — that's the next meeting, not a follow-up email.
- **Checkout.com** — Seat [redacted] and [redacted] together and let the HAL "18% of PRs" stat be the icebreaker you ask *them* to explain; pivot from "how do you scope agent tasks narrowly" to "how do you ground those agents in fresh external data," and leave with a scoped pilot ask for the Data & AI Engineering team, not just a follow-up call.
- **Monzo** — Because their GenAI effort is still forming (blog says "recently begun"), position this as early input rather than a pitch: seat [redacted] for the strategic/P&L view and [redacted] for the technical reality, ask what's blocking reliability in the Ops Agent today, and turn any concrete gap they name into a scoped technical follow-up with [redacted]'s team.

## Gaps

- **Role currency**: Two of the four Revolut/Checkout LinkedIn profiles ([redacted], [redacted]) and several Checkout profiles show generic "Head/Director of Engineering" titles with no AI-specific signal — excluded from the seat map, but confirm with the account owner whether any of them outrank or gatekeep the people we did select. [redacted]'s and [redacted]'s roles both changed within the last 6 months (Apr 2026, Jan 2026) — verify they haven't moved again since this research was pulled.
- **Existing relationships**: No CRM/relationship data included in this research — before inviting, check whether any seller already has a warm thread to [redacted], [redacted], [redacted], or the others named, and whether they're the right host or should be paired with someone who already has trust.
- **Open opportunities**: Checkout.com and Revolut both show visible internal build activity (Agent HAL, Revolut's AI gateway) — confirm neither is mid-procurement on a competing search/retrieval vendor, and that this dinner doesn't collide with an active Exa opportunity already in motion with a different buyer at the same account.
- **Blog bylines unverified as seats**: Checkout.com's two AI blog posts are authored by "[redacted]" and "[redacted]" — no role given in the source text, so they're excluded from the seat map, but worth a quick check with the account owner since a named author of the flagship AI post could outrank the seats listed here.
