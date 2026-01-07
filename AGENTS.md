# Agent Architecture Requirements

This document defines the requirements for building autonomous agents (NOT chatbots).

## ❌ DO NOT BUILD

**Chatbot Characteristics (Avoid These):**
- Prompt-only solutions with no real logic
- Always-on RAG (retrieves on every query regardless of need)
- No explicit decision-making step
- Rule-based keyword matching instead of reasoning
- No tool error handling or fallbacks
- No confidence scoring or thresholds
- No escalation to humans
- No cross-session memory persistence
- Conversational framing without actions

**These are "polite chat APIs" - not agents.**

## ✅ MUST IMPLEMENT

### 1. Autonomous Decision-Making

**Required:**
- Explicit decision step that outputs one of:
  - `RETRIEVE` - needs factual lookup from knowledge base
  - `REASON_ONLY` - can answer from existing context
  - `USE_TOOL` - requires tool execution
  - `CLARIFY` - ask user for more information
  - `ESCALATE` - beyond agent capability
- Decision must use LLM reasoning, NOT hardcoded rules
- Decision output must be structured and logged

**Code Must Show:**
```python
# agent/decision_engine.py or equivalent
class DecisionEngine:
    def decide(self, query, context, history) -> Decision:
        # Analyze situation with LLM
        # Return explicit decision enum
        pass
```

**Verification:**
- Can you point to the exact function that makes decisions?
- Does it return a structured enum/type?
- Does it use LLM reasoning vs keyword matching?

### 2. Conditional RAG (Not Always-On)

**Required:**
- RAG retrieval is CONDITIONAL based on decision
- Simple queries skip retrieval (greetings, confirmations)
- Factual queries trigger retrieval
- Must be a conditional branch in orchestration

**Code Must Show:**
```python
# In orchestrator
if decision == Decision.RETRIEVE:
    retrieved_sources = rag_retriever.retrieve(query)
else:
    # Skip retrieval
    pass
```

**Verification:**
- Can you show the conditional check that gates RAG?
- Does agent handle queries without retrieval?
- Are there metrics for retrieval vs non-retrieval queries?

### 3. RAG Grounding

**Required:**
- Responses must cite sources when using RAG
- Empty/weak retrieval → ask clarifying question OR escalate
- Conflicting sources → degrade confidence
- Source quality scoring

**Code Must Show:**
```python
if not retrieved_sources or all(s.score < threshold):
    # Escalate or ask clarifying question
    pass

if detect_conflicts(retrieved_sources):
    confidence *= penalty
```

**Verification:**
- Are responses grounded in sources?
- What happens when retrieval returns nothing?
- How are conflicting sources handled?

### 4. Tool Usage with Error Handling

**Required:**
- Tools return structured success/failure
- Retry logic for transient errors
- Graceful degradation on permanent failures
- Escalation when critical tools fail

**Code Must Show:**
```python
@dataclass
class ToolResult:
    success: bool
    data: Optional[Dict]
    error: Optional[str]
    retry_allowed: bool

class Tool:
    def execute_with_retry(self, **kwargs) -> ToolResult:
        # Retry logic with backoff
        pass
```

**Verification:**
- Do tools return structured results?
- Is there automatic retry on failure?
- What happens when retries are exhausted?
- Are tool errors logged?

### 5. Confidence Scoring & Thresholds

**Required:**
- Calculate confidence score (0-1) for each response
- Multi-factor scoring:
  - Source quality
  - Query complexity
  - Context completeness
  - Tool success rate
  - Conflict detection
- Thresholds enforce actions:
  - ≥0.75: proceed with answer
  - 0.5-0.75: ask clarifying question
  - <0.5: escalate to human

**Code Must Show:**
```python
def calculate_confidence(
    source_quality: float,
    query_complexity: float,
    context_completeness: float,
    tool_success_rate: float,
    conflict_detected: bool
) -> float:
    # Composite scoring
    confidence = weighted_average(...)
    if conflict_detected:
        confidence *= 0.5
    return confidence

def should_escalate(confidence: float) -> bool:
    return confidence < LOW_THRESHOLD
```

**Verification:**
- Where is confidence calculated?
- What factors contribute to the score?
- Are thresholds enforced?
- Can you trace a low-confidence query → escalation?

### 6. Human Escalation

**Required:**
- Explicit escalation node/handler
- Escalation triggers:
  - Confidence below threshold
  - Sensitive topics detected
  - Tool failures
  - Conflicting information
- Escalation payload includes:
  - Reason for escalation
  - Confidence score
  - Context (query, history, errors)
  - Lead information
- Escalation events logged and tracked

**Code Must Show:**
```python
def handle_escalation(state):
    escalation_event = create_escalation(
        lead_id=state.lead_id,
        reason=state.escalation_reason,
        confidence=state.confidence,
        context={
            "query": state.query,
            "errors": state.errors,
            "sources": state.sources_used
        }
    )
    # Update CRM status to "escalated"
    # Notify human team
    # Return non-committal response to user
```

**Verification:**
- Is there an explicit escalation handler?
- What triggers escalation?
- What data is included in escalation payload?
- Are escalation events persisted?

### 7. Cross-Session Memory

**Required:**
- Factual memory (SQL):
  - Lead/contact information
  - Interaction history
  - Notes and qualification data
  - Escalation events
- Semantic memory (vector store):
  - Conversation embeddings
  - Contextual history
- Memory loaded at session start
- Memory updated after each interaction

**Code Must Show:**
```python
# Factual memory (SQL)
class FactualMemory:
    def get_lead_by_email(self, email) -> Lead: pass
    def add_interaction(self, lead_id, message, metadata): pass

# Semantic memory (vector)
class SemanticMemory:
    def add_conversation_turn(self, lead_id, role, message): pass
    def get_conversation_history(self, lead_id, n_results): pass

# Orchestration
def load_lead_context(state):
    lead = factual_memory.get_lead_by_email(state.email)
    history = factual_memory.get_lead_interactions(lead.id)
    # Populate state with context
```

**Verification:**
- Are there two memory systems (SQL + vector)?
- Is memory loaded at session start?
- Is memory updated after interactions?
- Can you trace a returning user → context loaded?

### 8. Observability

**Required:**
- Structured logging (JSON)
- Trace IDs for request correlation
- Events logged:
  - Decision made (with reasoning)
  - Retrieval performed (sources + scores)
  - Tool called (parameters + results)
  - Confidence calculated (factors + score)
  - Escalation triggered (reason + context)
  - Response composed (grounded? sources used?)
  - Errors (type + message + context)

**Code Must Show:**
```python
trace_logger.decision_made(
    decision="retrieve",
    confidence=0.85,
    reasoning="Query requires pricing lookup"
)

trace_logger.escalation_triggered(
    reason="confidence_below_threshold",
    confidence=0.35,
    context={...}
)
```

**Verification:**
- Are all key events logged?
- Is there a trace ID per request?
- Are logs structured (JSON)?
- Can you reconstruct agent flow from logs?

## 🧪 Proof Requirements

**You must be able to demonstrate:**

1. **Point to the decision function** that returns explicit enum
2. **Show the conditional** that gates RAG retrieval
3. **Trace a low-confidence query** → escalation with payload
4. **Show tool error** → retry → escalate if critical
5. **Load a returning user** → context from memory systems
6. **Walk through logs** for a single request showing all decisions

## 🚫 Anti-Patterns to Avoid

1. **Always-on RAG**: Don't retrieve on every query
2. **Keyword rules**: Don't use `if "pricing" in query: retrieve()`
3. **Silent failures**: Don't ignore tool errors
4. **No confidence**: Don't respond without scoring
5. **No escalation**: Don't try to handle everything
6. **Stateless**: Don't forget conversation history
7. **Chatty logs**: Don't use print(), use structured logging

## ✅ Success Criteria

An autonomous agent:
- **Decides** what to do (explicit step)
- **Retrieves** conditionally (not always)
- **Acts** with tools (with error handling)
- **Remembers** across sessions (SQL + vector)
- **Escalates** when uncertain (with context)
- **Observes** all actions (structured logs)
- **Proves** autonomy (not rule-based)

If you can't point to where these happen in code, it's not an agent.
