# gemini_agent_run.py
import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner

load_dotenv()

Runner.trace_export_enabled = False

async def main():
    # Create ChatGPT agent
    agent = Agent(
        name="ChatGPT Agent",
        instructions="""
        You are a helpful assistant powered by ChatGPT.
        Be concise, factual, and clear in your responses.
        """,
        model="gpt-4o-mini"
    )

    # Run the agent asynchronously
    result = await Runner.run(agent, "Explain agentic AI in simple terms.")
    print("=== ChatGPT Agent Output ===")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
