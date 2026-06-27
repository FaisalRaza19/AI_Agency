# Technical Stack Matrix (TECH_STACK_MATRIX)

This matrix outlines the specific components, libraries, APIs, and tools selected to build the UABE system architecture.

---

## 1. Application Architecture Layers

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Desktop Wrapper** | [Tauri](https://tauri.app/) (Rust) | Sub-6MB binaries, minimal RAM footprint, highly secure system-level hooks compared to resource-heavy Electron. |
| **Web UI Frontend** | React + TypeScript + Vite | Industry standard, fast builds, responsive rendering, easily embeds into Tauri's WebView. |
| **Backend Daemon** | Python + FastAPI | Native compatibility with AI/LLM toolsets, highly performant async runtime, automatic OpenAPI documentation. |
| **Database** | PostgreSQL | Relational integrity for complex campaign, user, and financial states. |
| **Vector Engine & Index** | pgvector + HNSW index | Compresses semantic search execution times to sub-10ms inside Supabase/PostgreSQL. |
| **Hot Cache Layer** | Upstash Redis | Stores active meeting session contexts, API credentials, and rate limits to guarantee sub-600ms RAVA round-trips. |
| **Task Queue** | Redis + Celery / Arq | Reliable async task distribution, webhook queue handling, and agent process execution management. |
| **Distributed Locking** | Redlock (via `pottery` or `redis-py`) | Prevents race conditions and API key over-utilization when multiple agents run concurrently. |
| **Dynamic Sandbox** | Docker + Docker SDK for Python | Runs dynamically generated Python tools in isolated containers to protect host hardware from execution errors. |

---

## 2. Artificial Intelligence Models & Core APIs

| Function | Provider / API | Model / Service | Purpose |
| :--- | :--- | :--- | :--- |
| **Executive Orchestration** | Anthropic Claude API | `claude-3-5-sonnet` | Complex logic parsing, system state routing, dynamic tool generation, and staging QA checks. |
| **Worker Executions** | OpenAI API | `gpt-4o-mini` | Low-latency, cost-effective processing for outbound drafts, content editing, and classification. |
| **Real-time Scraped Research** | Perplexity API | `sonar-pro` | Real-time web-enabled search, market validations, and citation gathering. |
| **Live RAVA Meetings** | Retell AI or Vapi (via WebSockets) | Custom LLM integration | Connects WebRTC voice bot to FastAPI WebSockets. Allows pgvector RAG querying mid-call to handle live objections. |
| **Asset Generation** | Midjourney / DALL-E 3 | Text-to-Image API | Autonomously designs thumbnails, banner graphics, and social media imagery. |

---

## 3. Deployment, Security & Infrastructure

| Function | Service | Configuration Details |
| :--- | :--- | :--- |
| **Cloud Hosting** | AWS ECS / Supabase | Containerized backend runtime scaled dynamically; managed PostgreSQL instance. |
| **Remote Access Tunnel** | Cloudflare Tunnels | Exposes FastAPI backend endpoints to web portals securely without opening firewall ports. |
| **Email Services & Verify** | Resend API + MillionVerifier | Outbound automated email newsletters and pitches; pre-flight email validity validation scrubbing. |
| **Auth Protocol** | PyJWT / bcrypt | Strict token-based authentication with role validation at the REST level. |
| **Database DLP** | AWS S3 Backups | Scheduled cron scripts backing up PostgreSQL databases nightly. |
| **Error Tracking** | Sentry | Centralized monitoring of agent execution exceptions, model timeouts, and backend failures. |
