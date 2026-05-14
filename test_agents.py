#!/usr/bin/env python3
"""Test script for Jarvis agents."""

import asyncio
from jarvis.core.jarvis_core import JarvisCore


async def test_agents():
    """Test the agents by sending commands."""
    jarvis = JarvisCore()

    print("Testing Jarvis Agents...\n")

    # Test each agent
    for agent in jarvis.agents:
        print(f"Testing {agent.name}:")
        if "Content" in agent.name:
            result = await agent.execute_command("generate idea")
            print(f"  {result}")
        elif "E-commerce" in agent.name:
            result = await agent.execute_command("generate business idea")
            print(f"  {result}")
            result = await agent.execute_command("report issue")
            print(f"  {result}")
        elif "Marketing" in agent.name:
            result = await agent.execute_command("create campaign")
            print(f"  {result}")
            result = await agent.execute_command("report issue")
            print(f"  {result}")
        else:
            result = await agent.execute_command("status")
            print(f"  {result}")
        print()

    print("Test completed.")


if __name__ == "__main__":
    asyncio.run(test_agents())