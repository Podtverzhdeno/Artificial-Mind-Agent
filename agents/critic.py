from core.brain import ask_llm


def critique(goal, action, result):

    prompt = f"""
You are analyzing your previous action.

Goal:
{goal}

Action performed:
{action}

Result:
{result}

Evaluate:

1. Was this action useful?
2. What should be improved next time?

Write a short reflection.
"""

    response = ask_llm(prompt)

    return response