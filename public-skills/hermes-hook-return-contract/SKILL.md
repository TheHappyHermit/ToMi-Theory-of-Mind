---
name: hermes-hook-return-contract
description: Use when a Hermes hook must block or deny.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Hermes Hook Return Contract

A hook that runs is not a hook that works. Before designing a hook, know which
events consume the return value — that single fact determines what your hook can
and cannot do.

## The Rule

The hook registry has two emit paths, and they behave differently:

| Emit path | Used by | Return value |
|---|---|---|
| `emit()` | most events, including `agent:start` and `agent:step` | **discarded** |
| `emit_collect()` | `command:*` events only | consumed |

Consequence: a handler on `agent:start` or `agent:step` can perform side
effects — write state, call a service, log, cache — but **cannot influence the
turn it is attached to**. To inject text into the model's context you would need
a core change that honours those returns. If a feature requires it, say so and
stop; do not quietly patch core.

## Denial Contract

Because most events discard returns, the only supported way to actually block
something is a `command:*` handler returning:

```python
{"decision": "deny", "message": "<explanation>"}
```

Any other key on a discarded event is a no-op. In particular, do **not** use:

- `advisory` — nothing reads it;
- `halt` — ineffective on ignored events;
- a bare string, boolean, or `{"block": ...}` shape.

A guard written with the wrong key looks correct in review and enforces nothing,
which is worse than having no guard: the code reads as a safety net that is
absent at runtime.

## Design Procedure

1. **Pick the event by required capability**, not by name intuition.
   - Need to *block* → `command:*`, and return `decision: deny`.
   - Need to *observe / feed state / warm a cache* → `agent:start` or
     `agent:step`, with side effects only.
   - Need to *inject context* → there is no existing event; stop and report it.
2. **Verify the event is real** before writing the handler — confirm the emitter
   and that your return shape is the one that path reads. Do not assume a
   symmetric API across events.
3. **Confirm the endpoint exists** by reading the server route table, not by
   inferring a plausible path. Prefer in-process evaluation when the component is
   importable; fall back to HTTP only when it is not.
4. **Prefer in-process first, HTTP second.** A live HTTP probe failing says
   nothing about an in-process component that never needed HTTP — do not treat
   dead HTTP as a dead subsystem.
5. **Keep writes narrow.** Per-session state under the cache dir and a log line
   to the turn log. A hook that rewrites shared state is a hook you cannot
   safely enable.
6. **Test offline.** In-process path, HTTP path, and both-disabled must each
   behave distinctly. Remember module caching: a handler that mutates
   `sys.path` for imports will poison later import tests — append, don't
   prepend, and clear caches between cases.

## Verifying Before Enabling

- [ ] Confirmed via the registry which events use `emit_collect()`
- [ ] Denial uses `decision: deny` on a `command:*` event
- [ ] Every URL and method checked against the actual route table
- [ ] Tests cover in-process, HTTP, and both-unavailable
- [ ] No shared-state writes outside the session cache
- [ ] **Not registered in live config until the user has reviewed it** — shipping
      an unreviewed gate into a running agent changes behaviour immediately

## Reporting Limits Honestly

When a hook cannot do what was asked, say which half it can do. "It gates and
logs but cannot inject into the current turn, because that return is discarded"
is a usable answer; implementing the half that works and letting the user assume
the other half landed is not.
