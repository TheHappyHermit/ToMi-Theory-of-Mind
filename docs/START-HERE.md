# Where Hermes Brain Actually Stands

**A plain-English summary. Written to be read, not skimmed.**

If you only read one document in this repo, read this one. Everything else is
either detail behind a link or a working note.

**Date:** 25 September 2026

---

## The one-paragraph version

Most of this project works. The search, the note-versioning, the installer, and
the knowledge base itself are solid and tested. But the "brain-inspired" layer —
the part with names like hippocampus and thalamus — is mostly **built but not
plugged in.** Six of those parts start up and then never do anything. And the
graph search, which we spent real effort building, **measurably makes search
worse.** I only found that out because I finally measured it instead of assuming.

That is the honest state. Nothing is broken. The gap is between what the design
document *says* the system does and what it *actually* does.

---

## Part 1 — The search problem, explained properly

### What the system does now

When you search the knowledge base, two things can happen:

1. **Normal search.** Looks for documents containing the words you typed.
2. **Graph search.** Follows connections between ideas.

You can turn the second one on with `--graph`. When you do, the system shows you
**five results from normal search and five from the graph.**

### What I measured

I picked 8 realistic search questions. For each, I marked which documents in the
vault a person would want to see. Then I checked: of those wanted documents, how
many showed up in the top 10 results?

| How you search | Out of 24 wanted documents, how many you got |
|---|---|
| **Normal search only** | **19** ✅ |
| Graph search only | 2 |
| Both together (what `--graph` does) | 17 |

**Turning the graph on loses you 2 wanted documents out of 24.**

Normal search alone already found everything there was to find. The graph's five
slots pushed out two good results to make room for five results that weren't
wanted.

### Why the graph keeps missing

Here is the actual reason, with no jargon.

You wrote a document about "implementation intentions" — the technique of
deciding *when* to do something later, rather than just *whether* to. In it, you
cite six research papers.

The graph turned your document into a map. Your document is one dot. Those six
papers are six more dots. **The lines all go from your document to the papers.**
Your document points at them. **Nothing points back at your document.**

That's the whole problem, and it's a build problem, not a settings problem.

**What happens when you search:** you type "prospective memory implementation
intentions." The system looks for dots whose *labels* match those words. It finds
dots about the **ideas** — "Prospective Memory," "Gollwitzer 1999." Those are
exactly what you typed, so they rank highest.

**Your own document — the one with your writing in it — never wins**, because
nothing in the map leads to it. It only leads outward.

I checked whether searching deeper would help. It doesn't. I tried looking 1, 2, 3
and 4 steps out. Your document was missing every time, even though it's definitely
in the map with 11 connections.

### What this means

**The graph is good at one thing:** finding related *ideas*.
**It's bad at the thing you actually want:** handing you the *document* to read.

Those are different jobs. We built it for the first one and then credited it with
the second.

### What I'd do

- **Don't turn it on by default.** It currently costs you results.
- **Don't delete it.** Finding related ideas is genuinely useful. It just isn't
  what a document search needs.
- **If we want to fix it,** the change is to make the search value "the document
  that *talks about* this idea" rather than "the idea itself." That's a real
  change to how the search works, not a dial to turn.

I've written this up properly, with the numbers, in
[RETRIEVAL-QUALITY-MEASUREMENT.md](RETRIEVAL-QUALITY-MEASUREMENT.md).

---

## Part 2 — The six brain parts that don't do anything

The project has nine "brain" parts. Think of them as nine small assistants, each
supposed to handle one job — like a memory, a filter, a planner.

**Six of them start up and then never get used.**

| Part | What it's supposed to do | What's actually happening |
|---|---|---|
| Belief revision | Forget things that turn out to be wrong | Starts up, never called |
| Defeater graph | Track what undermines a belief | Starts up, never called |
| Dialectic | Reason out two opposing views | Starts up, never called |
| Counterfactual | "What if I'd done X instead?" | Starts up, never called |
| Time perception | Notice how long a task has been running | Starts up, never called — **and nothing anywhere uses it** |
| Associative graph | Connect related ideas | Starts up, never called |

### The important detail

Three of these **do** show up on the dashboard. Two **do** get exercised by the
automated tests. So it would be wrong to call them "broken" or "deleted code."

The accurate description: **you can look at them, but they never see anything.**

When the agent reads your message, these six don't participate. The design
document describes them as working parts of the system. They aren't.

### Why the code isn't the problem

I ran two of them directly and they work correctly. The problem is purely that
nothing calls them. **The work is done. The wiring isn't.**

### What I'd do

- **Connect two of them.** "Belief revision" is the valuable one — right now the
  system can't drop a belief it's since learned is false, so it can hold
  contradictions forever. The "associative graph" is cheap to connect because its
  search code is already written and tested.
- **Connect "counterfactual" carefully.** There's evidence that "check everything
  constantly" triples the cost and *lowers* accuracy. It should fire at real
  decision points, not continuously.
- **Delete or clearly mark the other three.** "Dialectic" is one normal request to
  the AI, not a subsystem. "Time perception" has no user at all. "Defeater graph"
  does the same job as belief revision — pick one.

### The question underneath

**Are these features, or are they examples in a folder?**

Right now the design document says features. That's the gap. I don't think
anyone was dishonest — but the document describes a system that doesn't exist
yet, and a reader will reasonably assume it does.

---

## Part 3 — The curiosity number

There's a number in the system that goes **up** when something interesting happens
and **down** when things go badly. It appears in a status display.

**Nothing ever uses it to make a decision.**

It goes up, it goes down, it gets printed. That's all.

The code comment says it drives "novelty, knowledge gap reduction, and
exploration." It currently does none of those.

### Why the obvious fix is the wrong fix

The tempting move is to wire it in — "when curiosity is high, have the agent try
something different." We measured that idea, and it's genuinely bad:

- Making an agent pick randomly on purpose performs **exactly the same** as always
  picking the first sensible option. Zero benefit.
- And **9 times out of 10, it picks wrong and never corrects itself.**

There's a worse version of this too, where an AI is trained to be curious. That
one reached **0% success** — permanently. Not "slightly worse." Zero.

### What I'd do

Three options, all fine:

1. Delete it.
2. Keep it, but label it honestly: "displayed, not acted on."
3. Use it for something harmless, like deciding when to suggest exploring a new
   topic — never to make the agent act randomly.

**What's not acceptable:** leaving a number that claims to drive exploration while
driving nothing.

---

## Part 4 — The design document needs a honesty pass

**The research in the big design document is good.** The citations are careful,
the caveats are real, the synthesis is good work. I'm not criticising that.

**The claims at the top are stale or wrong.** Three specific ones:

**"7 brain subsystems."** There are nine. And six of them don't participate.

**"Graph retrieval: implemented and verified."** Verified that it *runs*, yes.
Now measured: it makes search worse.

**The overall framing.** The document reads as though brain-inspired mechanisms
*cause* the good results. The evidence says something different, and I should
state it plainly because it's the honest finding:

> The brain is genuinely useful for deciding **what to measure**.
> It has not been useful for deciding **what makes an agent better**.

Across eleven brain-inspired ideas I researched, every large measured improvement
came from moving a decision out of the AI and into ordinary predictable code.
Not one came from making something more brain-like.

The strongest example: for "remember to do this later," the best big AI scored
**65%**. Move the bookkeeping into normal code and it scored **83%**. A small AI
went from **4% to 66%** — not by thinking better, but by no longer being asked to
think about bookkeeping.

### What I'd do

Keep every mechanism and every citation. Add a short section near the top:

- **What's measured and working**
- **What's built but not connected**
- **What's still just an idea**

A reader who gets the accurate version still thinks this is a good project. A
reader who discovers the gaps themselves stops trusting the whole thing.

---

## Part 5 — Where I got things wrong

You should know these, because I've been confident and wrong more than once.

**I reported a serious bug that doesn't exist.** I said the system couldn't save
beliefs on a fresh install. It can. My test was built wrong — I tested a part in
a way nothing actually uses it. **I had the code that proves it was fine open in
front of me and didn't read it before reporting.** I only read it when you asked
me to fix it. That was careless, and I'm sorry.

**I quoted a research paper's numbers from memory and got them wrong.** The first
figures I gave you came from two different experiments spliced together. Reading
the actual paper, the real numbers are worse than what I said — the conclusion
still held, but I should never have presented unverified numbers as fact.

**I twice reported a password leak that wasn't real.** The tool that shows me
files hides passwords in its output. It made correct configuration look like a
committed secret. Both times I nearly "fixed" something that was already right.

**I wrote 30 documents instead of one answer.** This document exists because of
that.

The pattern in all four: I reached a conclusion before verifying it, and stated
it more confidently than I'd earned.

---

## The short list

If you want me to do something, in this order:

| # | What | Why | Effort |
|---|---|---|---|
| 1 | Stop the graph being on by default | It currently costs you search results | Tiny |
| 2 | Connect belief revision | System can't drop disproven beliefs; code already works | Small |
| 3 | Fix the design document's claims | Right now it oversells | Small |
| 4 | Delete or relabel the curiosity number | It claims to do something it doesn't | Tiny |
| 5 | Decide on the other five brain parts | Feature or example? | Needs your call |
| 6 | Build a real search evaluation | 8 questions isn't enough to be sure | Medium |

**What I would not do:** build more brain-inspired parts. The research is clear
that they lose to simple code, and the two most brain-like things already in the
project are among the weakest performers in the evidence. Adding more would make
this project worse, and we know that before writing any of it.

---

## A note on the other 29 documents

There are about thirty documents in this folder. **They were written for a
technical reader and they are dense.** That was a mistake on my part — you asked
for answers and got a filing cabinet.

If you need something specific, the table below is the map. If it's not in there,
ask me and I'll either answer it directly or write it in plain English.

You do not need to read any of them to use this project or to decide what happens
next. This document is the whole summary.

## Where the detail lives

| If you want | Read |
|---|---|
| The search numbers explained properly | [RETRIEVAL-QUALITY-MEASUREMENT.md](RETRIEVAL-QUALITY-MEASUREMENT.md) |
| The brain-science research, in plain terms | [COGNITIVE-EVIDENCE-REVIEW.md](COGNITIVE-EVIDENCE-REVIEW.md) |
| What the notes know that the code lacks | [COGNITIVE-COVERAGE-REVIEW.md](COGNITIVE-COVERAGE-REVIEW.md) |
| Whether the outside tools are any good | [DEPENDENCY-AUDIT.md](DEPENDENCY-AUDIT.md) |
| Whether the memory system is the right one | [MEMORY-SUBSYSTEM-EVALUATION.md](MEMORY-SUBSYSTEM-EVALUATION.md) |

Those are written for a technical reader. This one is for you.
