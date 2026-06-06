# Jarvis Architecture Overview

## Purpose
Jarvis is a multi-agent AI orchestrator that routes user requests to specialist agents, stores conversation state, and supports both interactive CLI and autonomous workflows.

## Key components

### 1. Entry point
- `src/jarvis/main.py`
  - Loads `.env` environment variables.
  - Parses CLI arguments.
  - Instantiates `JarvisCore`.
  - Runs interactive mode (`jarvis.run(ui)`) or one-shot pipeline mode (`jarvis.run_pipeline(...)`).

### 2. Core orchestrator
- `src/jarvis/core/jarvis_core.py`
  - Owns the agent registry, router, memory store, health monitor, and automation helpers.
  - `handle(user_input)` is the main public integration point.
  - Handles:
    - slash commands starting with `/`
    - forced routing via `@agent`
    - automatic routing via the router
  - Dispatches tasks to agents and logs every turn in memory.

### 3. Routing
- `src/jarvis/core/router.py`
  - Decides which specialist should handle each request.
  - Primary router strategy:
    1. LLM classifier using a lightweight model (default: `gpt-4o-mini`).
    2. Keyword fallback using each agent's declared capability keywords.
  - If the classifier is unavailable, keyword routing still works.
  - Agent names are resolved from router output and matched against loaded agents.

### 4. Agent abstraction
- `src/jarvis/agents/base_agent.py`
  - Defines `BaseAgent`, `Capability`, and `TaskContext`.
  - Each specialist agent inherits `BaseAgent` and implements:
    - `name`
    - `description`
    - `provider`
    - `model`
    - `system_prompt`
    - `capabilities()`
  - Default `handle()` behavior:
    - builds a message list from recent history
    - appends the current user input
    - sends the prompt to the selected LLM provider
    - returns the model response

### 5. Provider layer
- `src/jarvis/llm/registry.py`
  - Registers LLM providers by short name.
  - Exposes `get_provider(name)` and `available_providers()`.
- Built-in providers:
  - `src/jarvis/llm/openai_provider.py`
  - `src/jarvis/llm/anthropic_provider.py`
- Providers are configured through `.env` keys like `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.

### 6. Memory and state
- `src/jarvis/memory/store.py`
  - Stores conversation history, facts, and per-agent state in SQLite.
  - Supports:
    - message logging
    - `/remember key = value`
    - per-agent JSON state such as social account and credential records

### 7. User interfaces
- `src/jarvis/communication/user_interface.py`
  - CLI front-end that prompts `Jarvis> ` and prints output.
- `src/jarvis/communication/voice_interface.py`
  - Voice-enabled interface option.

### 8. Command handling
- Commands in `JarvisCore._handle_command(...)` include:
  - `/help`, `/agents`, `/status`
  - `/briefing`, `/plans`, `/tasks`
  - `/accounts`, `/account`, `/schedule`, `/publish`
  - `/health`, `/escalate`
  - `/remember`, `/facts`, `/session`
- These are processed internally without agent routing.

### 9. Social automation and credentials
- `src/jarvis/agents/social_agent.py`
  - Manages social platform accounts, posting workflows, and credentials.
- `src/jarvis/agents/email_agent.py`
  - Manages tracked signup email addresses and inbox monitoring.
- `JarvisCore._import_tokens(...)`
  - Imports social credentials from a local JSON file into the social agent state.

### 10. Additional services
- `src/jarvis/core/health.py`
  - Tracks agent success/failure counts.
- `src/jarvis/core/automation.py`
  - Manages scheduling and task monitoring.
- `src/jarvis/platforms/`
  - Contains connectors for TikTok, YouTube, and other platforms.
- `src/jarvis/automation/signup_automation.py`
  - Provides a browser automation scaffold for signup flows.

## Agent registry
- `src/jarvis/agents/__init__.py`
  - Imports all specialist agents.
  - Exposes `ALL_AGENTS`.
- Current specialists:
  - `DevAgent`
  - `PromptAgent`
  - `PersonalAgent`
  - `GrowthAgent`
  - `ContentAgent`
  - `ResearchAgent`
  - `SocialAgent`
  - `AnalyticsAgent`
  - `MonetizationAgent`
  - `OperationsAgent`
  - `VideoEditorAgent`
  - `EmailAgent`

## Workflow summary
1. CLI receives user text.
2. `JarvisCore.handle()` decides if it is a command, forced route, or auto-route.
3. Router chooses the agent.
4. `TaskContext` is built from session history and memory.
5. The selected agent sends the request to its configured LLM provider.
6. Response is saved to memory and returned to the user.

## Deployment notes
- Use `.env` to configure API keys and environment variables.
- Interactive mode: `python -m jarvis.main`
- Autonomous mode: `python -m jarvis.main --autonomous` or `JARVIS_MODE=autonomous`
- One-shot pipeline mode: `python -m jarvis.main --pipeline --platform=tiktok --topic="..." --simulate`

## Why this architecture works
- Separation of concerns:
  - core orchestration and routing are decoupled from agent behavior
  - providers are abstracted behind a registry
  - memory is centralized and reusable across agents
- Flexible routing:
  - forced agent selection, LLM classification, and keyword fallback
- Easily extensible:
  - add new specialist agents by subclassing `BaseAgent`
  - register them in `src/jarvis/agents/__init__.py`
