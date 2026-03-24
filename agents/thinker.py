from core.brain import ask_llm


def think(goal, memory):

    prompt = f"""
You are an autonomous AI agent.

Your goal:
{goal}

Recent memory:
{memory}

Think about what you should do next.

Write a short reasoning about your next step.
"""

    response = ask_llm(prompt)

    return response