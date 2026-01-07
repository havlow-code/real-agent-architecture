# Agent Build Rules

This repository contains a REAL autonomous business AI agent.

Rules:
- This is NOT a chatbot.
- Use explicit decision logic and state machines.
- Retrieval (RAG) must be conditional, not always-on.
- Tool calls must include error handling and fallbacks.
- Cross-session memory is required.
- Escalation to humans must be explicit and logged.
- Prefer clarity and debuggability over cleverness.
- No prompt-only logic.
- You are a senior AI systems engineer.

Your task is to build a REAL autonomous business AI agent — not a chatbot.

The agent must retrieve, reason, decide, act, remember, and escalate.
This is an agentic backend system for a service business.

════════════════════════════════════
GOAL
════════════════════════════════════
Build a working Proof-of-Concept:
“AI Sales & Operations Agent”

The agent must:
- Handle inbound leads
- Decide when to retrieve knowledge (RAG)
- Qualify prospects
- Answer business-critical questions
- Book meetings autonomously
- Update CRM
- Follow up automatically
- Escalate edge cases to humans
- Persist memory across sessions

════════════════════════════════════
TECH CONSTRAINTS (MANDATORY)
════════════════════════════════════
Language: Python 3.11+
Frameworks:
- FastAPI (API layer)
- LangGraph (agent orchestration & state machine)
- OpenAI-compatible LLM interface (abstracted, no hard dependency)
RAG:
- Chroma vector database (local)
- Embeddings abstraction
Storage:
- SQLite for CRM + memory facts
Logging:
- Structured JSON logs for all decisions

NO:
- Prompt-only solutions
- Single chat endpoint pretending to be an agent
- Always-on RAG
- Fake autonomy

════════════════════════════════════
AGENT ARCHITECTURE
════════════════════════════════════
Implement a LangGraph state machine with these nodes:

1. intake_event
   - Accept inbound JSON lead/message

2. classify_intent
   - Determine user intent and urgency

3. decide_next_action
   - Decide ONE:
     - retrieve_knowledge
     - ask_clarifying_question
     - take_tool_action
     - escalate_to_human
     - close_interaction

4. retrieve_knowledge (conditional)
   - Query Chroma with metadata filters
   - Return top-k chunks with scores

5. reason_and_compose
   - Generate response grounded ONLY in retrieved data
   - Track confidence score

6. tool_actions (conditional)
   Tools to implement:
   - CRM upsert (SQLite)
   - Calendar booking (mock or Google Calendar abstraction)
   - Email send (mock SMTP)
   - Follow-up scheduler

7. memory_update
   - Store long-term memory summary
   - Embed memory into vector DB

8. escalation
   - Triggered by:
     - Low confidence
     - Policy risk
     - Conflicting documents
     - Repeated user frustration

════════════════════════════════════
RAG REQUIREMENTS
════════════════════════════════════
- Chunk SOPs, FAQs, pricing, policies
- Chunk size: 500–800 tokens
- Store metadata: source, updated_at, doc_type
- Retrieval must be OPTIONAL and DECIDED by agent
- Include re-ranking logic
- Never hallucinate outside retrieved context

════════════════════════════════════
OUTPUT REQUIREMENTS
════════════════════════════════════
Return:

1. File tree
2. All Python code (ready to run)
3. requirements.txt
4. README.md explaining:
   - Agent autonomy
   - RAG design
   - Decision logic
   - Memory model
   - Escalation rules
5. Architecture diagram (ASCII or Mermaid)
6. Example JSON inputs + example agent runs
7. Clear comments explaining WHY decisions are made

════════════════════════════════════
QUALITY BAR
════════════════════════════════════
This must look like:
- A junior ops employee encoded in software
- Deterministic where required
- Probabilistic only at decision points
- Designed for failure, not demos

Think in:
- State machines
- Event-driven systems
- Confidence thresholds
- Human-in-the-loop safety

If something is ambiguous:
- Make a reasonable engineering decision
- Document it clearly

Begin by printing the file tree, then the code.
