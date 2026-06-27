# Project Execution Roadmap (EXECUTION_ROADMAP)

This execution roadmap breaks down the UABE project timeline into five distinct phases, focusing on delivering stable, testable core functionality before integrating complex multi-agent features.

---

## Roadmap Timeline Overview

```
Weeks  0   1   2   3   4   5   6   7   8   9  10
       |---|---|---|---|---|---|---|---|---|---|
Phase 1: [Core Engine & DB] ========>
Phase 2: [Control Planes, RBAC & HITL] ======>
Phase 3: [Default Spokes & Concurrency] ====>
Phase 4: [Agency, Live RAVA & Billing] ========>
Phase 5: [Code Sandbox & Cost Guardrails] ======>
```

---

## Detailed Phase Breakdown

### Phase 1: Core Engine & DB Infrastructure (Weeks 1 - 2)
*   **Deliverables:**
    *   Initialize online PostgreSQL database schema including tables for `users`, `rbac_permissions`, `campaigns`, `leads`, `agent_logs`, `module_registry`, `campaign_wallets`, `stripe_processed_events`, and `staging_prompt_registry`.
    *   Configure HNSW index on the `pgvector` columns inside PostgreSQL to optimize semantic search lookups to sub-10ms.
    *   Build the FastAPI core daemon service with WebSockets support for real-time streaming notifications.
    *   Establish central state managers and base orchestrator classes using LangGraph.
*   **Milestones:**
    *   Database connection pools, migrations, HNSW index configurations, and schema validation successfully passing.
    *   FastAPI backend up and running on a staging VPS.

### Phase 2: Control Planes, RBAC & HITL Gates (Weeks 3 - 4)
*   **Deliverables:**
    *   Develop the unified responsive frontend using Vite + React.
    *   Configure Tauri desktop wrapper for cross-platform compiles (`.exe`, `.app`, `.deb`).
    *   Implement JWT-based authentication with strict RBAC endpoints.
    *   Launch the Telegram Bot framework with dynamic webhook validation for owner/sub-owner command separation.
    *   Integrate the **Telegram Verification Bridge** for manual approval of generated outreach drafts.
*   **Milestones:**
    *   Login to Tauri App and see real-time log feeds from the database.
    *   Authenticate via Telegram bot, pull database telemetry statistics, and approve a sample outreach run.

### Phase 3: Default Business Spokes & Concurrency (Weeks 5 - 6)
*   **Deliverables:**
    *   **Deep Research Spoke:** Scraping engines integrated with Firecrawl & Tavily.
    *   **Pre-Flight Verification:** Connect MillionVerifier/Hunter API to scrub lead email lists before launching outreach campaigns.
    *   **Multi-Domain Rotation Matrix:** Implement PostgreSQL database tracking for secondary sending domains and automatic switchover logic on domain block alerts.
    *   **Task Queue & Locks:** Set up Redis and Celery/Arq task queues, implementing **Redis Distributed Locks (Redlock)** to prevent database/API write conflicts between concurrently running agents.
*   **Milestones:**
    *   Deep research report successfully generated and stored in Postgres.
    *   Outbound email task queues running pre-flight verification and sending via rotating domains safely.

### Phase 4: Service Agency, Live RAVA Calls & Billing (Weeks 7 - 8)
*   **Deliverables:**
    *   **Live RAVA Spoke:** Integrate Retell AI/Vapi Custom LLM WebSockets to support real-time voice calls. Implement hybrid context lookups (checking hot Upstash Redis cache first for <10ms response, failing back to pgvector HNSW database query for <20ms).
    *   **Voice Call State Recovery:** Configure FastAPI disconnect hooks and a 5-minute Celery grace-period recovery worker to handle WebRTC dropouts.
    *   **Idempotent Billing & E-Signature:** Implement Stripe Event ID database constraints to prevent duplicate deliveries. Create the background Stripe cron reconciliation worker running every 6 hours. Template generation engine that reads signature data and embeds it into legally binding PDFs.
*   **Milestones:**
    *   Simulated meeting successfully qualifications lead using live pgvector RAVA lookup, recovers from a temporary websocket drop, signs client contract, and triggers Stripe checkout invoice.
    *   Stripe payment webhook succeeds, logs event, and launches workers without double-triggering.

### Phase 5: Sandboxed Code compilation & Cost Guardrails (Weeks 9 - 10)
*   **Deliverables:**
    *   Configure secure Dockerized/Sandboxed python runner for executing generated code.
    *   Implement the **Two-Tier Dependency Resolver** (pre-approved whitelist check vs. Telegram approval request).
    *   Implement **Anisotropic Filtering & Prompt Pinning** (validating `PENDING_PROMPT` changes against a benchmark suite inside the sandbox before registering).
    *   Develop the **Cost Guardrail Daemon** that monitors campaign budget token usage and executes the **75% budget Kill-Switch** protocol (pausing daemons, logging errors, archiving memory, and alerting owner).
*   **Milestones:**
    *   Orchestrator autonomously writes a new helper script, prompts Telegram to install a non-whitelist package, runs tests in the sandbox, registers it, and executes it.
    *   Prompt learning loop tests a broken prompt string, correctly fails validation checks in the sandbox, rolls back to the pinned version, and sends a warning to Telegram.
    *   Triggering budget threshold (75%) successfully executes the automated safety shutdown and alerts the owner.
