# Decision Logic

## Overview

The decision engine is the **core autonomy feature** of this agent. Unlike rule-based systems, it uses LLM reasoning to decide what action to take based on the current state.

## Key Principle: NOT Rule-Based

**This is NOT:**
```python
if "pricing" in query:
    return "retrieve"
```

**This IS:**
```python
decision_output = llm.analyze(
    query=query,
    context=full_context,
    available_actions=ACTIONS
)
return decision_output.decision
```

The agent **reasons** about the situation, not just pattern-matching keywords.

## Decision Types

### 1. RETRIEVE
**When to use**: Query requires factual information from knowledge base.

**Examples**:
- "What's your enterprise pricing?"
- "What's your refund policy?"
- "How do I integrate with Salesforce?"

**Decision process**:
1. Identify query type: factual lookup
2. Determine relevant doc types: pricing, policies, SOPs
3. Confidence check: Is knowledge base likely to have answer?
4. Decision: RETRIEVE

**Confidence factors**:
- High if query matches known doc types
- Medium if query is tangentially related
- Low if query is too vague

### 2. REASON_ONLY
**When to use**: Can answer from existing context without retrieval.

**Examples**:
- "Thanks, that helps!"
- "Can you summarize what we discussed?"
- "Yes, let's proceed."

**Decision process**:
1. Check conversation history
2. Determine if sufficient context exists
3. Verify no new factual information needed
4. Decision: REASON_ONLY

**Confidence factors**:
- High if conversational/confirmatory
- High if recent context contains answer
- Low if answer incomplete

### 3. USE_TOOL
**When to use**: Requires executing external actions.

**Examples**:
- "Book a meeting with me."
- "Update my company name to Acme Corp."
- "Send me a follow-up email."

**Decision process**:
1. Identify action verbs (book, update, send)
2. Map to available tools
3. Check if parameters available
4. Decision: USE_TOOL
5. Specify which tools: ["calendar", "email"]

**Confidence factors**:
- High if clear action + parameters
- Medium if action clear but needs clarification
- Low if ambiguous or requires human approval

### 4. CLARIFY
**When to use**: Query is ambiguous or missing key information.

**Examples**:
- "I need help with your product."
- "How much does it cost?" (which plan?)
- "Can you integrate?" (with what?)

**Decision process**:
1. Analyze query completeness
2. Identify missing information
3. Determine if clarification would help
4. Decision: CLARIFY
5. Formulate clarifying question

**Confidence factors**:
- N/A (always low confidence when clarification needed)
- Explicit signal that agent is uncertain

### 5. ESCALATE
**When to use**: Beyond agent capability or high-risk situation.

**Examples**:
- "I want a refund for the entire year."
- "Your agent gave me wrong information and I lost money."
- "Can I get a custom contract with special terms?"

**Decision process**:
1. Detect sensitive keywords (refund, complaint, legal, custom)
2. Assess risk level
3. Check confidence score
4. Decision: ESCALATE
5. Specify reason: sensitive_topic, low_confidence, error

**Confidence factors**:
- Always <0.5 when escalating
- Automatic escalation on certain topics

## Confidence Scoring

### Calculation
Confidence is a composite score (0-1) based on multiple factors:

```python
confidence = (
    0.3 * source_quality +
    0.2 * (1 - query_complexity) +
    0.3 * context_completeness +
    0.2 * tool_success_rate
)

if conflict_detected:
    confidence *= 0.5
```

### Factor Definitions

**1. Source Quality (0-1)**
- Quality of retrieved RAG sources
- Based on relevance scores and doc type
- 1.0 = perfect match from high-authority source
- 0.5 = decent match from medium source
- 0.0 = no relevant sources

**2. Query Complexity (0-1)**
- How complex is the query?
- 0.0 = simple (e.g., "What's your pricing?")
- 0.5 = moderate (e.g., "How does your enterprise plan compare to competitors?")
- 1.0 = very complex (e.g., "Can you analyze my workflow and recommend optimization?")

**3. Context Completeness (0-1)**
- How much context do we have?
- 1.0 = full context (lead history, past interactions, clear intent)
- 0.5 = partial context
- 0.0 = no context (first interaction, vague query)

**4. Tool Success Rate (0-1)**
- Historical success rate of tool calls in this session
- 1.0 = all tools succeeded
- 0.5 = some failures
- 0.0 = all tools failed

**5. Conflict Detected (boolean)**
- Are retrieved sources contradictory?
- Halves confidence if true

### Thresholds

Confidence thresholds determine actions:

- **≥0.75**: HIGH - Proceed with answer
- **0.5-0.75**: MEDIUM - Ask clarifying question or retrieve more
- **<0.5**: LOW - Escalate to human

Example flows:

**High Confidence (0.85)**
```
Query: "What's your Starter plan pricing?"
Source Quality: 0.95 (exact match in pricing doc)
Query Complexity: 0.1 (very simple)
Context: 0.8 (have lead context)
Tool Success: 1.0 (no tools used yet)
→ Confidence: 0.85
→ Action: Proceed with answer
```

**Medium Confidence (0.65)**
```
Query: "I need a plan for my team."
Source Quality: 0.7 (found plans but unclear which one)
Query Complexity: 0.4 (needs qualification)
Context: 0.6 (first interaction, no team size known)
Tool Success: 1.0
→ Confidence: 0.65
→ Action: Ask clarifying question ("How many team members?")
```

**Low Confidence (0.35)**
```
Query: "I demand a full refund and compensation for damages."
Source Quality: 0.6 (found refund policy)
Query Complexity: 0.8 (legal/sensitive)
Context: 0.5 (unknown issue)
Tool Success: 1.0
→ Base Confidence: 0.52
→ Sensitive topic detected → Escalate
→ Final Confidence: 0.35
```

## Decision Prompt

The decision engine uses this prompt structure:

```
You are an autonomous AI agent for a service business. Analyze this situation and decide the best action.

CURRENT QUERY: [user query]
RECENT CONVERSATION: [last 5 messages]
LEAD CONTEXT: [CRM data]
PREVIOUSLY RETRIEVED SOURCES: [if any]

AVAILABLE ACTIONS:
1. RETRIEVE - Query knowledge base
2. REASON_ONLY - Answer using existing context
3. USE_TOOL - Execute tools (CRM, calendar, email)
4. CLARIFY - Ask user for more information
5. ESCALATE - Pass to human

DECISION CRITERIA: [guidance]

Respond in this format:
DECISION: [action]
CONFIDENCE: [0.0-1.0]
REASONING: [one sentence]
TOOLS_NEEDED: [list or "none"]
RETRIEVAL_NEEDED: [yes/no]
```

The LLM analyzes the full context and returns structured output.

## Escalation Logic

Escalation is triggered when:

### 1. Low Confidence (<0.5)
```python
if confidence < 0.5:
    escalate(reason="confidence_below_threshold")
```

### 2. Error Occurred
```python
if error_in_retrieval or error_in_tools:
    escalate(reason="internal_error")
```

### 3. Sensitive Topic Detected
```python
sensitive_keywords = ["refund", "legal", "complaint", "sue", "compensation"]
if any(keyword in query.lower() for keyword in sensitive_keywords):
    escalate(reason="sensitive_topic")
```

### 4. Explicit Decision
```python
if decision_engine.decide() == Decision.ESCALATE:
    escalate(reason=decision_output.escalation_reason)
```

## Conditional Retrieval

**RAG is NOT always on.** Retrieval only happens when decision engine determines it's needed.

### When retrieval is skipped:
- Simple acknowledgments ("Thanks!", "Sounds good.")
- Conversational queries answerable from context
- Tool-only actions (booking meeting, updating CRM)
- Questions about conversation history

### When retrieval is triggered:
- Factual queries about products/services
- Pricing/policy questions
- Technical how-to questions
- Any query requiring authoritative source

This saves time and API costs.

## Error Handling in Decisions

### Retrieval Errors
```python
if retrieval_failed:
    if critical_query:
        escalate("retrieval_failure")
    else:
        decision = REASON_ONLY  # Try to answer without retrieval
        confidence *= 0.7  # Reduce confidence
```

### Tool Errors
```python
if tool_failed and retry_exhausted:
    if tool_critical:
        escalate("tool_failure")
    else:
        log_error()
        proceed_without_tool()
```

### LLM Errors
```python
if llm_generation_failed:
    escalate("response_generation_error")
    fallback_response = "I'm experiencing technical difficulties. A team member will assist you."
```

## Decision Validation

After decision is made, validate:

1. **Decision is one of 5 valid types**
2. **Confidence is in range [0, 1]**
3. **If USE_TOOL, tools_to_use is non-empty**
4. **If RETRIEVE, query is not empty**
5. **If ESCALATE, reason is specified**

Invalid decisions → fallback to ESCALATE with low confidence.

## Learning and Improvement

### Current (PoC)
- Static decision logic
- Manual confidence tuning

### Future (Production)
- Track decision outcomes
- A/B test confidence thresholds
- Fine-tune decision prompt based on success rate
- Learn from escalations (what should have been escalated earlier?)
- Reinforcement learning from human feedback

## Examples

See `examples/example_runs.md` for complete walkthroughs of:
1. Pricing inquiry (RETRIEVE)
2. Lead qualification (USE_TOOL)
3. Policy conflict (ESCALATE)
4. Calendar booking failure (error handling)
