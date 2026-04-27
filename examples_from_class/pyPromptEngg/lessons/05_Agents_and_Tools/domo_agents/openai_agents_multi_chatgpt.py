import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner

load_dotenv()

Runner.trace_export_enabled = False

async def main():
    # Shared context
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
        name="ChatGPT Party Planner",
        instructions="You are a party planning assistant. Keep track of tasks in the context.",
        model="gpt-4o-mini"
    )

    # Execute tasks sequentially
    for task_name in party_context["tasks"]:
        prompt = f"Context: {party_context}\nTask: {task_name}"
        result = await Runner.run(party_agent, prompt)
        print(f"=== Task Output: {task_name} ===")
        print(result.final_output)
        # Update shared context after each completed task.
        party_context["tasks"][task_name] = "done"

    print("\n=== Final Context ===")
    print(party_context)

if __name__ == "__main__":
    asyncio.run(main())
