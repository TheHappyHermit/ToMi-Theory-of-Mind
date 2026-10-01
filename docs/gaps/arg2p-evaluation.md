# Arg2P: what it is, and whether it fits a self-hosted repo

Investigated 2026-09-29 because the research survey recommended it as the
one genuine dependency for the epistemology region. the operator's constraint:
everything self-hosted, no metered API, no data leaving the house, and the
repo must stay universal across platforms.

## What it actually is

Arg2P (tuProlog/arg2p-kt) is a Kotlin implementation of ASPIC+ structured
argumentation, built on the tuProlog engine. 137 Kotlin files, MIT, ~960
commits. It is a library, not a service: you feed it an argument framework
and a semantics, and it returns which arguments are accepted, rejected, or
undefeated under that semantics.

Why it was recommended: our `epistemology/defeater_graph.py` implements
Pollock-style defeaters, an older and weaker formalism that ASPIC+ subsumes.
Arg2P is the best-maintained implementation of the stronger formalism.

## The platform question, answered with evidence

There are TWO distributions and they behave completely differently.

**1. JVM (Gradle/Maven)**
- Requires a JDK. Kotlin/JVM runs on Linux, macOS and Windows equally --
  the repo ships `gradlew` AND `gradlew.bat`, so Windows is a first-class
  target, not an afterthought.
- This does NOT make the repo less universal than Docker. It makes it
  depend on a JVM instead of a Docker daemon. On the machines the operator cares
  about, a JDK is a far smaller ask than a working Docker engine -- and the
  audit of our own installer already found that Docker-daemon detection is
  one of its weakest points (claim 2 in the external audit).

**2. NPM (`@tuprolog/arg2p`)**
- 9.9 MB installed, 56 packages, **no JVM bundled** -- pure JS.
- Runs on Node on any platform. No Docker, no JVM, no native build.

## The finding that disqualifies the npm route

The npm build does not actually solve anything. Running the project's own
README example:

    const g = arg2p.solve('arg2p::solve', `f1 :=> d.
f2 :=> -d.`, `...`);

returns:

    {"i":{},"query":"'::'(arg2p, solve)"}

That is a query echo, not a solved framework. Instrumenting
`net.Socket.prototype.connect` to catch any socket opened during the call
shows **none**. The declared dependency `sync-request`/`sync-rpc` is
present, which means the bridge is designed to proxy to a Prolog engine
over the network, and the failure mode is a SILENT no-op rather than an
error.

That is the worst kind of failure for a knowledge system: it returns
without complaining and the caller has to notice the empty result. A
check that cannot fail is not a check, and a solver that silently returns
its own query is worse than no solver.

## Recommendation

**Do not adopt Arg2P now.** Two reasons, in order:

1. The npm route is a silent no-op, and the JVM route adds a JDK
   dependency to a Python codebase for a formalism we do not yet
   implement correctly anyway.
2. `epistemology/agm.py` is 82 lines with no deductive closure, no
   remainder computation and no partial ordering. It does not implement AGM.
   Adding a correct argumentation engine on top of an incorrect belief
   revision layer fixes the wrong end of the problem.

**Revisit when `agm.py` is actually AGM.** At that point the question
becomes real: either implement ASPIC+ properly, or take the JVM dependency.
Read `atlas_core/revision/agm.py` (Apache-2.0, 15KB of real code) first --
it is a reference implementation of the same theory in Python, with no new
runtime dependency at all, and is the cheaper first step.

**If Arg2P is ever adopted, use the JVM build and containerise it**, not
npm. That keeps the JVM off the host and matches how the rest of the stack
is deployed.
