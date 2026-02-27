# Senior Developer Guide

This guide focuses on architecture, boundaries, reliability, and extension points.

## System Topology

```mermaid
flowchart LR
    subgraph Runtime
        ORCH[telegram_orchestrator.py]
        HS[webhook_server.py]
        HND[handlers/*]
        CORE[domain services]
        DB[(SQLite)]
    end

    TG[Telegram API] --> HS
    HS --> ORCH
    ORCH --> HND
    HND --> CORE
    CORE --> JOP[Joplin API]
    CORE --> GT[Google Tasks API]
    CORE --> LLM[LLM Provider]
    CORE --> DB
```

## Webhook Request Path

```mermaid
sequenceDiagram
    participant User
    participant Telegram
    participant WebhookServer
    participant PTB as PTB Application
    participant Handler
    participant Services

    User->>Telegram: Send /status or message
    Telegram->>WebhookServer: POST /webhook
    WebhookServer->>PTB: process_update(update)
    PTB->>Handler: Route command/message
    Handler->>Services: Domain operations
    Services-->>Handler: Result
    Handler-->>Telegram: sendMessage(...)
    Telegram-->>User: Response
```

## Design Notes

- Orchestrator remains thin; command logic belongs to `src/handlers/`.
- Runtime mode is environment-driven: webhook in Fly.io, polling locally.
- Durable state and audit logs are SQLite-backed.
- Joplin and bot are co-located in one container to simplify networking.

## Suggested Next Refactors

- Introduce repository interfaces for SQLite access.
- Add command-level integration tests for all handlers.
- Add explicit health/readiness split (`/health` vs `/ready`).
