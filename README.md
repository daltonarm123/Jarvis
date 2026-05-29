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
| `growth` | Trend research, monetization, niche discovery | GPT-4o-mini |
| `content` | Short-form video ideas, captions, hooks, scripts | GPT-4o-mini |
| `research` | Trend and market research for social opportunities | GPT-4o-mini |
| `social` | Multi-account social automation and posting workflows | GPT-4o-mini |
| `analytics` | Channel performance and optimization recommendations | GPT-4o-mini |
| `monetization` | Revenue strategy, affiliate funnels, ads, and product offers | GPT-4o-mini |
| `operations` | SOPs, automation systems, and scaling execution plans | GPT-4o-mini |
| `research` | Trend and market research for social opportunities | GPT-4o-mini |
| `social` | Multi-account social automation, posting, and account creation | GPT-4o-mini |

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
Jarvis> /status
Jarvis> /briefing
   → generate the daily manager summary and current plans
Jarvis> /plans
   → show current agent work plans
Jarvis> can you refactor this lua script for me
   → routed to: server
Jarvis> @social create account for tiktok as faceless1
   → register a TikTok account and get prompted for credentials
Jarvis> @social add credentials for tiktok faceless1
   access_token: sk_live_xxx
   → securely store credentials for posting
Jarvis> @social list accounts
   → show all registered accounts and credential status
Jarvis> /remember favorite_editor = neovim
```

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

### Social platform automation

- `social` manages multi-account posting and account tracking for TikTok, Instagram, Facebook, and YouTube.
- `research` finds viral trends and content opportunities before posting.
- `analytics` evaluates performance and suggests optimization.
- `monetization` recommends revenue streams and creator economy offers.
- `operations` builds repeatable SOPs and scaling systems.

`Social` supports credential-based account management: create accounts, securely store API tokens and credentials, and publish videos/posts when credentials are supplied.

#### Credential workflow

1. **Create account**: `@social create account for <platform> as <alias>`
   - Jarvis will prompt for required credentials.
2. **Add credentials**: `@social add credentials for <platform> <alias>`
   - Paste the credentials (access tokens, account IDs, etc.) in the format shown.
3. **List accounts**: `@social list accounts`
   - See all registered accounts and their credential status (✓ or ⚠).
4. **Post content**: `@social post video https://url.mp4 to <platform> caption='text' #hashtags`
   - Jarvis uses stored credentials to publish automatically.

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

Autonomous manager mode:
```bash
export JARVIS_MODE=autonomous
python -m jarvis.main
```

systemd:
```bash
sudo ./deploy.sh system
```

The provided `jarvis.service` is configured to run Jarvis in autonomous manager mode using `JARVIS_MODE=autonomous`.

For social automation, configure platform credentials in `.env`:

- `FACEBOOK_PAGE_ACCESS_TOKEN`
- `FACEBOOK_PAGE_ID`
- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- `YOUTUBE_ACCESS_TOKEN`
- `TIKTOK_ACCESS_TOKEN`

`Social` can publish to Facebook/Instagram and YouTube when tokens are available. TikTok support is scaffolded and can be extended with a supported Business API integration.

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
