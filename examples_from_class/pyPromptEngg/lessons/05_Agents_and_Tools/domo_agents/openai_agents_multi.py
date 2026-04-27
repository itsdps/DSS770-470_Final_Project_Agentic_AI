import asyncio
from agents import Agent, Runner

Runner.trace_export_enabled = False

async def main():
    # Shared MCP
    party_context = {
        "user_goal": "plan birthday party for 20 people",
        "tasks": {
            "book_venue": "pending",
            "invite_friends": "pending",
            "order_catering": "pending"
        },
        "tools_available": ["BookingAPI", "EmailAPI", "CateringAPI"]
    }

    # Create an agent
    party_agent = Agent(
        name="Party Planner",
        instructions="You are a party planning assistant. Keep track of tasks in the context.",
        model="litellm/gemini/gemini-2.5-flash"
    )

    # Execute tasks sequentially
    for task_name in party_context["tasks"]:
        prompt = f"Context: {party_context}\nTask: {task_name}"
        result = await Runner.run(party_agent, prompt)
        print(f"=== Task Output: {task_name} ===")
        print(result.final_output)
        # Update MCP
        party_context["tasks"][task_name] = "done"

    print("\n=== Final Context ===")
    print(party_context)

asyncio.run(main())
