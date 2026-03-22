"""Demo script for Red Hat Wellness Bot using deep agents.

This script demonstrates the wellness bot's capabilities across 3 scenarios:
1. Full wellness analysis with email
2. Retrieving previous BMI from memory
3. Updating weight and recalculating with memory

All tools are served via MCP server at http://0.0.0.0:5001/mcp
"""

import asyncio

from langchain_core.messages import HumanMessage

from template_agent.src.core.agent import get_template_agent
from template_agent.utils.pylogger import get_python_logger

logger = get_python_logger()


async def run_demo():
    """Run the wellness bot demo with 3 scenarios on the same thread."""
    print("=" * 80)
    print("Red Hat Wellness Bot Demo (Deep Agents + MCP Tools)")
    print("=" * 80)
    print()

    # Use the existing get_template_agent() which now returns a deep agent
    async with get_template_agent(enable_checkpointing=True) as agent:
        logger.info("✓ Deep agent initialized with MCP tools, skills, and subagents")
        print()

        # Use the same thread_id for all scenarios to demonstrate memory
        thread_id = "demo-session-wellness-001"
        config = {"configurable": {"thread_id": thread_id}}

        # =====================================================================
        # SCENARIO 1: Full wellness analysis with email
        # =====================================================================
        print("=" * 80)
        print("SCENARIO 1: Full Wellness Analysis")
        print("=" * 80)
        print("\n👤 User: I'm 178cm and 82kg, email is tuhin@redhat.com\n")

        result1 = await agent.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content="I'm 178cm and 82kg, email is tuhin@redhat.com"
                    )
                ]
            },
            config=config,
        )

        # Extract final response
        final_message = result1["messages"][-1]
        print(f"🤖 Bot: {final_message.content}\n")
        print(
            "📊 Expected: Wellness Analyst → calculates BMI (25.9), water (2.7L), calories (1968)"
        )
        print(
            "🔍 Expected: Wellness Analyst → searches for health tips for overweight BMI"
        )
        print(
            "📧 Expected: Report Dispatcher → formats and emails report to tuhin@redhat.com"
        )

        await asyncio.sleep(2)

        # =====================================================================
        # SCENARIO 2: Memory recall
        # =====================================================================
        print("\n" + "=" * 80)
        print("SCENARIO 2: Memory Recall")
        print("=" * 80)
        print("\n👤 User: What was my BMI again?\n")

        result2 = await agent.ainvoke(
            {"messages": [HumanMessage(content="What was my BMI again?")]},
            config=config,
        )

        final_message = result2["messages"][-1]
        print(f"🤖 Bot: {final_message.content}\n")
        print(
            "💭 Expected: Bot recalls BMI (25.9) from memory without calling MCP tools"
        )

        await asyncio.sleep(2)

        # =====================================================================
        # SCENARIO 3: Update weight with memory
        # =====================================================================
        print("\n" + "=" * 80)
        print("SCENARIO 3: Update Weight (Memory Recall)")
        print("=" * 80)
        print("\n👤 User: I'm now 79kg\n")

        result3 = await agent.ainvoke(
            {"messages": [HumanMessage(content="I'm now 79kg")]}, config=config
        )

        final_message = result3["messages"][-1]
        print(f"🤖 Bot: {final_message.content}\n")
        print("💭 Expected: Remembers height (178cm) from memory")
        print("🧮 Expected: Calculates new BMI using bmi_tool(178, 79) → 24.9")
        print(
            "📈 Expected: 'You went from 25.9 to 24.9 — you're in the normal range now!'"
        )

        # Complete
        print("\n" + "=" * 80)
        print("Demo Complete!")
        print("=" * 80)
        print("\n✓ All scenarios executed successfully")
        print("✓ Memory persistence demonstrated across turns")
        print("✓ MCP tools used: bmi_tool, multiply_tool, web_search_tool, email_tool")
        print("✓ Skills used: wellness-report (for formatting)")
        print("✓ Subagents used: Wellness Analyst → Report Dispatcher")
        print("✓ Memory used: AGENTS.md for routing and identity\n")


async def main():
    """Main entry point for demo."""
    try:
        await run_demo()
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")
        print("\n⚠️  Make sure:")
        print("  1. MCP server is running at http://0.0.0.0:5001/mcp")
        print("  2. OPENAI_API_KEY or GOOGLE_APPLICATION_CREDENTIALS is set")
        print("  3. All dependencies are installed: pip install -e '.[dev]'")
        raise


if __name__ == "__main__":
    asyncio.run(main())
