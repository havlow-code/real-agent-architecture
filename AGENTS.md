# Agent Build Rules

This repository contains a REAL autonomous business AI agent.
It is NOT a chatbot.

## Core Principles
- The system must retrieve, reason, decide, act, remember, and escalate.
- The agent represents a real business function (sales / operations), not a conversational toy.
- Autonomy must be explicit, inspectable, and debuggable.

## Architecture Rules
- Use an explicit state machine (LangGraph or equivalent) with persisted state.
- The agent must have a dedicated decision step that chooses the next action.
- Deterministic logic is preferred for safety; probabilistic logic is allowed only at decision points.

## RAG Rules
- Retrieval (RAG) must be conditional and decided by the agent.
- RAG must never be always-on.
- Retrieved documents must be chunked with metadata (source, doc_type, updated_at).
- Responses must be grounded in retrieved evidence.
- If retrieval is weak, conflicting, or empty, the agent must ask clarifying questions or escalate.

## Tooling Rules
- Tool calls must be real or cleanly mocked behind interfaces.
- Every tool must return structured success/failure responses.
- Tool failures must be handled with retries, fallbacks, or escalation.
- The agent must decide WHEN to use tools — tools must not be auto-triggered.

## Memory Rules
- Cross-session memory is mandatory.
- Store factual memory in SQL (e.g., lead status, preferences).
- Store semantic memory in a vector database.
- Memory updates must occur after meaningful interactions.

## Confidence & Safety
- Confidence scoring is required for responses.
- Low-confidence situations must trigger clarification or escalation.
- Human escalation must be explicit, logged, and produce a handoff payload.
- Policy, pricing, or legal ambiguity must always escalate.

## Engineering Standards
- Prefer clarity, correctness, and debuggability over cleverness.
- No prompt-only logic.
- No fake autonomy.
- No hard-coded secrets — use environment variables and .env.example.
- All decisions, retrievals, tool calls, and escalations must be logged.

## Output Expectations
- This repository should read like production engineering work.
- Anyone reviewing the code should be able to trace:
  decision → retrieval → action → memory → outcome.
