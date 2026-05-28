# Jarvis

A multi-agent personal AI orchestrator for Dalton Armstrong.

You talk to **Jarvis**. Jarvis routes the task to the right **specialist** — each running on whichever LLM is best for the job — then returns the answer.

```
       You ──► Jarvis (router + memory) ──► Dev / Server / Discord / Personal
```

## Specialists

| Agent | What it does | Default model |
|---|---|---|
| `dev` | Coding, debugging, refactors, GitHub work | Claude Sonnet (falls back to GPT-4o) |
| `server` | FiveM / Bloodmark RP: Lua, QB-Core, MLOs, txAdmin | Claude Sonnet (falls back to GPT-4o) |
| `discord` | Bot dev, slash commands, moderation, Wheel Spin | GPT-4o-mini |
| `personal` | Tasks, reminders, quick research, default catch-all | GPT-4o-mini |

Adding new specialists is one file in `src/jarvis/agents/` — declare capabilities, system prompt, provider/model.

## Quickstart

```bash
git clone https://github.com/daltonarm123/Jarvis.git
cd Jarvis

cp .env.example .env
# Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY in .env

python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"

jarvis            # or: python -m jarvis.main
```

You'll get a `Jarvis>` prompt. Try:

```
Jarvis> /help
Jarvis> /agents
Jarvis> /tools
Jarvis> /status
Jarvis> can you refactor this lua script for me
   → routed to: server
Jarvis> @dev write a python script to rename files
   → forced to: dev
Jarvis> /remember favorite_editor = neovim
```

## Tools

Agents have access to a sandboxed toolset:

| Tool | What it does |
|---|---|
| `read_file` | Read a UTF-8 file from the workspace |
| `write_file` | Create/overwrite a file in the workspace |
| `list_dir` | List files (optionally recursive) |
| `shell` | Run a shell command (allowlist + timeout) |
| `http_get` | Raw HTTP GET |
| `web_fetch` | Fetch a webpage and return readable text |

File ops are scoped to `AGENT_WORKSPACE` (default `./data/agent_workspace`). Shell goes through an allowlist; `rm`, `sudo`, `dd`, etc. are hard-denied. Path traversal blocked. Test a tool directly with `/tool <name> <json-args>`.

Agents call tools by emitting fenced JSON blocks in their replies:

```
```tool
{"tool": "web_fetch", "args": {"url": "https://news.ycombinator.com"}}
```
```

Jarvis executes them in order, feeds results back, and loops until the agent produces a plain-text final answer.

## Architecture

```
src/jarvis/
├── main.py                       # Entry point (loads .env, runs core)
├── core/
│   ├── jarvis_core.py            # Orchestrator: command loop, dispatch
│   └── router.py                 # LLM classifier + keyword fallback
├── agents/
│   ├── base_agent.py             # Capability system, TaskContext
│   ├── dev_agent.py              # Dev Jarvis
│   ├── server_agent.py           # Server Jarvis (FiveM)
│   ├── discord_agent.py          # Discord Jarvis
│   ├── personal_agent.py         # Personal Jarvis
│   └── legacy/                   # Old content/marketing agents (kept for reference)
├── llm/
│   ├── base.py                   # LLMProvider interface
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   └── registry.py               # Provider registration
├── memory/
│   └── store.py                  # SQLite: conversations, facts, agent_state
└── communication/
    └── user_interface.py         # CLI front-end (Discord/voice can plug in here)
```

### How routing works

1. **LLM classifier** — a cheap model (default `gpt-4o-mini`) sees the user's task and the agent catalog, returns a JSON pick. Costs fractions of a cent per turn.
2. **Keyword fallback** — if no provider is configured or the classifier fails, each agent's `capabilities()` keywords are tallied; highest score wins. `personal` is the default if nothing matches.
3. **Forced routing** — `@dev <task>` forces a specific agent.

### Memory

SQLite at `data/jarvis.db` (path via `DATA_DIR`):

- **conversations** — every turn with which agent handled it
- **facts** — `/remember key = value` survives restarts
- **agent_state** — per-agent JSON blob for scratch state

## Adding a new specialist

1. New file `src/jarvis/agents/foo_agent.py` subclassing `BaseAgent`
2. Set `name`, `description`, `provider`, `model`, `system_prompt`
3. Implement `capabilities()` (with keywords for the fallback router)
4. Add it to `ALL_AGENTS` in `src/jarvis/agents/__init__.py`

## Tests

```bash
pip install -e ".[test]"
pytest
```

Smoke tests cover agent loading, the keyword router, and memory persistence — all without needing API keys.

## Deployment

Docker:
```bash
docker compose up -d --build
```

systemd:
```bash
sudo ./deploy.sh system
```

## Roadmap

- [ ] Tool/function-calling per agent (file ops, github CLI, web fetch)
- [ ] Discord front-end (so you can DM Jarvis)
- [ ] Voice front-end (Whisper in, ElevenLabs out)
- [ ] Vector memory for semantic recall
- [ ] Per-agent scheduled tasks (autonomous mode)
- [ ] FiveM live integration (txAdmin webhook bridge)

## Security

- `.env` is gitignored. Never commit real keys.
- Docker image does not bake secrets — they're injected at runtime via `env_file`.
- Use scoped fine-grained PATs for any GitHub automation.
