# Cost & Budget Management (COST_BUDGET_MANAGEMENT)

This document provides granular financial models for the deployment, operational API usage, and structural hosting optimization strategies of UABE.

---

## 1. Hosting & Database Infrastructure Cost Estimates (Monthly)

| Service | Tier | Description | Est. Cost / Mo |
| :--- | :--- | :--- | :--- |
| **AWS ECS Fargate** | 1 vCPU / 2GB RAM | FastAPI Daemon Container execution | $15.00 |
| **Supabase DB** | Pro Tier | Managed PostgreSQL + `pgvector` + HNSW index | $25.00 |
| **Upstash Redis** | Pay-as-you-go | Queue broker & hot session cache layer | $8.00 |
| **Cloudflare Tunnel** | Free Tier | Secure ingress web panel hosting proxy | $0.00 |
| **Total Base Infrastructure** | | | **$48.00 / Mo** |

---

## 2. API Token & Execution Cost Model (Per-Campaign Unit Cost)

Assumptions: One Campaign runs for 30 days, generates 500 leads, conducts 100 outbound emails, books 5 video meetings (15 minutes each), and auto-generates 20 content packs.

### A. LLM Reasoning Costs
*   **Claude 3.5 Sonnet (Executive Brain):**
    *   *Input:* $3.00 per Million tokens. *Output:* $15.00 per Million tokens.
    *   *Estimated volume:* 5M input tokens, 1.5M output tokens.
    *   *Cost:* $15.00 (Input) + $22.50 (Output) = **$37.50**
*   **GPT-4o-mini (Worker Spokes):**
    *   *Input:* $0.150 per Million tokens. *Output:* $0.600 per Million tokens.
    *   *Estimated volume:* 20M input tokens, 5M output tokens.
    *   *Cost:* $3.00 (Input) + $3.00 (Output) = **$6.00**

### B. Business Operations APIs
*   **Perplexity API (sonar-pro research):**
    *   $5.00 per 1000 searches. Estimated usage: 200 searches = **$1.00**
*   **Retell AI / Vapi (Voice Meetings):**
    *   $0.15 per active call minute. Estimated usage: 5 meetings * 15 mins = 75 minutes = **$11.25**
*   **MillionVerifier API (Email Scrubbing):**
    *   $0.0029 per email checked. Estimated usage: 500 leads verification = **$1.45**
*   **DALL-E 3 / Midjourney (Creative Asset Generation):**
    *   $0.04 per HD image. Estimated usage: 60 images = **$2.40**

### C. Campaign Cost Summary
*   **Base Token Cost per campaign:** **$59.60**

---

## 3. Financial Margin Optimization & Guardrail Strategies

To protect the Owner's financial margin, the Central Brain dynamically applies four core optimization and safety policies:

### Policy A: Dynamic 75% Budget Kill-Switch
*   Every campaign is initialized with a specific budget (e.g., $100.00) in PostgreSQL.
*   The **Cost Guardrail Daemon** tracks the sum of all model/API charges associated with the campaign ID.
*   If the cost exceeds **75% ($75.00)** and the campaign has not recorded a positive conversion milestone (such as a signed client contract or a confirmed booked meeting), the Kill-Switch is triggered:
    *   Active outreach threads are paused.
    *   Continuous agent loops are spun down.
    *   Logs are archived for the nightly self-reflection analysis.
    *   A high-priority alert is sent via Telegram: *"🚨 CRITICAL: Campaign [X] has reached 75% budget ($75.00) with 0 conversions. Execution paused to prevent overrun."*

### Policy B: Semantic Caching & Hybrid Memory Layering
*   By placing active call sessions and campaign rules in the **Hot Redis Cache Layer**, database read execution time is compressed, preventing token overhead.
*   Before hitting the Claude API for complex actions (e.g., qualifying a lead or analyzing an SEO keyword), the Orchestrator runs a pgvector semantic search (`threshold > 0.95`) against past queries in the DB.
*   If a near-identical query exists, the system reuses the cached response.
*   **Estimated Cost Reduction:** **20% - 30%** on repeating LLM inputs.

### Policy C: Multi-Model Orchestration Tiering
*   **Rule:** Never send formatting, translation, JSON parsing, or classification tasks to Claude 3.5 Sonnet.
*   The Orchestrator routes structured formatting and outbound template variations strictly to `gpt-4o-mini`, reserving `claude-3-5-sonnet` only for executive decision-making and code generation inside the sandbox.
*   **Estimated Cost Reduction:** **40%** overall token spend.

### Policy D: Voice Meeting Pre-Qualification Guardrails
*   **Pre-qualification:** To prevent paying Retell AI call fees for spam or low-value leads, the system forces clients to pass a text-based qualification questionnaire via email or Telegram *before* generating the booking link.
*   **Timeout Policy:** AI meetings are automatically capped at a maximum of 20 minutes. The agent will politely wrap up and schedule next steps, preventing runaway loop call costs.
