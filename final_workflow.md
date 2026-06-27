# Core System & User Journey Architecture (FINAL_WORKFLOW)

This document maps out the system topology, multi-channel flow, and key user/agent workflows of the Universal Autonomous Business Engine (UABE).

---

## 1. System Topology

UABE operates as a centralized online backend server communicating with distributed clients (Desktop, Web, Telegram) and dynamic external services.

```mermaid
graph TB
    %% Interfaces
    OwnerDesktop[Tauri Desktop App] -->|HTTPS / WSS| APIGateway[FastAPI Gateway & Auth]
    SubOwnerWeb[React Web Portal] -->|HTTPS / WSS| APIGateway
    TelegramBot[Telegram API Webhook] -->|JSON Webhook| APIGateway

    %% API Gateway & Control
    APIGateway -->|RBAC Guard| Orchestrator[Central Executive Brain]
    Orchestrator -->|Read/Write State| DB[(PostgreSQL Cloud Instance - HNSW Indexed)]
    Orchestrator -->|Queue Jobs| RedisQueue[Redis Task Queue + Redlock]
    Orchestrator -->|Read/Write Session Context| RedisCache[(Upstash Redis Cache - Hot Layer)]

    %% Orchestrator Executions
    RedisQueue --> AgentRunner[Agent Execution Runtime]
    AgentRunner -->|Spawns| DeepResearch[Deep Research Agent]
    AgentRunner -->|Spawns| ContentCreator[Content & SEO Agent]
    AgentRunner -->|Spawns| AgencyWorker[Agency Builder & PM Agents]
    AgentRunner -->|Spawns| MeetingBot[Voice Meeting Agent - RAVA]
    AgentRunner -->|Spawns| SelfTraining[Asynchronous Self-Learning Sandbox]
    AgentRunner -->|Spawns| GuardrailDaemon[Financial Cost Guardrail Daemon]
    AgentRunner -->|Spawns| ReconciliationWorker[Stripe Cron Reconciliation Worker]

    %% External APIs
    MeetingBot -->|WebRTC + WebSockets| RetellAPI[Retell AI / Vapi API]
    RetellAPI -->|Custom LLM Hook| APIGateway
    DeepResearch -->|Scraping & Verification| WebScrapers[Firecrawl / MillionVerifier API]
    ContentCreator -->|Assets| MidjourneyAPI[Midjourney / OpenAI DALL-E]
    AgencyWorker -->|Invoicing| StripeAPI[Stripe Payments]
```

---

## 2. Core Operational Workflow (with HITL, RAVA, Domain Rotation & Idempotency)

The complete lifecycle showing the human verification, security domain rotation, RAVA context lookup, reconnection grace-periods, and billing reconciliation workflows:

```mermaid
sequenceDiagram
    autonumber
    actor Owner
    participant Brain as Central Executive Brain
    participant Agent as Agency & Research Agents
    participant Redis as Redis Cache (Hot Layer)
    participant DB as Postgres (HNSW Indexed pgvector)
    participant Meeting as Voice Meeting Agent (RAVA)
    participant Client
    participant Billing as Stripe & E-Sign

    Owner->>Brain: Initiate Campaign Objective (e.g., "Sell SEO services")
    Brain->>Agent: Run market research & lead generation
    Agent->>WebScrapers: Scrub leads via MillionVerifier API
    WebScrapers-->>Agent: Return verified, clean list (no bounce traps)
    Agent-->>Brain: Return lead list & draft email templates
    
    %% HITL Verification Gate
    Brain->>Owner: Send outreach draft to Telegram bot (Approval Gate)
    Note over Owner, Brain: Telegram Verification Bridge
    alt Approved
        Owner->>Brain: Approve campaign launch via Telegram
        Brain->>Agent: Fire outreach emails using Domain Rotation array
        Note over Agent: Rotate domains if Resend triggers block alerts
    else Rejected/Edit Needed
        Owner->>Brain: Edit pitch/request regeneration
        Brain->>Agent: Regenerate drafts & retry approval
    end
    
    Client->>Meeting: Book call & join Voice Meeting
    Note over Meeting, Redis: Session context stored in Hot Redis cache
    
    %% RAVA Voice Interaction Loop
    loop Real-Time Call Context Ingestion (Sub-600ms round-trip)
        Meeting->>Redis: Check Hot Cache for client queries & objections
        alt Cache Hit
            Redis-->>Meeting: Match immediate contextual answer (Fast Path, <10ms)
        else Cache Miss
            Meeting->>DB: Scan pgvector using HNSW index (Slow Path, <20ms)
            DB-->>Meeting: Return deep historical context
            Meeting->>Redis: Cache retrieved answer
        end
        Meeting->>Client: Speak with custom contextual intelligence
    end

    %% Voice Call State Recovery
    alt Client Drops Connection Mid-Call
        Meeting->>Brain: Catch connection drop
        Brain->>Brain: Spawn 5-minute Celery Grace Period Worker
        alt Reconnects within 5 mins
            Client->>Meeting: Re-enters WebRTC session
            Meeting->>Redis: Retrieve cached session state
            Meeting->>Client: Resume conversation seamlessly
        else Grace Period Expires
            Brain->>Brain: Mark state as INTERRUPTED
            Brain->>Agent: Send transcript summary email via Resend
        end
    end
    
    Meeting-->>Brain: Sync meeting transcript & contract terms
    Brain->>Billing: Generate contract (with stored Owner Signature) & Stripe invoice
    Billing->>Client: Send contract & payment link
    Client->>Billing: Executes payment & signs contract
    Billing-->>Brain: Trigger payment success webhook (Stripe Event ID)
    Note over Brain: Validate Event ID in Postgres (Idempotency Check)
    alt Webhook dropped due to outage
        Brain->>ReconciliationWorker: 6-hour cron polls Stripe API
        ReconciliationWorker->>Brain: Detect paid invoice missing in DB, force payment state
    end
    Brain->>Agent: Spawn Builder Agent to execute work
    Agent->>Brain: Submit deliverable to QA agent
    Brain->>Client: Deliver finalized, verified assets
```

---

## 3. Dynamic Module Extension Workflow (Self-Learning Loop & Staging Prompt Registry)

How the system dynamically adds business capabilities while safeguarding memory integrity:

1.  **Requirement Identification:** The Central Brain identifies a task that requires a tool or API it does not currently have in its `Registry`.
2.  **Research Phase:** The Brain uses the Deep Research Agent to pull down API documentation and library requirements.
3.  **Code Synthesis:** The Brain writes the target Python integration module inside a secure local sandbox environment.
4.  **Dependency Check (Two-Tier):**
    *   If the library is on the pre-approved whitelist, it is automatically `pip` installed.
    *   If not, the brain sends a Telegram request: *"Install library [x] for tool [y]? [Approve / Reject]"*.
5.  **Verification:** The system generates automated test suites to mock the API calls and tests the newly synthesized code.
6.  **Integration:** If the tests pass, the class is registered inside the PostgreSQL database's `BusinessModuleRegistry` and made available for future execution.
7.  **Memory Safeguarding (Staging Registry):**
    *   When the system updates its prompt contexts from open web research, it saves the changes as a `PENDING_PROMPT` in the `Staging Registry` table.
    *   An automated validation script executes the prompt against historical benchmark runs inside the sandbox container.
    *   If the parser throws an error or fails, the update is dropped and the system rolls back to the pinned stable prompt, firing an alert to the Owner via Telegram.
