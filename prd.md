# Project Requirement Document (PRD) - Universal Autonomous Business Engine (UABE)

## 1. Executive Summary & Objective
The Universal Autonomous Business Engine (UABE) is an online-first, multi-agent AI system designed to operate, scale, and monetize diverse digital business models autonomously. Guided by a centralized "Executive Brain," the system automates Lead Generation, Client Negotiation (including voice/video agent calls with real-time vector retrieval), Contract Execution, Creative/Technical Deliverables, Online Teaching, Content Automation, and Billing. The owner maintains complete control via desktop, web, and Telegram control planes, with secure Role-Based Access Control (RBAC) for business partners (sub-owners).

---

## 2. User Personas

### 2.1 The Master Owner (The CEO)
*   **Role:** The absolute controller and cryptographic root of trust for the system.
*   **Capabilities:** Full system administration, API configuration, DB credentials, system deployment, sign-off on capital budgets, manual verification of outbound templates, dynamic dependency authorization, and provisioning sub-owner roles.
*   **Interface Access:** Tauri Desktop App (local root), Secure Web Console (remote), Telegram Master Channel.

### 2.2 The Sub-Owner (The Operator)
*   **Role:** Business partner or manager hired to oversee specific business modules (e.g., Content Creator, SEO Manager).
*   **Capabilities:** Operations-only access. Can review leads, approve content, trigger predefined automations, and view dashboards. Blocked from viewing raw API keys, billing configurations, or DB root credentials.
*   **Interface Access:** Authenticated Web Console, designated Telegram operator channels.

### 2.3 The Customer / Client
*   **Role:** External entity buying services, enrolling in courses, or negotiating contracts.
*   **Capabilities:** Books meetings, interacts with the Voice/Video Agent, receives deliverables, and signs automated contracts.
*   **Interface Access:** Customer Portal, Email, Video/Voice Meeting interface.

---

## 3. Epic Feature Requirements

### Epic 1: Central Executive Brain & State Orchestrator
*   **State Management:** Maintain complete operational state across all agents and databases in an online PostgreSQL instance.
*   **Memory Architecture (Hybrid Memory Layering):** 
    *   *Warm Layer:* Hierarchical Navigable Small World (HNSW) index on `pgvector` columns inside Supabase to compress search execution times to sub-10ms.
    *   *Hot Layer:* Temporary JSON context stored directly in Upstash Redis cache during active campaigns and live voice calls to bypass deep database retrieval for 90%+ of conversational turnarounds.
*   **Autonomous Agent Dispatcher:** A meta-orchestrator that parses user objectives, spawns domain-specific agents, and routes deliverables through a QA agent before final release.
*   **Self-Training Engine (Staging Prompt Registry):** 
    *   Asynchronously analyzes execution logs, client feedback, and operational success rates to consolidate "lessons learned."
    *   Updates are saved in a PostgreSQL `Staging Registry` as `PENDING_PROMPT` variants.
    *   A sandboxed validation script runs the new prompt against historical benchmark runs; if tests fail or raise parsing errors, the update is dropped and the system rolls back to the pinned stable prompt.

### Epic 2: Multi-Channel Control Planes & RBAC
*   **Tauri Desktop App:** A lightweight, secure desktop wrapper for Windows, macOS, and Linux that acts as the primary administration console.
*   **Secure Web Console:** Responsive, premium web panel running online, secured by JWT and MFA. Exposes UI states and dashboards to the Owner and Sub-owners based on RBAC.
*   **Telegram Command Console:** A synchronized Telegram Bot framework. 
    *   *Master channel:* For system reboot/financials.
    *   *Operator channel:* For content approval.
    *   *Outreach Verification Bridge:* Prompts the Master Owner to approve, edit, or regenerate outbound email pitches before campaigns fire.

### Epic 3: Extensible Business Module Registry & Sandboxing
*   **Dynamic Module Onboarding:** Base interface class (`BaseBusinessModule`) enabling runtime importing and registration of new modules (e.g., Stock Market Module).
*   **Two-Tier Dependency Resolver:** 
    *   *Tier 1 (Safe-Auto):* Packages on a standard pre-approved whitelist are dynamically installed via pip.
    *   *Tier 2 (Human Gate):* Obscure or new libraries trigger a Telegram authorization request before installation.
*   **Autonomous Extension:** The Executive Brain can research new APIs, generate tool scripts in a sandboxed runtime environment, run dynamic unit test scripts, register the metadata/schema, and load the class at runtime.

### Epic 4: Service Agency, Live RAVA Calls & E-Signatures
*   **Retrieval-Augmented Voice Agent (RAVA):** Integrates real-time Voice/Video AI meeting agents (via WebRTC APIs like Retell AI or Vapi) connected to a custom backend WebSocket. The agent queries the hot Redis cache (and pgvector if cache misses) to handle objections with sub-600ms latency.
*   **State Machine Re-entry (Disconnection Fault-Tolerance):** 
    *   If a client drops connection mid-call, FastAPI catches the disconnect and spawns a 5-minute grace-period worker.
    *   Reconnecting within the window resumes the call with cached session state.
    *   If the grace period expires, the call is marked `INTERRUPTED`, transcripts are summarized, and a recovery checkout email is sent.
*   **E-Sign Integration:** Automatically compile client-negotiated terms into legal contracts, embed the owner’s pre-stored signature, and generate e-signing links.

### Epic 5: The Monetization Spokes & Cold Email Hardening
*   **Multi-Domain Rotation Matrix:** PostgreSQL stores an array of warmed sending domains (e.g., changing from `.com` to `.co` or `.io`). If a domain is flagged or receives a Resend restriction webhook, the Orchestrator automatically rotates to the next active secondary domain.
*   **Pre-Flight Verification:** Outbound campaigns run lead lists through MillionVerifier/Hunter APIs to purge catch-alls and invalid mailboxes, maintaining bounces under 2%.
*   **Content & SEO Automator:** Tracks viral niches, auto-generates video/image assets, writes SEO articles, and publishes them.
*   **Online Teaching Agent:** Curates educational curricula, edits instructional materials, creates assignments, and manages a student database.
*   **Deep Research Agent:** Perplexity-style scraper and analyst capable of pulling real-time market data.

### Epic 6: Financial Guardrails & Idempotent Billing
*   **Real-time Cost Monitor:** A daemon that tracks token burn rates and API usage costs per campaign in PostgreSQL.
*   **Liquidation Protocol:** If a campaign spends 75% of its allocated budget without hitting a conversion milestone (signed contract or qualified booking), the system suspends active worker daemons, archives execution logs for reflection, and triggers a high-priority alert to the Owner via Telegram.
*   **Idempotent Billing Webhooks:** Stores Stripe Event IDs in PostgreSQL with a unique constraint to avoid double fulfillment.
*   **Reconciliation Worker:** A Celery background cron job executing every 6 hours to poll the Stripe API and verify all transactions are in sync with internal statuses, correcting dropped webhooks automatically.

---

## 4. Scope Boundaries

| In-Scope | Out-of-Scope |
| :--- | :--- |
| Online-first PostgreSQL state synchronization. | Offline-only execution without API models. |
| Automatic Cloudflare/Secure Web access provisioning. | Developing custom local LLMs (system relies on API models). |
| Real-time AI Voice negotiation via custom WebSocket. | Operating full human legal representation for contract disputes. |
| Sandboxed Python tool compilation for self-learning. | Managing hardware server procurement (infrastructure is cloud-hosted). |

---

## 5. Non-Functional Requirements (NFRs)

### 5.1 Security
*   **Data Encryption:** All API keys and credentials stored in PostgreSQL must be encrypted at rest (AES-256) using a master key held in environment variables.
*   **IAM & RBAC:** Session validation must occur at every API endpoint. Sub-owners have no read access to secret environment configurations.

### 5.2 Scalability & Concurrency
*   **Distributed Task Queues & Locking:** Backend execution must use a robust queue manager (Redis/Celery or RabbitMQ) utilizing Redis Distributed Locks (Redlock) to prevent race conditions when multiple agents query the same API key or local database files.
*   **Data Loss Prevention (DLP):** Automatic database replication and daily backups to cold storage (e.g., AWS S3).

### 5.3 Reliability & Self-Healing
*   **Agent Failure Recovery:** If a worker agent crashes or returns an invalid output, the Executive Brain must catch the exception, review the logs, rewrite the prompt or parameters, and retry up to 3 times before alerting the owner via Telegram.
