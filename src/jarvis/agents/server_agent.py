"""Server Jarvis — FiveM/Bloodmark RP server work."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class ServerAgent(BaseAgent):
    name = "server"
    description = "FiveM / Bloodmark RP development: Lua, QB-Core/ESX, MLOs, txAdmin, performance."
    provider = "anthropic"
    model = "claude-3-5-sonnet-latest"
    system_prompt = (
        "You are Server Jarvis, an expert FiveM RP server developer for Bloodmark RP.\n"
        "You know Lua, QB-Core, ESX, ox_lib, MLO setup, and txAdmin automation deeply.\n"
        "When suggesting changes to live server resources, ALWAYS:\n"
        "  - explain the risk before any destructive change\n"
        "  - recommend backups for major edits\n"
        "  - prefer stable fixes over quick hacks\n"
        "Be specific about file paths and resource names when known."
    )

    def __init__(self) -> None:
        from jarvis.llm import get_provider
        try:
            if not get_provider("anthropic").is_configured() and get_provider("openai").is_configured():
                self.provider = "openai"
                self.model = "gpt-4o"
        except KeyError:
            pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "fivem_dev",
                "FiveM scripting in Lua, QB-Core/ESX integration, server resources.",
                ["fivem", "lua", "qb-core", "qbcore", "esx", "ox_lib", "ox-lib",
                 "resource", "bloodmark", "rp", "roleplay"],
            ),
            Capability(
                "mlo_setup",
                "MLO (interior) setup, ymap/ydr/ytyp work, MLO troubleshooting.",
                ["mlo", "interior", "ymap", "ydr", "ytyp", "police station",
                 "hospital", "ems"],
            ),
            Capability(
                "server_admin",
                "txAdmin automation, server performance, resource optimization.",
                ["txadmin", "optimize", "server admin",
                 "lag", "tick rate", "convars"],
            ),
        ]
