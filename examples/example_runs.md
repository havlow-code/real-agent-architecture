# Example Runs

## Example 1: Pricing Inquiry

### Input
```json
{
  "email": "john@acme.com",
  "name": "John Doe",
  "message": "What's your enterprise pricing?",
  "source": "website_form"
}
```

### Agent Execution Flow

**1. Intake & Load Context**
- New lead created: `john@acme.com`
- Status: `new`
- No conversation history

**2. Decision Engine**
- Query analysis: "enterprise pricing" detected
- Decision: `RETRIEVE`
- Reasoning: "Query requires factual pricing lookup"
- Confidence: 0.85
- Retrieval needed: Yes

**3. RAG Retrieval**
- Query embedding generated
- Retrieved 8 chunks from knowledge_base
- Top sources:
  - `pricing/service_pricing.md` (score: 0.92)
  - `faqs/general.md` (score: 0.78)
  - `sops/lead_qualification.md` (score: 0.65)
- Re-ranked by quality + recency
- Filtered to top 3

**4. Compose Response**
- LLM generates response grounded in sources
- Cites: "service_pricing.md"
- Includes: Enterprise plan details ($2,499+/month, custom pricing)

**5. Execute Tools**
- CRM: Lead status → `contacted`
- Email: Sends response

**6. Update Memory**
- Interaction logged to SQL
- Conversation turn added to vector store

**7. Response**
```json
{
  "response_text": "Our Enterprise plan is designed for large organizations and starts at $2,499/month with custom pricing based on your needs. It includes unlimited team members, unlimited storage, 24/7 support, a dedicated account manager, 99.99% uptime SLA, full API access, and unlimited custom integrations. We also offer white-label options and on-premise deployment. Would you like to schedule a call to discuss your specific requirements?",
  "confidence": 0.85,
  "decision_type": "retrieve",
  "sources_used": ["service_pricing.md"],
  "tools_called": ["crm_tool", "email_tool"],
  "escalated": false
}
```

---

## Example 2: Lead Qualification

### Input
```json
{
  "email": "sarah@startup.io",
  "name": "Sarah Chen",
  "message": "We're a 15-person team looking for a solution. What do you recommend?",
  "source": "email"
}
```

### Agent Execution Flow

**1. Decision Engine**
- Query analysis: Team size mentioned, needs recommendation
- Decision: `USE_TOOL` + `RETRIEVE`
- Reasoning: "Need to qualify lead and retrieve plan info"
- Confidence: 0.72
- Tools needed: ["crm"]

**2. RAG Retrieval**
- Retrieved pricing and SOP docs
- Found Professional plan details (up to 25 members)
- Found qualification criteria

**3. Compose Response**
- Recommends Professional plan
- Asks qualifying questions (BANT)

**4. Execute Tools**
- CRM: Qualify lead
  - Budget range: "estimated $500-1000/month" (based on team size)
  - Timeline: "exploring"
  - Qualification score: 60/100
  - Status: `qualified`

**5. Response**
```json
{
  "response_text": "For a 15-person team, I'd recommend our Professional plan at $799/month. It includes up to 25 team members, 500 GB storage, priority support, advanced analytics, and API access. To ensure this is the right fit, could you tell me: 1) What's your timeline for making a decision? 2) What's the main challenge you're looking to solve? 3) Do you have a budget allocated for this?",
  "confidence": 0.72,
  "decision_type": "use_tool",
  "sources_used": ["service_pricing.md", "lead_qualification.md"],
  "tools_called": ["crm_tool"],
  "escalated": false
}
```

---

## Example 3: Policy Conflict (Escalation)

### Input
```json
{
  "email": "angry@customer.com",
  "name": "Alex Johnson",
  "message": "I demand a full refund for the past 6 months. Your service has been terrible and I want compensation for damages.",
  "source": "email"
}
```

### Agent Execution Flow

**1. Decision Engine**
- Query analysis: Sensitive keywords detected ("refund", "demand", "compensation", "damages")
- Decision: `ESCALATE`
- Reasoning: "Sensitive issue requiring human attention"
- Confidence: 0.35 (below threshold)
- Escalation reason: "sensitive_topic"

**2. RAG Retrieval**
- Retrieved refund_policy.md for context
- Found 14-day guarantee, no pro-rata refunds

**3. Compose Response**
- Empathetic, non-committal response
- Escalates to human

**4. Handle Escalation**
- Escalation event created in database
- CRM status → `escalated`
- Alert sent to support team (future)

**5. Response**
```json
{
  "response_text": "I understand you're frustrated, and I want to ensure you get the best possible resolution. I'm connecting you with one of our senior team members who will review your account and follow up with you within 24 hours. They'll have the authority to discuss compensation options and find a solution that works for you.",
  "confidence": 0.35,
  "decision_type": "escalate",
  "sources_used": ["refund_policy.md"],
  "tools_called": ["crm_tool"],
  "escalated": true
}
```

---

## Example 4: Calendar Booking Failure (Error Handling)

### Input
```json
{
  "email": "prospect@bigcorp.com",
  "name": "Michael Brown",
  "message": "Can we schedule a demo for next week?",
  "source": "website_form"
}
```

### Agent Execution Flow

**1. Decision Engine**
- Query analysis: Meeting request detected
- Decision: `USE_TOOL`
- Reasoning: "Need to book calendar meeting"
- Confidence: 0.80
- Tools needed: ["calendar"]

**2. Execute Tools (Attempt 1)**
- Calendar tool: `book_meeting()`
- **Result**: FAILURE (simulated API error)
- Error: "Calendar API temporarily unavailable"
- Retry allowed: Yes

**3. Execute Tools (Retry 1)**
- Calendar tool: `book_meeting()`
- **Result**: FAILURE
- Retry count: 1/3

**4. Execute Tools (Retry 2)**
- Calendar tool: `book_meeting()`
- **Result**: SUCCESS
- Meeting scheduled: Jan 10, 2025 at 10:00 AM
- Meeting link: `https://meet.company.com/abc123`

**5. Compose Response**
- Confirms meeting booked
- Includes meeting link and details

**6. Execute Tools**
- Email: Send confirmation with calendar invite

**7. Response**
```json
{
  "response_text": "Great! I've scheduled a demo for you on January 10, 2025 at 10:00 AM. You'll receive a calendar invite shortly. Here's your meeting link: https://meet.company.com/abc123. Looking forward to showing you what we can do!",
  "confidence": 0.80,
  "decision_type": "use_tool",
  "sources_used": [],
  "tools_called": ["calendar_tool", "email_tool"],
  "escalated": false
}
```

**Logging Output** (structured JSON):
```json
{
  "trace_id": "uuid-123",
  "event": "tool_result",
  "tool_name": "calendar_tool",
  "success": false,
  "error": "Calendar API temporarily unavailable",
  "retry_count": 0
}
{
  "trace_id": "uuid-123",
  "event": "tool_result",
  "tool_name": "calendar_tool",
  "success": true,
  "retry_count": 2,
  "data": {"booking_id": "...", "meeting_link": "..."}
}
```

---

## Summary Table

| Example | Decision | Tools Used | Escalated | Key Feature Demonstrated |
|---------|----------|------------|-----------|-------------------------|
| 1. Pricing | RETRIEVE | CRM, Email | No | RAG grounding, source citation |
| 2. Qualification | USE_TOOL | CRM | No | Lead scoring, BANT qualification |
| 3. Policy Conflict | ESCALATE | CRM | Yes | Sensitive topic detection, human handoff |
| 4. Booking Failure | USE_TOOL | Calendar, Email | No | Error handling, retry logic, resilience |

## Testing These Scenarios

Run the test script:
```bash
python examples/test_scenarios.py
```

Or test individually via API:
```bash
curl -X POST http://localhost:8000/webhook/lead \
  -H "Content-Type: application/json" \
  -d '{"email": "john@acme.com", "name": "John Doe", "message": "What's your enterprise pricing?"}'
```
