# 0001: Layered architecture with a pure domain core

- **Status:** Proposed (the owner should review and accept it)
- **Date:** 2026-11-22

## Context
cobalt mixes its rules (URL matching, action decisions) with I/O in places, which makes them harder to test in isolation.
This project is also a learning project, so it needs clear boundaries that are easy to test.

## Options considered
1. **Flat modules** like cobalt. Quick to start, but the rules get tangled with HTTP and ffmpeg code.
2. **Layered**: `api` → `services` → `domain`, with `infra` and `extractors` as adapters behind `Protocol` interfaces. It takes more files, but every rule can be tested without the network.

## Decision
Option 2. The domain (URL pipeline, action decider, models, error codes) does no I/O and imports no frameworks. Dependencies only point downward.

## Consequences
- Fast unit tests for most of the logic.
- FastAPI, Redis or ffmpeg can be swapped without touching the domain.
- There is a bit more ceremony: Protocols, plus dependency injection via FastAPI `Depends`.
