# Jarvis

Multi-agent AI system for content creation, marketing, and automation.

> ⚠️ Early-stage scaffold. Most agents currently return stub responses; the AI-backed methods (`call_ai`) work once `OPENAI_API_KEY` is set.

## Features

- Pluggable agent architecture (`BaseAgent` → specialized agents)
- Async command dispatch loop
- Daily reporting + finance tracking utilities
- Docker / systemd deployment paths

## Quickstart

```bash
# 1. Clone
git clone https://github.com/daltonarm123/Jarvis.git
cd Jarvis

# 2. Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (minimum)

# 3. Install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 4. Run
jarvis
# or: python -m jarvis.main
```

You should see a `Jarvis>` prompt. Try `help`, `status`, or `agent "Content Creator 1" generate idea`.

## Project Layout

```
src/jarvis/
├── main.py                   # Entry point (loads .env, starts the core)
├── config.py                 # Static agent → model mapping
├── core/jarvis_core.py       # Central controller + command loop
├── agents/
│   ├── base_agent.py         # Abstract base (lazy OpenAI client)
│   ├── content_creator.py
│   ├── video_editor.py
│   ├── stream_clipper.py
│   ├── social_poster.py
│   ├── ecommerce_agent.py
│   └── marketing_agent.py
├── communication/user_interface.py
└── utils/
    ├── daily_reporter.py
    └── finance_tracker.py
```

## Agents

| Agent | Purpose | Default model |
| --- | --- | --- |
| Content Creator | Ideas, scripts | gpt-4 |
| Video Editor | Editing, rendering (stub) | gpt-3.5-turbo |
| Stream Clipper | Clipping streams (stub) | gpt-3.5-turbo |
| Social Poster | Cross-platform posting (stub) | gpt-4 |
| E-commerce Agent | Business ideas, market analysis | gpt-4 |
| Marketing Agent | Campaigns, audience analysis | gpt-4 |

## Deployment

### Docker

```bash
docker compose up -d --build
```

`docker-compose.yml` reads `.env` for secrets and mounts `./data` and `./logs`.

### systemd

```bash
sudo ./deploy.sh system
```

Installs to `/opt/jarvis`, runs as the `jarvis` user, managed via `systemctl`.

## Roadmap

- Replace stub agent commands with real integrations
- Add scheduler for autonomous mode
- Discord/voice front-ends
- Persistent agent memory

## Security

- `.env` is **gitignored** — never commit real keys.
- The Docker image does not bake secrets in; they're passed at runtime via `env_file`.
- Use scoped tokens where possible.
